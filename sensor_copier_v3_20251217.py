#!/usr/bin/env python3
import time
from datetime import datetime
import os
try:
    import smbus
except ImportError:
    import smbus2 as smbus  # CIテスト環境でsmbusがない場合のフォールバック
import logging
import subprocess
import json

# --- 設定 ---
__version__ = "3.0.0"  # 定時同期のバグを修正した安定版

# ログ設定
LOG_DIR = "/home/hideo_81_g/logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_handlers = [logging.FileHandler(os.path.join(LOG_DIR, "sensor_copier_v3.log"))]

if os.environ.get("LOG_TO_CONSOLE") in ("1", "true", "True"):
    log_handlers.append(logging.StreamHandler())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)
logger.info(f"--- SensorCopier v{__version__} 起動 ---")

# --- 定数設定 (SWE.2 アーキテクチャ) ---

# RAMバッファ (高速書き込み用)
RAM_DATA_DIR = "/tmp/sensor_data"
os.makedirs(RAM_DATA_DIR, exist_ok=True)

# 永続ディレクトリ (停電耐性用)
PERSISTENT_DATA_DIR = "/home/hideo_81_g/sensor_data"
os.makedirs(PERSISTENT_DATA_DIR, exist_ok=True)

LATEST_FILENAME = "latest_temp_humid.txt"

I2C_BUS = 1
SENSOR_ADDRESS = 0x38
TRIGGER_COMMAND = [0xAC, 0x33, 0x00]
MAX_I2C_ERRORS = 3

AHT25_STATUS_MASK = 0x18

SENSOR_INIT_SLEEP = 0.1
CONVERSION_SLEEP = 0.08

# 全体同期の間隔（時間）
FULL_SYNC_INTERVAL_HOURS = 4

BW_LIMIT = "200k"

i2c_error_count = 0

# --- モジュール実装 (SWE.2) ---

def get_monthly_filepath(base_dir):
    """現在の年月に基づく月次データファイルのパスを生成 (JSTローカル)"""
    month_str = datetime.now().strftime("%Y-%m")
    return os.path.join(base_dir, f"temp_humid_{month_str}.txt")

def initialize_sensor(i2c_bus):
    """SensorReader: センサー初期化"""
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
    """SensorReader & DataProcessor: センサーからデータを読み取り、CSV形式の文字列を返す (JSTローカル)"""
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
        # DataProcessor: タイムスタンプ付与
        return f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},tmp={temperature},hum={humidity}"
    except (OSError, ValueError) as e:
        i2c_error_count += 1
        logger.error(f"I2Cエラー ({i2c_error_count}/{MAX_I2C_ERRORS}): {e}")
        if i2c_error_count >= MAX_I2C_ERRORS:
            logger.warning("連続I2Cエラー。センサーを再初期化します。")
            initialize_sensor(i2c_bus)
            i2c_error_count = 0
        return None

def execute_command(command, description, retries=3):
    """汎用コマンド実行関数 (リトライ付き)"""
    for attempt in range(retries):
        try:
            # タイムアウトを120秒に延長
            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=120)
            logger.info(f"{description} 成功。")
            return True
        except subprocess.TimeoutExpired:
            logger.error(f"{description} タイムアウト (120s)。リトライします ({attempt+1}/{retries})。")
        except subprocess.CalledProcessError as e:
            logger.error(f"{description} 失敗 (試行 {attempt+1}/{retries})。エラー: {e.stderr.strip()}")
        
        if attempt < retries - 1:
            time.sleep(2 ** attempt)

    logger.critical(f"{description} に {retries}回失敗しました。")
    return False

def needs_full_sync():
    """SyncManager: 全体同期の必要性をcron基準で判定（ステートレス）"""
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute

    # 4時間ごとの、かつ0分から14分の間に実行された場合のみ同期を許可する
    # (cronが15分間隔で実行されることを想定)
    if current_hour % FULL_SYNC_INTERVAL_HOURS == 0 and 0 <= current_minute < 15:
        return True, f"定時同期（{FULL_SYNC_INTERVAL_HOURS}時間ごと）の時刻のため"
    return False, ""

