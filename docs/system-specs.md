# PiPulse Pipeline: System Specifications & Inventory

V字プロセス (SYS.2/SUP.7) に基づくシステム仕様書兼インベントリ。ハードウェア/ソフトウェアのスペック、Python環境、MySQL設定を一元管理します。トラブルシューティング、アップデート、CI/CDの基盤として使用します。

**最終更新:** 2025-10-18  
**バージョン:** v1.0.0 (初版: RPi環境完了 + 依存追加)  
**担当者:** Hideo Kataoka (with Grok & Gemini assist)

## 1. ハードウェア (Hardware Inventory)

### 1.1. Mac (データ処理・分析)
- **モデル**: MacBook Air (M2, 2022, 15-inch)
  - 確認: `sysctl -n hw.model` (出力: Mac14,2)
- **OSバージョン**: macOS 26.0.1 (Build 25A362, Tahoeベータ相当)
  - 確認: `sw_vers`
    - 出力例: `ProductName: macOS`, `ProductVersion: 26.0.1`, `BuildVersion: 25A362`
- **CPU**: Apple M2 (8コア: 4性能 + 4効率)
  - 確認: `sysctl hw.ncpu` (出力: 8)
- **メモリ (RAM)**: 8 GB Unified Memory
  - 確認: `system_profiler SPHardwareDataType | grep "Memory"` (出力: Memory: 8 GB)
- **ストレージ**: 256 GB HDD (空き容量: ~107 GB)
  - 確認: `df -h /` (出力例: Size 228Gi, Used 11Gi, Avail 105Gi)

### 1.2. Raspberry Pi (データ収集)
- **モデル**: Raspberry Pi 4 Model B Rev 1.2 (4GB RAM版, Sony UK)
  - 確認: `cat /proc/cpuinfo | grep Revision` (出力: c03112)
- **OSバージョン**: Raspbian GNU/Linux 10 (buster) (Debian 10ベース, 32-bit ARMv7)
  - 確認コマンド (LX Terminalで): `cat /etc/os-release`
    - 出力例: `PRETTY_NAME="Raspbian GNU/Linux 10 (buster)"`
  - 注意: 64-bit Bookworm (Debian 12) へのアップデート推奨（ARMv8表示&パフォーマンス向上）。手順: Raspberry Pi ImagerでBookwormイメージ書き込み → `sudo apt update && sudo apt full-upgrade`。
- **CPU**: Broadcom BCM2711, 1.5 GHz Quad-core ARM Cortex-A72 (ARMv8, 32-bit OSでv7l表示)
  - 確認コマンド: `cat /proc/cpuinfo | grep -E "model name|cpu MHz"`
    - 出力例: `model name: ARMv7 Processor rev 3 (v7l)` (クロック変動, 最大1.8 GHz)。
- **メモリ (RAM)**: 4 GB LPDDR4-3200 SDRAM (ARM割り当て: 948 MB, GPU多め設定)
  - 確認コマンド: `free -h` (total 3.7Gi) & `vcgencmd get_mem arm` (arm=948M)
    - 注意: /boot/config.txt で `gpu_mem=76` に調整推奨（ARM側RAM最大化）。
- **ストレージ**: 64 GB microSD (空き容量: 43 GB)
  - 確認コマンド: `df -h /`
    - 出力例: `/dev/root 56G 11G 43G 21% /`。
- **接続ハードウェア**:
  - **センサー**: AHT25 (I2C接続, GPIO4ピン)
  - **電源**: 5V 3A USB-C アダプタ (RPi4本体用; USB-Cポート確認済み)
  - **USBデバイス例**: VIA Labs Hub (Device 002), Unknown (ID 25a7:fa61, Device 003/004)
    - 確認: `lsusb`

### 1.3. MySQLサーバー (データベース)
- **ホスト**: localhost (ローカルインストール, ポート: 3306)
  - インストール例 (Mac): Homebrewで `brew install mysql@9.0` → `brew services start mysql@9.0` (RPi: `sudo apt install mysql-server`)
- **バージョン**: 9.2.0 (Homebrew)
  - 確認: `mysql --version` または SQL内で `SELECT VERSION();` (出力: 9.2.0)
