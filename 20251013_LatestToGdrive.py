#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime, timedelta
import os
import smbus
import re  # ping RTT抽出用

# 定数設定
LOG_FILE = "/tmp/20251013_LatestToGdrive.log"
LATEST_FILE = "/tmp/latest_temp_humid.txt"
BACKUP_DIR = "/home/hideo_81_g/sensor_data"
GDRIVE_PATH = "raspi_data:/sensor_data"
INTERVAL_SECONDS = 15 * 60
I2C_BUS = 1
SENSOR_ADDRESS = 0x38
TRIGGER_COMMAND = [0xAC, 0x33, 0x00]
DATA_BUFFER = [0x00] * 7
MAX_I2C_ERRORS = 3
BACKUP_DAY = 1  # 月初1日にバックアップ実行
LAST_BACKUP_RUN_FILE = "/tmp/gdrive_backup_last_run.txt"

def get_sensor_file(month=None):
    """指定された年月に基づくSENSOR_FILEのパス"""
    if month is None:
        month = datetime.now().strftime("%Y-%m")
    return f"/tmp/temp_humid_{month}.txt"

def log(message):
    """ログを/tmpに記録"""
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except OSError as e:
        print(f"ログ書き込みエラー: {e}")

def get_last_backup_run_date():
    """最後にバックアップを実行した日付をファイルから取得"""
    try:
        with open(LAST_BACKUP_RUN_FILE, "r") as f:
            return datetime.strptime(f.read().strip(), "%Y-%m-%d").date()
    except (FileNotFoundError, ValueError):
        return None

def set_last_backup_run_date(date):
    """バックアップ実行日をファイルに書き込む"""
    try:
        with open(LAST_BACKUP_RUN_FILE, "w") as f:
            f.write(date.strftime("%Y-%m-%d"))
    except OSError as e:
        log(f"エラー: バックアップ実行日の書き込み失敗: {e}")

def ping_test():
    """ネットワーク遅延チェック (ping google.com)"""
    try:
        result = subprocess.run(['ping', '-c', '4', '-i', '0.25', 'google.com'], 
                                capture_output=True, text=True, timeout=10)
        rtts = re.findall(r'time=([\d.]+) ms', result.stdout)
        if rtts:
            avg_rtt = sum(float(r) for r in rtts) / len(rtts)
            log(f"RTT平均: {avg_rtt:.2f}ms")
            if avg_rtt > 100:
                log("警告: ネットワーク遅延検知 (RTT > 100ms)")
            return avg_rtt
        else:
            log("警告: ping失敗 - RTT取得不可")
            return None
    except subprocess.TimeoutExpired:
        log("警告: pingタイムアウト")
        return None
    except Exception as e:
        log(f"pingエラー: {e}")
        return None

def initialize_sensor(i2c_bus):
    """センサー初期化"""
    try:
        time.sleep(0.1)
        ret = i2c_bus.read_byte_data(SENSOR_ADDRESS, 0x71)
        if ret in [0x18, 0x1C]:
            if ret == 0x1C:
                log(f"警告: センサーのステータスレジスタが 0x{ret:02X} (期待値: 0x18)")
            log("センサー初期化成功")
            return True
        log(f"警告: センサーのステータスレジスタが 0x{ret:02X} (期待値: 0x18 または 0x1C)")
        return False
    except OSError as e:
        log(f"センサー初期化エラー: {e}")
        return False

def read_sensor_data(i2c_bus, data_buffer):
    """センサーからデータ読み取り"""
    try:
        time.sleep(0.01)
        i2c_bus.write_i2c_block_data(SENSOR_ADDRESS, 0x00, TRIGGER_COMMAND)
        time.sleep(0.08)
        data_buffer[:] = i2c_bus.read_i2c_block_data(SENSOR_ADDRESS, 0x00, 7)
        hum = round((data_buffer[1] << 12 | data_buffer[2] << 4 | (data_buffer[3] & 0xF0) >> 4) / 2**20 * 100, 1)
        tmp = round(((data_buffer[3] & 0x0F) << 16 | data_buffer[4] << 8 | data_buffer[5]) / 2**20 * 200 - 50, 1)
        if not (0 <= hum <= 100 and -40 <= tmp <= 80):
            log(f"異常なセンサーデータ: 温度={tmp}°C, 湿度={hum}%")
            return None
        return f"{datetime.now().strftime('%Y-%m-%d %H:%M')},tmp={tmp},hum={hum}"
    except OSError as e:
        log(f"I2Cエラー: {e}")
        return None

