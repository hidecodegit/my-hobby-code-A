# PiPulse Pipeline: System Specifications & Inventory

本ドキュメントは、PiPulseパイプラインのハードウェア、ソフトウェア、および関連設定を管理するシステム仕様書兼インベントリです。

**最終更新:** 2025-10-19
**バージョン:** v1.1.1 (Mac Python環境を3.9.23に確定、MySQL 9.3.0更新、依存テーブル追加、シェル表示問題の無視補足)
**担当者:** Hideo Kataoka (with Grok & Gemini assist)

## 1. ハードウェア (Hardware Inventory)

### 1.1. Mac (データ処理・分析)
- **モデル**: MacBook Air (M2, 2022, 15-inch)
- **OS**: macOS 26.0.1 (Tahoe)
- **CPU**: Apple M2 (8コア: 4性能 + 4効率)
- **メモリ (RAM)**: 8 GB Unified Memory
- **ストレージ**: 256 GB SSD

### 1.2. Raspberry Pi (データ収集)
- **モデル**: Raspberry Pi 4 Model B Rev 1.2 (4GB RAM版, Sony UK)
- **OS**: Raspbian GNU/Linux 10 (buster), 32-bit
  - *補足: 将来的に64-bit OS (Bookworm) へのアップデートを推奨。*
- **CPU**: Broadcom BCM2711 (Quad-core ARM Cortex-A72)
- **メモリ (RAM)**: 4 GB LPDDR4-3200 SDRAM (ARM割り当て: 948 MB, GPU多め設定)
- **ストレージ**: 64 GB microSD
- **接続ハードウェア**:
  - **センサー**: AHT25 (I2C Bus: 1, Address: 0x38)
  - **電源**: 5V 3A USB-C アダプタ

### 1.3. MySQLサーバー (データベース)
- **ホスト**: localhost (Mac, ポート: 3306)
- **バージョン**: 9.3.0 (Homebrew, macos15.4 on arm64)
- **DB概要**: sensor_data_db (InnoDBエンジン)
  - **主要テーブル**: `measurements` (timestamp, temperature, humidity)
  - *補足: 定期的なバックアップ (`mysqldump`) を推奨。*

## 2. ソフトウェア (Software Specifications)

### 2.1. OS / ランタイム
- **Python**:
  - **Mac (開発環境)**: 3.9.23 (conda `my_hobby_env` env, pip 25.2)
    - *補足: `python`/`pip`を優先使用。`python3`/`pip3`のwhich/バージョン表示がシステム版（3.9.6）を示す場合があるが、実際の実行はconda環境（3.9.23）が優先されるため、無視可能。機能テスト（e.g., `python -c "import sys; print(sys.version)"`）で確認推奨。*
  - **RPi (実行環境)**: 3.7.3 (system)
    - *補足: Mac/RPi間のPythonバージョン差による互換性確認を定期的に（e.g., pickleシリアライズ）。*
- **MySQL**: 9.3.0

### 2.2. Python 依存関係

Raspberry Pi上の `SensorSync.py` (v1.2.0) は、標準ライブラリと `smbus` のみを使用します。

|ライブラリ|RPi (3.7.3) バージョン|用途                |
|---|---|---|
|smbus|1.1.2 (OS依存)     |I2Cセンサー通信 (aptで管理)|

Mac側の分析環境では、`pandas`, `numpy`, `matplotlib`, `mysql-connector-python` などを使用します。

|ライブラリ                 |Mac (3.9.23) バージョン|用途   |
|---|---|---|
|pandas                |2.3.2             |データ分析|
|numpy                 |2.0.2             |数値計算 |
|matplotlib            |3.9.4             |グラフ描画|
|mysql-connector-python|9.4.0             |DB接続 |

### 2.3. その他ツール
- **開発環境 (Mac)**: VSCode + Python拡張機能
- **RPi 運用**:
  - **スケジューラ**: `cron` を使用し、15分間隔で `SensorSync.py` を実行。
    - `*/15 * * * * /usr/bin/python3 /home/hideo_81_g/workspace/SensorSync.py`
  - **デプロイ**: RealVNC経由での手動ファイル転送。
- **データ同期**: `rclone` v1.69.0
  - **リモート**: `raspi_data` (Google Drive)
  - **設定**: 帯域幅制限 `200k` を適用。
- **CI/CD**: GitHub Actions (`ci.yml` - pytest/CodeQL; SUP.1/QA)
- **依存関係管理**: Dependabot (有効化を検討)

## 3. 構成管理 (Configuration Management)

- **V字プロセスリンク**:
  - `SYS.2`: 本ドキュメントはシステム設計 (`system-design.md`) のスペック定義に相当。
  - `SWE.3`: `SensorSync.py` の実装は本ドキュメントの依存関係に従う。
  - `SUP.7`: コミットメッセージルール (feat/fix/refactor) を適用。
- **潜在リスクと対策**:
  - **I2C/センサーエラー**: `SensorSync.py` 内でエラーカウンタを設け、3回連続でエラーが発生した場合にセンサーを再初期化。
  - **メモリ不足 (RPi)**: データの一時保存にRAMディスク (`/tmp/sensor_data`) を使用し、SDカードへの書き込みを抑制。
  - **データ同期エラー**: `rclone` 実行時にリトライ処理（指数バックオフ）を実装。

## 4. 更新履歴

|日付        |バージョン |変更内容                                                                                          |担当者                        |
|---|---|---|---|
|2025-10-19|v1.1.1|Mac Python環境をconda `my_hobby_env` (3.9.23, pip 25.2)で最終確認。MySQL 9.3.0更新、依存テーブル追加、シェル表示問題の無視補足。|Hideo Kataoka (Grok assist)|
|2025-10-19|v1.1.0|`SensorSync.py` (v1.2.0) の内容を反映し、ドキュメント全体を簡素化。                                                |Hideo Kataoka (Grok/Gemini)|
|2025-10-18|v1.0.0|初版作成 (RPi4/Python3.7.3基準)。                                                                    |Hideo Kataoka (Grok/Gemini)|

---
