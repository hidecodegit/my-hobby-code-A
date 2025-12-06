# MAN.1 トレーサビリティマトリクス（Traceability Matrix）
これはV字モデルの管理プロセス（MAN.1）における中心的成果物です。
要件から設計、実装、検証までの追跡可能性（トレーサビリティ）を双方向に確保します。

**最終更新**: 2025-12-06（Hideo, Grok & Gemini 共同確定）

### 改訂履歴
| 日付         | 変更者               | 変更内容                                   |
|--------------|----------------------|--------------------------------------------|
| 2025-12-06   | Hideo, Grok, Gemini  | 初版作成。プロセスごとのステータス管理を導入し、フォーマットを標準化。 |

### 用語集・凡例
- **✓**: 定義済み
- **-**: 未着手または非該当
- **ステータス**: `[x]`=完了, `[p]`=進行中, `[ ]`=未着手

### 双方向トレーサビリティマトリクス

| 要件ID   | 分類 | SYS.1<br>要件 | SYS.2<br>アーキテクチャ設計 | SWE.2<br>SW詳細設計 | SWE.3<br>実装 | V&V<br>検証 |
|----------|------|:-------------:|:------------------------:|:--------------------------:|:------------------------------------------------:|:-------------------------------------:|
| REQ-01   | FR   | ✓ [x]         | センサー取得モジュール [p]   | `sensor_reader` [p]            | `read_sensor_data()` in `SensorCopier.py` [p]      | V&V.3 (`system-tests.md`) [ ]       |
| REQ-01.1 | NFR  | ✓ [x]         | データフロー（柔軟パース） [p] | `parse_flexible_timestamp` [p] | `parse_flexible_timestamp()` in `(TBD)` [p]        | V&V.1 (`unit-tests.md`) [ ]         |
| REQ-02   | FR   | ✓ [x]         | rclone同期フロー [p]         | `uploader` [p]                 | `run_rclone()` in `SensorCopier.py` [p]            | V&V.2 (`integration-tests.md`) [ ]  |
| REQ-02.1 | NFR  | ✓ [x]         | スケジューラー（cron） [p]   | `monthly_switch` [p]           | `get_monthly_filepath()` in `SensorCopier.py` [p]  | V&V.3 (`system-tests.md`) [ ]       |
| REQ-02.2 | NFR  | ✓ [x]         | 監視・通知機構 [ ]           | `slack_alerter` [ ]            | - [ ]                                            | V&V.3 (`system-tests.md`) [ ]       |
| REQ-03   | FR   | ✓ [x]         | MySQLインポート・可視化 [p]  | `mysql_importer`, `plotter` [ ]  | `(TBD: analysis_script.py)` [ ]                  | V&V.2 (`integration-tests.md`) [ ]  |
| REQ-03.1 | NFR  | ✓ [x]         | 描画性能・異常値検出 [p]     | `anomaly_detector` [ ]         | `(TBD: analysis_script.py)` [ ]                  | V&V.2 (`integration-tests.md`) [ ]  |
| REQ-04   | FR   | ✓ [x]         | CI/CDパイプライン [ ]        | `ci_cd_workflow` [ ]           | `.github/workflows/ci.yml` [ ]                   | SUP.6 (`product-acceptance.md`) [ ] |
| REQ-04.2 | NFR  | ✓ [x]         | アーカイブ機構 [ ]           | `archiver` [ ]                 | - [ ]                                            | V&V.3 (`system-tests.md`) [ ]       |