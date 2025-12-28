# PiPulse Pipeline 統合仕様書
# (Unified Master Specification)

**Document ID**: PP-UMS-001  
**Version**: 1.3.0  
**Version**: 1.3.1  
**Last Updated**: 2025-12-28  
**Status**: Active / Living Document
**Author**: Hideo, Grok, Gemini

---

## 0. ドキュメント管理情報

### 0.1 改訂履歴（Document Level）
**表0-1 改訂履歴 (Document Level)**
| Date       | Author | Description |
|:-----------|:-------|:------------|
| 2025-12-28 | Hideo, Grok, Gemini | **v1.3.1**: INC-006の詳細原因（Pythonガード欠如）とAI過信への教訓を追記し、トレーサビリティを完全化。 |
| 2025-12-28 | Hideo, Grok, Gemini | **v1.3.0**: Grok提案に基づき、ASPICEプロセス意識を残しつつ可読性を向上させた構成へ全面刷新。 |
| 2025-12-27 | Hideo, Grok, Gemini | **Consolidation**: `implementation.md` を廃止し、データ構造・フォーマット定義を本ドキュメントに統合。 |
| 2025-12-21 | Hideo, Grok, Gemini | **Re-structure**: プロセスID（MAN, SYS, SWE...）ベースの階層構造に再編。 |
| 2025-12-21 | Hideo, Grok, Gemini | **Initial Integration**: 既存の全ドキュメント（SYS/SWE/SUP/MAN）を本ファイルに統合。INC-006対応完了版。 |

### 0.2 用語集（Glossary）
**表0-2 用語集**
| Term | Definition |
|:---|:---|
| **Atomic / Non-Atomic (アトミック・非アトミック)** | 操作が不可分であること。アトミックな書き込みは、途中状態が存在せず「成功か失敗か」のどちらかになるため、データ破損を防ぐ（例: `.tmp` 書き込み後の `mv`）。 |
| **7月データ** | 192件の過去センサーデータ（秒なし `%Y-%m-%d %H:%M`）。後方互換性テストのベースライン。 |
| **CI/CD** | Continuous Integration / Continuous Deployment。継続的インテグレーション・デプロイメント（例: GitHub Actionsによる自動テスト・自動デプロイ）。 |
| **Criteria (クライテリア)** | メトリクスに対して設定された合否判定基準・目標値（例: 欠測0、処理時間<60秒）。 |
| **FR (Functional Requirement)** | 機能要件。システムが必ず提供しなければならない機能（例: センサー計測）。 |
| **Metrics (メトリクス)** | 要件の達成度を客観的に測定可能な指標（例: 欠測数、処理時間）。 |
| **NFR (Non-Functional Requirement)** | 非機能要件。性能、信頼性、保守性などの品質特性（例: JST統一、再起動耐性）。 |
| **INC-xxx** | インシデント番号。過去の失敗と教訓を管理するID（例: INC-006）。 |
| **Tailoring (テーラリング)** | 個人開発の規模に合わせて、標準プロセス（V字モデル）を最適化・省略すること。 |
| **Traceability (トレーサビリティ)** | 要件(REQ)から設計、実装、テストまでの追跡可能性。 |
| **Single Source of Truth** | 唯一の正本。本ドキュメント（Unified Master Spec）が全ての情報の基準となること。 |
| **YAML** | Yet Another Markup Language。設定ファイルやCI/CDワークフロー定義（`.github/workflows/*.yml`）に使用される、人間が読みやすいデータ形式。 |

### 0.3 参照ドキュメント（References）
- ASPICE v3.1 Process Reference Model（プロセスIDの参照元）
- ISO/IEC 15288（システムライフサイクルプロセス）
- 本プロジェクトGitHubリポジトリ（コード・ワークフロー）

---

## 1. MAN (Management Process) – プロジェクト管理

### 1.1 プロジェクト概要と目的
- **PiPulse Pipelineのビジョン**: 信頼性が高く、再起動耐性のある温湿度データ収集・クラウド永続化システム。
- **進化の歴史**: 「とりあえず動けばOK」 → 「ドキュメント駆動」 → **「テスト・教訓駆動設計（Test & Lesson-Driven Design）」**（現在）。
- **目的**: 個人開発におけるV字モデルの最適化（テーラリング）の実証と、INC（インシデント）ゼロの運用。

### 1.2 ステークホルダーと役割
**表1-1 ステークホルダーと役割**
| Stakeholder | Role | Responsibilities |
|:---|:---|:---|
| **User (You)** | **Project Owner & Developer** | ビジョン決定、実装、RPi運用、最終意思決定。 |
| **Grok** | **DevOps Advisor** | コードレビュー、ドキュメント整理、INCまとめ、ニヤニヤ担当。 |
| **Gemini** | **Architect & QA Partner** | 要件定義、設計評価、テスト計画、技術的整合性の担保。 |

