# 1. ハードウェア (Hardware Inventory)

本ドキュメントは、PiPulseパイプラインを構成するハードウェア資産のインベントリです。

**最終更新:** 2025-10-24

---

### 改訂履歴
| 日付 | 変更者 | 変更内容 | 関連 |
|---|---|---|---|
| 2025-10-24 | Hideo (assisted by Gemini) | レビューに基づく微調整（一貫性/視覚強化）。 | PR #18<br>(v1.2.4参照) |
| 2025-10-22 | Hideo (assisted by Gemini) | 初版作成。 | PR #11 |

---

### クイックリード
1.  RPi: データ収集コア。
2.  Mac: 分析環境。
3.  MySQL: DB管理、バックアップ推奨。

### ハードウェア概要比較
| 項目 | Mac | RPi | MySQL |
|---|---|---|---|
| RAM | 8 GB | 4 GB | N/A |
| OS | macOS 15.x (Sequoia推定) | Raspbian GNU/Linux 10 (buster) | 9.3.0 (Homebrew) |
| ストレージ | 256 GB SSD | 64 GB microSD | localhost |
| CPU | Apple M2 (8コア) | Broadcom BCM2711 (Quad-core ARM Cortex-A72) | N/A |
| 接続 | Wi-Fi, Bluetooth | Wi-Fi, Bluetooth, Ethernet, I2C | TCP/IP (localhost) |

### 1.1. Mac (データ処理・分析)
- **モデル**: MacBook Air (M2, 2022, 15-inch)
- **OS**: macOS 15.x (Sequoia推定)
- **CPU**: Apple M2 (8コア: 4性能 + 4効率)
- **メモリ (RAM)**: 8 GB Unified Memory
- **ストレージ**: 256 GB SSD

### 1.2. Raspberry Pi (データ収集)
- **モデル**: Raspberry Pi 4 Model B Rev 1.2 (4GB RAM版, Sony UK)
- **OS**: Raspbian GNU/Linux 10 (buster), 32-bit (将来的に64-bit OS (Bookworm) へのアップデートを推奨)
- **Tips:** 将来的に64-bit OS (Bookworm) へのアップデートを推奨。
- **CPU**: Broadcom BCM2711 (Quad-core ARM Cortex-A72)
- **メモリ (RAM)**: 4 GB LPDDR4-3200 SDRAM (ARM割り当て: 948 MB, GPU多め設定)
- **ストレージ**: 64 GB microSD
- **接続ハードウェア**:
  - **センサー**: AHT25 (I2C Bus: 1, Address: 0x38)
  - **電源**: 5V 3A USB-C アダプタ
  - RPiはセンサー収集のコアであり、`cron`による15分間隔のデータ取得は[REQ-02]で定義された<1min更新の基盤となります。

### 1.3. MySQLサーバー (データベース)
- **ホスト**: localhost (Mac, ポート: 3306)
- **バージョン**: 9.3.0 (Homebrew, macos15.4 on arm64)
- **DB概要**: sensor_data_db (InnoDBエンジン)
  - **主要テーブル**: `measurements` (timestamp, temperature, humidity)
  - **Tips:** 定期的なバックアップ (`mysqldump`) を推奨。

*この調整により、ハードウェア構成が明確になり、[REQ-02]のデータ収集基盤が整理されます。*