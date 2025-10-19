#!/usr/bin/env python3
import time
from datetime import datetime, timezone
import os
import smbus
import logging
import subprocess
import json

# --- 設定 ---
__version__ = "1.2.1"  # ログ戦略改善版

# ログ設定
LOG_DIR = "/home/hideo_81_g/logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ハンドラリストを作成 (条件付き)
log_handlers = [logging.FileHandler(os.path.join(LOG_DIR, "sensor_sync.log"))]

# 環境変数 LOG_TO_CONSOLE=1/true でコンソール出力ON (手動テスト用)
if os.environ.get("LOG_TO_CONSOLE") in ("1", "true", "True"):
    log_handlers.append(logging.StreamHandler())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

# 定数設定
SENSOR_DATA_DIR = "/tmp/sensor_data"  # SDカード保護のためRAMディスクを使用
os.makedirs(SENSOR_DATA_DIR, exist_ok=True)

LATEST_FILENAME = "latest_temp_humid.txt"
FULL_SYNC_STATE_FILE = os.path.join(SENSOR_DATA_DIR, "last_full_sync.json")

I2C_BUS = 1
SENSOR_ADDRESS = 0x38
TRIGGER_COMMAND = [0xAC, 0x33, 0x00]
MAX_I2C_ERRORS = 3

AHT25_STATUS_MASK = 0x18

SENSOR_INIT_SLEEP = 0.1
CONVERSION_SLEEP = 0.08

FULL_SYNC_INTERVAL_HOURS = 2

BW_LIMIT = "200k"

i2c_error_count = 0

def get_monthly_filepath():
    """現在の年月に基づく月次データファイルのパスを生成 (UTC基準)"""
    month_str = datetime.now(timezone.utc).strftime("%Y-%m")
    return os.path.join(SENSOR_DATA_DIR, f"temp_humid_{month_str}.txt")

def initialize_sensor(i2c_bus):
    """センサー初期化"""
    try:
        time.sleep(SENSOR_INIT_SLEEP)
        status = i2c_bus.read_byte_data(SENSOR_ADDRESS, 0x71)
        if (status & AHT25_STATUS_MASK) == AHT25_STATUS_MASK:
            logger.info("センサー初期化成功。")
            return True
        logger.warning(f"センサー初期化失敗。ステータス: {hex(status)}")
        return False
    except OSError as e:
        logger.error(f"センサー初期化エラー: {e}")
        return False

def read_sensor_data(i2c_bus):
    """センサーからデータを読み取り、CSV形式の文字列を返す"""
    global i2c_error_count
    try:
        i2c_bus.write_i2c_block_data(SENSOR_ADDRESS, 0x00, TRIGGER_COMMAND)
        time.sleep(CONVERSION_SLEEP)
        data = i2c_bus.read_i2c_block_data(SENSOR_ADDRESS, 0x00, 7)

        if (data[0] & AHT25_STATUS_MASK) != AHT25_STATUS_MASK:
            raise ValueError(f"無効なセンサーステータス: {hex(data[0])}")

        hum_raw = (data[1] << 12 | data[2] << 4 | (data[3] >> 4))
        tmp_raw = ((data[3] & 0x0F) << 16 | data[4] << 8 | data[5])

        humidity = round((hum_raw / 2**20) * 100, 1)
        temperature = round((tmp_raw / 2**20) * 200 - 50, 1)

        if not (0 <= humidity <= 100 and -40 <= temperature <= 80):
            logger.warning(f"異常値検出: tmp={temperature}°C, hum={humidity}%")
            return None

        i2c_error_count = 0
        return f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')},tmp={temperature},hum={humidity}"
    except (OSError, ValueError) as e:
        i2c_error_count += 1
        logger.error(f"I2Cエラー ({i2c_error_count}/{MAX_I2C_ERRORS}): {e}")
        if i2c_error_count >= MAX_I2C_ERRORS:
            logger.warning("連続I2Cエラー。センサーを再初期化します。")
            initialize_sensor(i2c_bus)
            i2c_error_count = 0
        return None

def run_rclone(command, description, retries=3):
    """rcloneコマンドをリトライ付きで実行"""
    for attempt in range(retries):
        try:
            subprocess.run(command, capture_output=True, text=True, check=True, timeout=90)
            logger.info(f"{description} 成功。")
            return True
        except subprocess.TimeoutExpired:
            logger.error(f"{description} タイムアウト (90s)。リトライします ({attempt+1}/{retries})。")
            time.sleep(2 ** attempt)
        except subprocess.CalledProcessError as e:
            logger.error(f"{description} 失敗。rcloneエラー: {e.stderr.strip()}")
            return False
    logger.critical(f"{description} に {retries}回失敗しました。")
    return False

def main():
    """メイン処理: 15分ごとにcronで実行されることを想定"""
    start_ts = time.perf_counter()

    try:
        i2c = smbus.SMBus(I2C_BUS)
        if not initialize_sensor(i2c):
            logger.critical("センサー初期化に失敗。処理を中断します。")
            return
    except FileNotFoundError:
        logger.critical("I2Cバスが見つかりません。raspi-configでI2Cを有効にしてください。")
        return

    latest_line = read_sensor_data(i2c)
    if latest_line:
        monthly_path = get_monthly_filepath()
        # アトミック書き込み (全読み込み + 書き戻し)
        lines_to_write = []
        if os.path.exists(monthly_path):
            with open(monthly_path, "r") as f:
                lines_to_write = f.readlines()
        lines_to_write.append(latest_line + "\n")

        temp_path = monthly_path + ".tmp"
        with open(temp_path, "w") as f:  # "w"モードで全書き戻し
            f.writelines(lines_to_write)
        os.rename(temp_path, monthly_path)
        logger.info(f"月次ファイルに追記: {latest_line}")

        latest_filepath = os.path.join(SENSOR_DATA_DIR, LATEST_FILENAME)
        with open(latest_filepath, "w") as f:
            f.write(latest_line + "\n")
        cmd = ["rclone", "copy", latest_filepath, "raspi_data:/sensor_data/", "--checksum", "--no-traverse", "--bwlimit", BW_LIMIT]
        run_rclone(cmd, "最新データのアップロード")
    else:
        logger.warning("センサーデータの読み取りに失敗。アップロードはスキップします。")

    # 2時間ごとの全体同期 (UTC対応)
    needs_full_sync = not os.path.exists(FULL_SYNC_STATE_FILE)
    if not needs_full_sync:
        try:
            with open(FULL_SYNC_STATE_FILE, 'r') as f:
                state = json.load(f)
                last_sync = datetime.fromisoformat(state['last_sync']).replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - last_sync).total_seconds() >= FULL_SYNC_INTERVAL_HOURS * 3600:
                    needs_full_sync = True
        except (json.JSONDecodeError, FileNotFoundError):
            needs_full_sync = True

    if needs_full_sync:
        logger.info("全体の差分同期を開始します。")
        cmd = ["rclone", "sync", SENSOR_DATA_DIR, "raspi_data:/sensor_data/", "--bwlimit", BW_LIMIT]
        if run_rclone(cmd, "全体の差分同期"):
            with open(FULL_SYNC_STATE_FILE, 'w') as f:
                json.dump({'last_sync': datetime.now(timezone.utc).isoformat(), 'version': __version__}, f)

    duration = time.perf_counter() - start_ts
    logger.info(f"全処理完了。処理時間: {duration:.2f}秒")

if __name__ == "__main__":
    main()