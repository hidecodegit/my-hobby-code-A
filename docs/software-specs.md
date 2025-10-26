# 2. ソフトウェア (Software Specifications)

本ドキュメントは、PiPulseパイプラインを構成するソフトウェアと依存関係の仕様書です。

**最終更新:** 2025-10-26

---

### 改訂履歴
| 日付 | 変更者 | 変更内容 | 関連 |
|---|---|---|---|
| 2025-10-26 | Hideo (assisted by Gemini) | cronログ監視とトラブルシュートの事例を追記。 | - |
| 2025-10-24 | Hideo (assisted by Gemini) | レビューに基づく微調整（一貫性/視覚強化）。 | PR #18<br>(v1.2.4参照) |
| 2025-10-22 | Hideo (assisted by Gemini) | 初版作成。 | PR #11 |

---

### クイックリード
1.  Python: Mac 3.9.23 / RPi 3.7.3。
2.  依存: smbus / rclone中心。
3.  cron: 15min [REQ-02]同期。

### 2.1. OS / ランタイム
- **Python**:
  - **Mac (開発環境)**: 3.9.23 (conda `my_hobby_env` env, pip 25.2)
    - **Tips:** `python`/`pip`を優先使用。`python3`/`pip3`のwhich/バージョン表示がシステム版（3.9.6）を示す場合があるが、実際の実行はconda環境（3.9.23）が優先されるため、無視可能。機能テスト（e.g., `python -c "import sys; print(sys.version)"`）で確認推奨。
  - **RPi (実行環境)**: 3.7.3 (system)
    - **Tips:** Mac/RPi間のPythonバージョン差による互換性確認を定期的に（e.g., pickleシリアライズ）。
- **MySQL**: 9.3.0

### 2.2. Python 依存関係

Raspberry Pi上の `20251022_SensorCopier.py` (v1.3.0) は、標準ライブラリと `smbus` のみを使用します。

| ライブラリ | RPi (3.7.3) バージョン | 用途 |
|---|---|---|
| `smbus` | 1.1.2 (OS依存) | I2Cセンサー通信 (aptで管理) |

Mac側の分析環境では、`pandas`, `numpy`, `matplotlib`, `mysql-connector-python` などを使用します。

| ライブラリ | Mac (3.9.23) バージョン | 用途 |
|---|---|---|
| `pandas` | 2.3.2 | データ分析 ([REQ-02]グラフ) |
| `numpy` | 2.0.2 | 数値計算 |
| `matplotlib` | 3.9.4 | グラフ描画 ([REQ-02]グラフ) |
| `mysql-connector-python` | 9.4.0 | DB接続 |

### 2.3. その他ツール
- **開発環境 (Mac)**: VSCode + Python拡張機能
- **RPi 運用**:
  - **スケジューラ**: `cron` を使用し、15分間隔でスクリプトを実行。
    - `*/15 * * * * /usr/bin/python3 /home/hideo_81_g/workspace/20251022_SensorCopier.py >> /home/hideo_81_g/logs/cron_sensor.log 2>&1`
    - この`cron`設定は、[REQ-02]で定義されたリアルタイム更新（処理時間<1min目標）の基盤となります。

  - **監視 & トラブルシュート (2025-10-26 更新)**:
    - **cronログリダイレクト**: `crontab -e` でリダイレクト先を `>> /home/hideo_81_g/logs/cron_sensor.log 2>&1` に変更。エラー検知を強化し、SDカードへの影響は微小。
    - **同期タイムスタンプ確認**: `rclone lsl/cat | tail -n 5` や、ログ内の `grep "全体のコピー同期"` により、Google Drive APIの遅延などを監視。
    - **事例**: `last_full_sync.json` が古い症状に対し、18:00のcronトリガーが成功していることをログから確認。これは[REQ-02]の`<1min`目標達成を判断する基準となる。
  - **デプロイ**: RealVNC経由での手動ファイル転送、または `scp` コマンド。
- **データ同期**: `rclone` v1.69.0
  - **リモート**: `raspi_data` (Google Drive)
  - **設定**: 帯域幅制限 `200k` を適用。
- **CI/CD**: GitHub Actions (`ci.yml` - pytest/CodeQL; SUP.1/QA)
- **依存関係管理**: Dependabot (有効化実施 (SUP.7))

*この調整により、ソフトウェア環境が明確になり、[REQ-02]の実現に必要な依存関係が整理されます。*