- **インスタンススペック**: ローカルリソース依存 (推奨: 1 vCPU, 256-512 MB RAM割り当て; Mac 8GBで余裕)
  - 確認: Activity Monitor (Mac) または `top -p $(pgrep mysqld)` (RPi) でCPU/MEM使用率モニタ
  - 設定例: /usr/local/etc/my.cnf で `innodb_buffer_pool_size=128M` (Mac 8GB RAM基準)
- **DB概要**: sensor_data_db (InnoDBエンジン)
  - 確認: SQL内で `SHOW DATABASES;` (出力: information_schema, mysql, performance_schema, sensor_data_db, sys, test, world)
  - テーブル一覧: `SHOW TABLES;` (出力: hourly_data, hourly_data_separate, measurements, sensor_data, time_slot_stats)
  - テーブル例 (measurements): PRIMARY KEY: id (auto_increment), UNIQUE: timestamp, INDEX: year_month (MUL); カラム: timestamp (datetime), temperature (decimal(5,2)), humidity (decimal(5,2)), year_month (char(7))
    - 確認: SQL内で `DESCRIBE sensor_data_db.measurements;` (出力: 5カラム詳細)
  - 注意: バックアップ必須（`mysqldump -u root -p sensor_data_db > backup.sql`）。データディレクトリ: /usr/local/var/mysql (Macデフォルト)

## 2. ソフトウェア (Software Specifications)

### 2.1. OS / ランタイム
- **Python** (競合解消後):
  - Mac (pipulse env): 3.9.6 (conda専用)
    - 確認: `conda activate pipulse && python --version`
  - RPi (グローバル): 3.7.3 (system Python, workspace内)
    - 確認: `cd /home/hideo_81_g/workspace && python3 --version`
  - **競合解消手順**:
    - Mac: VSCode "Python: Create Environment" → Conda, 3.9.6。
    - RPi: グローバルOK, venvオプション (`python3 -m venv pipulse_env`)。
    - 注意: RPi OSアップデート (Bookworm) で3.11+検討。
- **MySQL**: 9.2.0 (ローカルインストール準拠)
  - 確認: `mysql --version`

### 2.2. Python 依存関係

グローバル環境で管理 (RPi pip list 2025-10-18確認)。RPiはデータ収集/同期のみ, DB/可視化はMac側 – 依存最小化。

| ライブラリ                  | Mac (3.9.6) バージョン | RPi (3.7.3) バージョン | 用途 & 互換注記 |
|-----------------------------|-------------------------|-------------------------|-----------------|
| smbus                      | -                      | 1.1.2 (OS依存)         | I2Cセンサー通信 (RPi必須) – aptで管理 |
| re (標準ライブラリ)         | 3.9.6 (同梱)           | 3.7.3 (同梱)           | ping応答のRTT抽出 (RPi) – インストール不要 |
| pandas                     | 2.3.3                  | 0.23.3 (既存)          | データインポート (RPi: CSV処理) – OK |
| numpy                      | 2.3.4                  | 1.16.2 (既存)          | 異常値検出 (RPiオプション) – OK |
| matplotlib                 | 3.10.7                 | 2.2.3 (既存)           | グラフ化 (RPi: 軽量プロットオプション) – OK |
| seaborn                    | 0.13.2                 | - (オフ)               | 可視化強化 – RPiスコープ外 (Macのみ) |
| mysql-connector-python     | 9.4.0                  | - (オフ)               | MySQL連携 – RPi不要 (Macのみ) |
| Adafruit-DHT (RPiのみ)     | -                      | - (オフ)               | センサー読み取り – 代替OK |
| schedule (RPiのみ)         | -                      | 1.2.2 (グローバル)     | タイマー – cron代替オプション, pip3 showで確認 |
| requests                   | 2.32.3                 | 2.21.0 (既存)          | Drive同期 – OK |
| imageio                    | 2.37.0                 | - (オフ)               | 画像処理 – RPiスコープ外 (Macのみ) |
| Pillow                     | 12.0.0                 | 5.4.1 (既存)           | PNG出力 (RPiオプション) – OK |
| pytest                     | 8.4.2                  | 3.10.1 (既存)          | ユニットテスト – OK (RPi軽量テスト) |
| SQLAlchemy                 | 2.0.44                 | - (オフ)               | ORM – RPi不要 (Macのみ) |