### 1.3 リリース履歴
**表1-2 リリース履歴**
| Version | Date | Summary |
|:---|:---|:---|
| **v4.20251221** | 2025-12-21 | **INC-006対策版**: 再起動耐性強化（DataRestorer）、ログ完全復旧機能。 |
| v2.0.1 | 2025-12-14 | SWE.3完了版。月次ファイル切り替え実装。 |
| v1.2.0 | 2025-10-22 | `rclone copy` 採用によるデータ消失対策。 |

### 1.4 プロセス・テーラリング宣言
- **Process Tailoring**: 本プロジェクトはASPICEプロセスを個人開発規模にテーラリングしています。
- **統合方針**: 独立した詳細設計書（SYS.3）やソフトウェア要件定義書（SWE.1）は作成せず、本ドキュメントとコード（SWE.3）に統合します。
- **Single File Policy**: `SensorCopier.py` 1ファイルに全ロジックを集約し、デプロイと管理を簡素化します。

---

## 2. SYS (System Definition Process) – システム要件定義

### 2.1 ハードウェア構成
- **Raspberry Pi 4 Model B**: データ収集コア。Raspbian (Buster)。AHT25センサー接続 (I2C)。
- **MacBook Air (M2)**: データ分析・可視化環境。
- **Google Drive**: データ永続化クラウドストレージ。

### 2.2 システム要件一覧（トレーサビリティ表）
**表2-1 機能・非機能要件（Traceability Matrix）**

| ID      | Type | Description                                      | Metrics / Criteria                  | Priority | Trace To                  | Status     |
|:--------|:-----|:-------------------------------------------------|:------------------------------------|:---------|:--------------------------|:-----------|
| REQ-01  | FR   | AHT25から温度・湿度を15分間隔で取得し保存         | 欠測なし、時刻誤差±5秒              | High     | 3.2, 4.1, 5.3             | [x] Done   |
| REQ-01.1| NFR  | タイムスタンプはJST。秒の有無を許容する柔軟パース | パース成功率 100%                   | High     | 3.3.1, 5.4                | [x] Done   |
| REQ-02  | FR   | 収集データをGoogle Driveへアップロード           | E2E処理時間 &lt; 60秒                 | High     | 3.3.5, 4.1, 5.3           | [x] Done   |
| REQ-02.1| NFR  | 月替りでファイル自動切替。ステートレス同期判定   | 切替時刻 00:00 JST                 | High     | 3.3.2, 3.3.3, 5.2         | [x] Done   |
| REQ-02.2| NFR  | アップロードエラー時Slackアラート                 | 通知遅延 ≤ 5分                     | Medium   | 6.2                       | [ ] Todo   |
| REQ-03  | FR   | DriveデータをMySQLに取り込み、Macで可視化         | 描画時間 &lt; 10秒                    | Medium   | 8.4                       | [p] Partial|
| REQ-03.1| NFR  | 可視化性能と異常値検出精度                       | 検出精度 > 95%                      | Medium   | 8.4                       | [p] Partial|
| REQ-04  | FR   | GitHub ActionsによるCI/CD自動化                  | デプロイ成功率 100%                 | Medium   | 6.1                       | [x] Done   |
| REQ-04.1| NFR  | ワークフロー実行時間 < 1min/Job。Slack通知統合    | 成功率 99%                          | Low      | 6.1                       | [ ] Todo   |
| REQ-04.2| NFR  | アーカイブ機能（旧月データ圧縮）。将来拡張        | 復元時間 < 5分                      | Low      | 6.3                       | [ ] Todo   |

---

## 3. SYS/SWE (Design Process) – システム・ソフトウェア設計

### 3.1 システムアーキテクチャ概要
**Logical Components & Data Flow:**
1.  **Cron Scheduler**: 15分ごとにトリガー (`*/15`)。
2.  **Sensor Reader**: I2C経由でAHT25から取得 (Retry x3)。
3.  **Data Writer**: RAM Disk (`/tmp`) へ一時書き込み（SDカード保護） + 月次/最新ファイルの更新。
4.  **Sync Manager**: Pythonロジックで「4時間ごとの全同期」を判定。
5.  **Uploader**: `rclone copy` でクラウドへ転送。

### 3.2 ソフトウェアコンポーネント構成
`SensorCopier.py` 内部の論理モジュール構成：
- **Main Controller**: 処理全体の制御。
- **SensorReader**: I2Cバス経由でのAHT25データ読み取り。 (Ref: **REQ-01**)
- **DataProcessor**: JSTタイムスタンプ付与、データ整形。 (Ref: **REQ-01.1**)
- **DataWriter**: RAMバッファへの書き込み、アトミック更新。 (Ref: **REQ-01**, **REQ-02.1**)
- **SyncManager**: `needs_full_sync` による同期判定。 (Ref: **REQ-02.1**)
- **Uploader**: `rclone` コマンドラッパー。 (Ref: **REQ-02**)
- **DataRestorer**: **(New)** 起動時のデータ復元ロジック。 (Ref: **INC-006**)