def get_latest_line():
    """現在のSENSOR_FILEの最新行を取得"""
    sensor_file = get_sensor_file()
    try:
        if not os.path.exists(sensor_file):
            log("情報: ファイルが存在しません。アップロードをスキップします。")
            return None # ファイルが存在しないのはエラーではない
        with open(sensor_file, "r") as f:
            lines = f.readlines()
            return lines[-1].strip() if lines else None
    except OSError as e:
        log(f"エラー: {sensor_file} 読み込み失敗: {e}")
        return None

def upload_latest():
    """最新データをLATEST_FILEに書き出し、Google Driveにアップロード"""
    latest = get_latest_line()
    if not latest:
        log("エラー: 最新データ取得失敗")
        upload_latest.txt_time = -1
        upload_latest.rclone_time = -1
        return False
    
    start_txt = time.perf_counter()  # TXT生成計測開始
    txt_time = None
    try:
        with open(LATEST_FILE, "w") as f:
            f.write(latest + "\n")
        txt_time = time.perf_counter() - start_txt  # TXT生成計測終了
        log(f"TXT生成時間: {txt_time:.2f}秒")
    except OSError as e:
        log(f"エラー: {LATEST_FILE} 書き込み失敗: {e}")
        upload_latest.txt_time = -1
        upload_latest.rclone_time = -1
        return False
    finally:
        upload_latest.txt_time = txt_time if txt_time is not None else -1

    start_rclone = time.perf_counter()  # rclone計測開始
    rclone_time = None
    try:
        cmd = ["rclone", "copy", LATEST_FILE, GDRIVE_PATH, "--checksum", "--no-traverse", "--bwlimit", "200k"]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        rclone_time = time.perf_counter() - start_rclone  # rclone計測終了
        log(f"rclone時間 (latest): {rclone_time:.2f}秒")
        return True
    except subprocess.CalledProcessError as e:
        log(f"エラー: rclone copy失敗 (latest): {e.stderr.strip()}")
        rclone_time = -1
        return False
    finally:
        upload_latest.rclone_time = rclone_time if rclone_time is not None else -1

def upload_full_history(source_file, gdrive_path):
    """指定されたファイルをGoogle Driveにアップロード"""
    if not os.path.exists(source_file):
        log(f"情報: アップロード対象ファイルが見つかりません: {source_file}")
        upload_full_history.rclone_time = -1
        return False
    
    start_rclone = time.perf_counter()  # rclone計測開始
    rclone_time = None
    try:
        cmd = ["rclone", "copy", source_file, gdrive_path, "--checksum", "--no-traverse", "--bwlimit", "200k"]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        rclone_time = time.perf_counter() - start_rclone  # rclone計測終了
        log(f"rclone時間 (full): {rclone_time:.2f}秒")
        return True
    except subprocess.CalledProcessError as e:
        log(f"エラー: rclone copy失敗 (full): {e.stderr.strip()}")
        rclone_time = -1
        return False
    finally:
        upload_full_history.rclone_time = rclone_time if rclone_time is not None else -1

def backup_monthly():
    """前月データをSDカードとGoogleドライブにバックアップし、前月ファイルを削除"""
    now = datetime.now()
    last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    last_month_file = get_sensor_file(last_month)
    backup_file_sd = f"{BACKUP_DIR}/temp_humid_{last_month}.txt"

    if not os.path.exists(last_month_file):
        log(f"情報: 前月ファイル {last_month_file} が存在しません。バックアップ処理をスキップします。")
        return True

    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        subprocess.run(["cp", last_month_file, backup_file_sd], capture_output=True, text=True, check=True)
        log(f"処理: SDカードにバックアップ完了: {backup_file_sd}")

        # 改善案1: GDriveへのアップロードが成功した場合のみファイルを削除
        if not upload_full_history(last_month_file, GDRIVE_PATH):
            log(f"警告: Google Driveへのバックアップに失敗しました。ローカルファイルは削除しません。")
            return False

        log(f"処理: Google Driveにバックアップ完了: {last_month_file}")
        os.remove(last_month_file)
        log(f"処理: 前月ファイル {last_month_file} を削除しました。")

        log(f"処理: backup_monthlyが正常に完了しました。")
        return True
    except subprocess.CalledProcessError as e:
        # 改善案2: エラー詳細をログに出力
        log(f"エラー: バックアップ/コピー処理失敗: {e.stderr.strip()}")
        return False
    except OSError as e:
        log(f"エラー: ファイルシステム操作失敗: {e}")
        return False
    except Exception as e:
        log(f"エラー: backup_monthly処理中に予期せぬエラー: {e}")
        return False