- **requirements_rpi.txt** (最小版, 既存 + schedule):
  
  ```
  # 既存: pandas==0.23.3, numpy==1.16.2, matplotlib==2.2.3, requests==2.21.0, Pillow==5.4.1, pytest==3.10.1
  schedule==1.2.2  # タイマーオプション (グローバルインストール)
  ```
- 生成/インストール: `pip3 freeze > requirements_rpi.txt` / `pip3 install -r requirements_rpi.txt`
- 注意: グローバルインストール時はsudo pip3使用。RAM影響小 (354Mi used基準)。

### 2.3. その他ツール
- **開発ツール (Mac)**: VSCode v1.95.0 + Python拡張 v2025.10.1, Pylance, Python Debugger (インストール済み)
  - 確認: Help > About; Extensionsビュー。
  - 設定: "Python: Select Interpreter" でpipulse env固定。統合ターミナルでenv自動アクティブ。Git操作: Source Controlビュー (⌘Shift+G)。
- **RPi運用ツール**: LX Terminal + cron/systemd (ヘッドレス軽量優先, VSCode/Git非使用)
  - 確認: SSH経由 `crontab -l` (スケジュール), `systemctl list-timers` (timer)。
  - 同期フロー: Mac編集 → RealVNC ViewerでRPi接続 (IP:5900) → VNC内Filesでドラッグ&ドロップ転送 (~/pipulse/) → Terminalで実行/テスト (`source pipulse_env/bin/activate && python script.py`)。
  - 注意: VNCサーバー有効化 (`sudo raspi-config` → Interface → VNC Enable)。転送後タイムスタンプ確認, スクリプトにログ出力追加。RAM負荷低減優先 (セッション時のみ接続)。
- **Google Drive/Sheets連携**: `rclone` v1.69.0 (リモート名: `raspi_data`, config: ~/.config/rclone/rclone.conf)
  - 確認: `rclone version` (バイナリインストール推奨)
- **RPi スケジューラ**: `systemd` timer (15分間隔: AppendSensorData.py, 2時間: GdriveSync.py; サービス例: 20251013_LatestToGdrive.service)
  - 確認: `systemctl list-timers`
- **CI/CD**: GitHub Actions (`ci.yml` - pytest/CodeQL; SUP.1/QA)
- **依存関係管理**: Dependabot (自動PR for pip/rclone updates, SUP.7 TODO)

## 3. 構成管理 (Configuration Management)

- **V字プロセスリンク**:
  - `SYS.2`: データフロー図 (system-design.md) に本ドキュメントのスペックを反映（Drive→Sheets sync追加）。
  - `SWE.3`: 実装 (20251013_LatestToGdrive.py) は本ドキュメントのPython依存関係に従う（リアルタイム<1min対応）。
  - `SUP.7`: ファイル命名規則 (`YYYYMMDD_*.py`) とコミットメッセージルール (feat/fix/refactorプレフィックス) を適用。
- **潜在リスクと対策**:
  - **転送エラー (RPi同期)**: RealVNCでファイルサイズ/権限確認, スクリプトにエラーログ出力追加 (e.g., loggingモジュール)。
  - **メモリ不足 (RPi)**: `full_upload_counter` の導入により、2時間に1回の全量アップロードに制限し、メモリ負荷を軽減 (swap 512MB追加オプション)。
  - **バージョン不一致**: `requirements_[mac/rpi].txt` でバージョンを固定し、Dependabotで更新を管理 (SUP.7 TODO)。
  - **ネットワーク遅延**: `ping_test()` を導入し、RTTを監視 (SYS.1②High要件)。

## 4. 更新履歴

|日付        |バージョン |変更内容                           |参照プロセス      |担当者                 |
|----------|------|-------------------------------|------------|--------------------|
|2025-10-18|v1.0.0|初版作成 (RPi4/Python3.7.3基準, 最小依存 + smbus/re追加) |SYS.2, SUP.7|Hideo Kataoka (Grok/Gemini)|

---