### 3.3 詳細設計（Key Logic）

#### 3.3.1 データ保存形式とディレクトリ構造
- **Directory Structure**:
  ```text
  /tmp/sensor_data/                    # RAM Buffer (Volatile)
  ├── temp_humid_YYYY-MM.txt          # Monthly Append
  └── latest_temp_humid.txt           # Latest Atomic Update
  /home/hideo_81_g/sensor_data/        # Persistent Storage
  ├── temp_humid_YYYY-MM.txt
  └── latest_temp_humid.txt
  ```
- **CSV Format**: `YYYY-MM-DD HH:MM:SS,tmp=23.4,hum=45.1` (JST, Fixed Seconds)

#### 3.3.2 月次ファイル切り替えロジック
- `YYYY-MM` 形式のファイル名を動的に生成し、月が変わると自動的に新しいファイルへ書き込みを開始する。

#### 3.3.3 同期判定ロジック（needs_full_sync）
- **課題**: Cronで `0 */4 * * *` と設定すると、REQ-01（15分ごとの計測）が満たせなくなる。また、ガードなしでは4回連続同期が発生する（詳細は **8.6** 参照）。
- **解決策**: Cronは `*/15` で回し、Pythonコード内で `hour % 4 == 0` かつ `0 <= minute < 15` の場合のみ「全同期」フラグを立てる。

#### 3.3.4 再起動耐性（DataRestorer）
- **INC-006対策**: RAMディスク運用中に再起動すると、未保存データが消え、さらに古い永続データで上書きされるリスクがある。
- **解決策**: 起動時に永続領域 (`~/sensor_data`) から RAM (`/tmp`) へデータを逆コピーする。

#### 3.3.5 アトミック更新手法
- **手法**: `.tmp` ファイルに書き込み、`fsync` 後に `os.rename` でアトミックに置き換える。これにより、書き込み途中のデータ破損を防ぐ。

### 3.4 設計決定事項とトレードオフ
- **ConfigLoader未実装**: 設定項目が少ないため、ハードコード定数で実装し、1ファイル構成による保守性を優先。
- **単一ファイル構成**: デプロイの容易さを最優先。

---

## 4. SWE (Implementation Process) – ソフトウェア実装

### 4.1 実装仕様
- **File Name**: `sensor_copier_v5_20251227.py`（次回以降はバージョン日付更新）
- **Language**: Python 3.x
- **Dependencies**: `smbus2`, `rclone` (external command)

### 4.2 デプロイ方法
- **Method**: Self-hosted Runnerによる自動デプロイ。
- **Process**:
    1. GitHub ActionsがRasPi上のRunnerをトリガー。
    2. `git fetch` で最新コードを取得。
    3. `.tmp` ファイル経由でアトミックに配置。
    4. 実行権限付与とシンボリックリンク更新。

---

## 5. V&V (Verification & Validation Process) – 検証・妥当性確認

### 5.1 テスト戦略概要
- **Unit Test**: ロジック（同期判定、コマンド生成）の網羅的テスト。
- **System Test**: 実機での稼働ログ確認。
- **Acceptance Test**: 過去データとの互換性確認。

### 5.2 単体テスト（Unit Test）
- **Scope**: `needs_full_sync` ロジック、`build_rclone_cmd` の安全性。
- **Status**: [x] Done (CIで実行中)。

### 5.3 統合・システムテスト計画
- **Status**: [p] Partial (実機稼働確認)。
- **Plan**: Docker環境でのE2Eテスト（将来拡張）。

### 5.4 受入テスト
- **Status**: [p] Partial (7月データ互換性確認)。

### 5.5 テスト容易性向上施策
- **v5での改善**: `rclone` コマンド生成ロジックを関数化し、単体テスト可能にした（INC-001対策）。

---

## 6. SUP (Supporting Process) – 運用・サポート

### 6.1 CI/CDパイプライン（GitHub Actions）
- **Workflow**: `.github/workflows/test-and-deploy.yml`
- **Test Scope**: Syntax Check, Unit Test (`needs_full_sync`, `build_rclone_cmd`, Data Format).
- **Policy**: テスト通過時のみデプロイを実行（Quality Gate）。

### 6.2 監視・アラート計画
- **Status**: [ ] TBD
- **Plan**: REQ-02.2 に基づくSlack通知の実装。

### 6.3 バックアップ・アーカイブ計画
- **Plan**: 旧月データの圧縮アーカイブ（REQ-04.2）。

