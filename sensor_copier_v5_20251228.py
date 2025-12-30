#!/usr/bin/env python3
import time
from datetime import datetime, timezone, timedelta
import os
try:
    import smbus
except ImportError:
    import smbus2 as smbus  # CIテスト環境でsmbusがない場合のフォールバック
import logging
from logging.handlers import RotatingFileHandler
import shutil
import subprocess

# --- 設定 ---
__version__ = "5.1.0"  # v5.1.0: JST強制・空ファイル対策版 (Lite)

# ログ設定
LOG_DIR = "/home/hideo_81_g/logs"
# CI環境ではログディレクトリ作成をスキップ (PermissionError回避)
if os.getenv("GITHUB_ACTIONS") != "true":
    os.makedirs(LOG_DIR, exist_ok=True)

# ログローテーション設定 (SDカード容量圧迫防止)
# maxBytes=1MB, backupCount=3世代まで保存
log_file_path = os.path.join(LOG_DIR, "sensor_copier_v5.log")
log_handlers = [
    RotatingFileHandler(log_file_path, maxBytes=1024*1024, backupCount=3)
]

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
if os.getenv("GITHUB_ACTIONS") != "true":
    os.makedirs(RAM_DATA_DIR, exist_ok=True)

# 永続ディレクトリ (停電耐性用)
PERSISTENT_DATA_DIR = "/home/hideo_81_g/sensor_data"
if os.getenv("GITHUB_ACTIONS") != "true":
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

# JSTタイムゾーン定義 (INC-002対策: 環境依存排除)
JST = timezone(timedelta(hours=9), 'JST')

i2c_error_count = 0

# --- モジュール実装 (SWE.2) ---

def get_jst_now():
    """現在時刻(JST)を取得する。システム時刻設定に依存せずJSTを強制する。"""
    return datetime.now(JST)

def get_monthly_filepath(base_dir):
    """現在の年月に基づく月次データファイルのパスを生成 (JST)"""
    month_str = get_jst_now().strftime("%Y-%m")
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
    """SensorReader: センサーからデータを読み取り、CSV形式の文字列を返す (JST)"""
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
        # INC-005対策: 秒ありフォーマット固定
        return f"{get_jst_now().strftime('%Y-%m-%d %H:%M:%S')},tmp={temperature},hum={humidity}"
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
    """SyncManager: 全体同期の必要性をcron基準で判定"""
    now = get_jst_now()
    current_hour = now.hour
    current_minute = now.minute

    # INC-006対策: 4時間ごとの枠、かつその枠の最初の15分間だけTrue
    if current_hour % FULL_SYNC_INTERVAL_HOURS == 0 and 0 <= current_minute < 15:
        return True, f"定時同期（{FULL_SYNC_INTERVAL_HOURS}時間ごと）の時刻のため"
    return False, ""

def build_rclone_cmd(source, dest, is_file=True):
    """Uploader: rcloneコマンドを生成"""
    cmd = ["rclone", "copy", source, dest]
    if is_file:
        cmd.extend(["--checksum", "--no-traverse"])
    cmd.extend(["--bwlimit", BW_LIMIT])
    return cmd

def flush_ram_to_persistent():
    """DataFlusher: RAMバッファから永続ディレクトリへrsyncで安全にフラッシュ"""
    logger.info(f"DataFlusher: RAMバッファ ({RAM_DATA_DIR}) から永続領域 ({PERSISTENT_DATA_DIR}) へフラッシュします。")
    # 【重要】--deleteオプションは使用しない。RAM消失時に永続データが消えるのを防ぐため。
    cmd = ["rsync", "-a", RAM_DATA_DIR + "/", PERSISTENT_DATA_DIR + "/"]
    return execute_command(cmd, "RAMから永続領域へのフラッシュ")

def restore_ram_from_persistent():
    """DataRestorer: 起動時に永続領域からRAMへデータを復元する"""
    # 1. 月次ファイルの復元
    monthly_path_ram = get_monthly_filepath(RAM_DATA_DIR)
    monthly_path_persistent = get_monthly_filepath(PERSISTENT_DATA_DIR)

    # INC-006追加対策: ファイルが存在しない場合 OR サイズが0の場合に復元する
    should_restore_monthly = False
    if not os.path.exists(monthly_path_ram):
        should_restore_monthly = True
    elif os.path.getsize(monthly_path_ram) == 0:
        logger.warning(f"RAM上の月次ファイルが空(0byte)です。破損リスクのため復元対象とします: {monthly_path_ram}")
        should_restore_monthly = True

    if should_restore_monthly and os.path.exists(monthly_path_persistent):
        logger.info(f"DataRestorer: RAMバッファ(月次)が空です。永続領域から復元します: {monthly_path_persistent} -> {monthly_path_ram}")
        try:
            shutil.copy2(monthly_path_persistent, monthly_path_ram)
            logger.info("月次ファイル復元成功。")
        except Exception as e:
            logger.error(f"月次ファイル復元失敗: {e}")

    # 2. 最新データファイル(latest)の復元
    latest_path_ram = os.path.join(RAM_DATA_DIR, LATEST_FILENAME)
    latest_path_persistent = os.path.join(PERSISTENT_DATA_DIR, LATEST_FILENAME)

    should_restore_latest = False
    if not os.path.exists(latest_path_ram):
        should_restore_latest = True
    elif os.path.getsize(latest_path_ram) == 0:
        logger.warning(f"RAM上のlatestファイルが空(0byte)です。復元対象とします。")
        should_restore_latest = True

    if should_restore_latest and os.path.exists(latest_path_persistent):
        logger.info(f"DataRestorer: RAMバッファ(latest)が空です。永続領域から復元します: {latest_path_persistent} -> {latest_path_ram}")
        try:
            shutil.copy2(latest_path_persistent, latest_path_ram)
            logger.info("最新データファイル復元成功。")
        except Exception as e:
            logger.error(f"最新データファイル復元失敗: {e}")

def main():
    """Main Controller"""
    start_ts = time.perf_counter()
    i2c = None

    try: # Global Error Handler
        try:
            i2c = smbus.SMBus(I2C_BUS)
            if not initialize_sensor(i2c):
                logger.critical("センサー初期化に失敗。処理を中断します。")
                return
        except FileNotFoundError:
            logger.critical("I2Cバスが見つかりません。raspi-configでI2Cを有効にしてください。")
            return
    
        # 0. DataRestorer: 処理開始前にRAMの状態を確認・復元
        restore_ram_from_persistent()

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
            cmd = build_rclone_cmd(latest_filepath_ram, "raspi_data:/sensor_data/", is_file=True)
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
                cmd = build_rclone_cmd(PERSISTENT_DATA_DIR, "raspi_data:/sensor_data/", is_file=False)
                execute_command(cmd, "永続ディレクトリ全体のコピー同期")
            else:
                logger.error("RAMから永続領域へのフラッシュに失敗したため、全体同期は中止します。")

        duration = time.perf_counter() - start_ts
        logger.info(f"全処理完了。処理時間: {duration:.2f}秒")

    except Exception as e:
        logger.critical(f"予期せぬエラーが発生し、プロセスがクラッシュしました: {e}", exc_info=True)
    finally:
        if i2c:
            try:
                i2c.close()
                logger.debug("I2Cバスをクローズしました。")
            except Exception as e:
                logger.error(f"I2Cバスのクローズ中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()