def main():
    """メインループ"""
    try:
        i2c = smbus.SMBus(I2C_BUS)
    except FileNotFoundError:
        log("エラー: I2Cバスが見つかりません。'sudo raspi-config'でI2Cを有効にしてください。")
        return

    dat = DATA_BUFFER.copy()
    sensor_error_count = 0
    # 最適化: 全履歴アップロードの間隔を制御するためのカウンタ
    full_upload_counter = 7  # 初回実行時にアップロードされるように7で初期化
    FULL_UPLOAD_INTERVAL = 8  # 15分 * 8 = 2時間

    if not initialize_sensor(i2c):
        log("センサー初期化失敗。スクリプトを終了します。")
        return

    while True:
        start_time = datetime.now()
        start_total = time.perf_counter()  # 総時間計測開始
        
        # ネットワークチェック (ping)
        ping_test()
        
        # 月初バックアップ処理
        current_date = start_time.date()
        last_run_date = get_last_backup_run_date()
        if current_date.day == BACKUP_DAY and last_run_date != current_date:
            log("処理: 月初バックアップ処理を開始します。")
            if backup_monthly():
                log("処理: 月初バックアップが正常に完了しました。")
                set_last_backup_run_date(current_date)
            else:
                log("警告: バックアップ処理に失敗しました。次のサイクルで再試行します。")
                time.sleep(INTERVAL_SECONDS)
                continue

        # センサー読み取りと記録
        start_i2c = time.perf_counter()  # I2C計測開始
        results = read_sensor_data(i2c, dat)
        i2c_time = time.perf_counter() - start_i2c  # I2C計測終了
        log(f"I2C読取時間: {i2c_time:.2f}秒")
        
        if results:
            try:
                sensor_file = get_sensor_file()
                os.makedirs(os.path.dirname(sensor_file), exist_ok=True)
                with open(sensor_file, "a") as f:
                    f.write(results + "\n")
                sensor_error_count = 0
            except OSError as e:
                log(f"エラー: {sensor_file} 書き込み失敗: {e}")
        else:
            sensor_error_count += 1
            if sensor_error_count >= MAX_I2C_ERRORS:
                log("I2Cエラー上限到達。センサー再初期化を試行します。")
                initialize_sensor(i2c)  # 自動復旧を試みる
                sensor_error_count = 0 # カウンタをリセット

        # 最新データは毎回アップロード
        upload_latest()
        
        # 最適化: 2時間に1回（8回に1回）だけ全履歴をアップロード
        full_upload_counter += 1
        full_rclone_time = -1  # full_historyのrclone時間初期化
        if full_upload_counter >= FULL_UPLOAD_INTERVAL:
            log("処理: 全履歴の定期アップロードを実行します。")
            upload_full_history(get_sensor_file(), GDRIVE_PATH)
            full_rclone_time = upload_full_history.rclone_time

        # 処理時間ログ
        total_time = time.perf_counter() - start_total  # 総時間計測終了
        log(f"総処理時間: {total_time:.2f}秒")

        # 改善案: 1サイクルあたりのパフォーマンスサマリーログを追加
        # このログを無効化したい場合は、以下の行をコメントアウトする
        log(f"PERF_SUMMARY: total={total_time:.2f}s, i2c={i2c_time:.2f}s, "
            f"txt_gen={upload_latest.txt_time:.2f}s, rclone_latest={upload_latest.rclone_time:.2f}s, "
            f"rclone_full={full_rclone_time:.2f}s")

        sleep_time = INTERVAL_SECONDS - total_time
        if sleep_time > 0:
            time.sleep(sleep_time)

if __name__ == "__main__":
    main()