### 6.4 構成管理
- **Timezone**: 全て **JST (Japan Standard Time)** で統一。
- **Risks**: I2Cエラー（リトライ済）、SDカード寿命（RAMディスク済）。

---

## 7. SUP (Problem Resolution & Process Improvement) – 教訓とプロセス改善

### 7.1 インシデントログ（Lessons Learned）
**表7-1 インシデントログ**

| ID     | Date       | Incident                  | Root Cause                          | Countermeasure                  | Linked Section |
|:-------|:-----------|:--------------------------|:------------------------------------|:--------------------------------|:---------------|
| INC-001| 2025-10    | クラウドデータ消失         | rclone syncの誤用                   | rclone copyへ変更               | 3.3.5, 4.1     |
| INC-002| 2025-10    | タイムゾーン不整合         | UTC→JST移行時の考慮不足             | JST統一                         | 3.3.1          |
| INC-003| 2025-11    | Silent Fail               | 例外処理の欠如                      | Try-Except強化                  | 4.1            |
| INC-004| 2025-11    | 同期遅延トラブル           | API遅延を同期失敗と誤認             | ログ監視強化                    | 6.2            |
| INC-005| 2025-12    | データ形式混在             | 秒あり/なしデータの混在             | 柔軟なパースロジック実装        | 3.3.1, 5.4     |
| INC-006| 2025-12-20 | 再起動によるデータ消失危機 + 4回連続アップロード | RAMディスク + Flush漏れ + Python同期ガード欠如 | DataRestorer + ロジックガード（詳細は **8.6** 参照） | 3.3.3, 3.3.4, 8.6 |

### 7.2 プロセス改善履歴
- **v1.3.0**: ASPICEプロセス意識を残しつつ、読みやすさと保守性を向上させる構成へ全面刷新。
- **INC-006教訓**: **AIレビューは静的中心。動的テスト（再起動/ガード）と要件トレードオフを人間判断**。
- **次なるステップ**: 過去のINCをテストで未然防止できていなかった教訓を踏まえ、**テスト自体の強化**と、**テスト容易性（Testability）向上のためのコード改修（リファクタリング）**を最優先事項として推進する。

---

## 8. 付録 (Appendices)

### 8.1 Cron設定例
```bash
# 15分ごとに実行 (REQ-01)
*/15 * * * * /usr/bin/python3 /home/hideo_81_g/workspace/SensorCopier_current.py >> /home/hideo_81_g/logs/cron_sensor.log 2>&1
```

### 8.2 rclone設定例（config抜粋）
- **Remote**: `raspi_data` (Google Drive)
- **Bandwidth Limit**: `200k`

### 8.3 主要コードスニペット
**needs_full_sync関数 (INC-006対策)**
```python
def needs_full_sync():
    now = datetime.now()
    # 4時間ごとの枠、かつその枠の最初の15分間だけTrue
    return (now.hour % 4 == 0) and (0 <= now.minute < 15)
```

### 8.4 将来予定機能リスト
- 可視化強化（グラフ・異常値検出）
- Slack通知実装 (REQ-02.2)
- DockerによるE2Eテスト環境

### 8.5 過去データ（7月データ）テストケース概要
- **Format**: `%Y-%m-%d %H:%M` (秒なし)
- **Test**: `read_sensor_data` がこの形式を読み込んでもエラーにならず、秒を `00` として扱えること。

### 8.6 INC-006 詳細レポート (Post-Mortem)
**概要**: 再起動によるデータ消失危機と、4回連続アップロードバグの複合インシデント。

**詳細な経緯と原因**:
1.  **4回連続アップロードバグ**:
    - **事象**: Cronを `*/15` (15分毎) に設定していたが、Python側で「4時間毎」の判定ロジックが不十分だったため、00分, 15分, 30分, 45分 の4回連続で全同期が走ってしまった。
    - **AIの関与**: AIレビューではCron設定の構文ミス（minute指定忘れ等）に目が向きがちで、ロジックガードの欠如を見落とした。「完璧👌」というAIの評価を過信したことが背景にある。
    - **教訓**: Cron設定を変更せず（REQ-01遵守）、Pythonコード内で `needs_full_sync()` によるガードを実装することで解決。AIの提案（Cronを `0 */4` に変更）は要件を満たさないため却下した（人間の判断）。

2.  **再起動データ消失**:
    - **事象**: RAMディスク運用中に再起動を行った際、Flushされていないデータが消失し、さらに起動時に古い永続データで上書きされるリスクがあった。
    - **解決策**: `DataRestorer` を実装し、起動時に永続領域からRAMへデータを復元するフローを追加。

---

## 9. Conclusion

> **We are Strongest.**
> 本プロジェクトは、ASPICEプロセスを個人規模にテーラリングし、教訓駆動設計により堅牢な再起動耐性と完全自動化を実現した。