def flush_ram_to_persistent():
    """DataFlusher: RAMバッファから永続ディレクトリへrsyncで安全にフラッシュ"""
    logger.info(f"DataFlusher: RAMバッファ ({RAM_DATA_DIR}) から永続領域 ({PERSISTENT_DATA_DIR}) へフラッシュします。")
    # 【重要】--deleteオプションは使用しない。RAM消失時に永続データが消えるのを防ぐため。
    cmd = ["rsync", "-a", RAM_DATA_DIR + "/", PERSISTENT_DATA_DIR + "/"]
    return execute_command(cmd, "RAMから永続領域へのフラッシュ")

def main():
    """Main Controller: 全体の処理フローを制御"""
    start_ts = time.perf_counter()
    i2c = None

    try:
        i2c = smbus.SMBus(I2C_BUS)
        if not initialize_sensor(i2c):
            logger.critical("センサー初期化に失敗。処理を中断します。")
            return
    except FileNotFoundError:
        logger.critical("I2Cバスが見つかりません。raspi-configでI2Cを有効にしてください。")
        return
    
    try:
        # 1. SensorReader & DataProcessor
        latest_line = read_sensor_data(i2c)
        
        if latest_line:
            # 2. DataWriter: RAMバッファに書き込み
            # 月次ファイルへ追記 (fsyncで原子性を強化)
            monthly_path_ram = get_monthly_filepath(RAM_DATA_DIR)
            with open(monthly_path_ram, "a") as f:
                f.write(latest_line + "\n")
                f.flush()
                os.fsync(f.fileno())
            logger.info(f"RAMバッファの月次ファイルに追記: {latest_line}")

            # 最新ファイルへアトミックに上書き (.tmp + fsync + rename)
            latest_filepath_ram = os.path.join(RAM_DATA_DIR, LATEST_FILENAME)
            temp_latest_path = latest_filepath_ram + ".tmp"
            with open(temp_latest_path, "w") as f:
                f.write(latest_line + "\n")
                f.flush()
                os.fsync(f.fileno())
            os.rename(temp_latest_path, latest_filepath_ram)
            
            # 3. Uploader: 最新ファイルのみ即時アップロード
            cmd = ["rclone", "copy", latest_filepath_ram, "raspi_data:/sensor_data/", "--checksum", "--no-traverse", "--bwlimit", BW_LIMIT]
            execute_command(cmd, "最新データのアップロード")
        else:
            logger.warning("センサーデータの読み取りに失敗。書き込み・アップロードはスキップします。")

        # 4. SyncManager: 全体同期の判定
        is_sync_needed, reason = needs_full_sync()
        if is_sync_needed:
            logger.info(f"{reason}、全体同期プロセスを開始します。")
            
            # 5. DataFlusher: RAM -> 永続領域
            if flush_ram_to_persistent():
                # 6. Uploader: 永続ディレクトリ全体をアップロード
                logger.info("永続ディレクトリ全体のコピー同期を開始します。")
                cmd = ["rclone", "copy", PERSISTENT_DATA_DIR, "raspi_data:/sensor_data/", "--bwlimit", BW_LIMIT]
                execute_command(cmd, "永続ディレクトリ全体のコピー同期")
            else:
                logger.error("RAMから永続領域へのフラッシュに失敗したため、全体同期は中止します。")

        duration = time.perf_counter() - start_ts
        logger.info(f"全処理完了。処理時間: {duration:.2f}秒")

    finally:
        if i2c:
            try:
                i2c.close()
                logger.debug("I2Cバスをクローズしました。")
            except Exception as e:
                logger.error(f"I2Cバスのクローズ中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
