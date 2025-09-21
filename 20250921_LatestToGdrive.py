#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime, timedelta
import os
import smbus

# 定数設定
LOG_FILE = "/tmp/20250921_LatestToGdrive.log"
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

def get_sensor_file(month=None):
    """指定された年月に基づくSENSOR_FILEのパス"""
    if month is None:
        month = datetime.now().strftime("%Y-%m")
    return f"/tmp/temp_humid_{month}.txt"

def get_gdrive_file(month=None):
    """Googleドライブ上のファイルパス"""
    if month is None:
        month = datetime.now().strftime("%Y-%m")
    return f"raspi_data:/sensor_data/temp_humid_{month}.txt"

def log(message):
    """ログを/tmpに記録"""
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except OSError as e:
        print(f"ログ書き込みエラー: {e}")

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
            log(f"エラー: {sensor_file} が見つかりません")
            return None
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
        return False
    try:
        with open(LATEST_FILE, "w") as f:
            f.write(latest + "\n")
        cmd = ["rclone", "copy", LATEST_FILE, GDRIVE_PATH, "--checksum", "--no-traverse", "--bwlimit", "200k"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        log(f"処理: 最新データアップロードOK: {latest}")
        return True
    except subprocess.CalledProcessError as e:
        log(f"エラー: rclone copy失敗 (latest): {e.stderr}")
        return False
    except OSError as e:
        log(f"エラー: {LATEST_FILE} 書き込み失敗: {e}")
        return False

def upload_full_history(source_file, gdrive_path):
    """指定されたファイルをGoogle Driveにアップロード"""
    if not os.path.exists(source_file):
        log(f"エラー: {source_file} が見つかりません")
        return False
    try:
        cmd = ["rclone", "copy", source_file, gdrive_path, "--checksum", "--no-traverse", "--bwlimit", "200k"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        log(f"処理: 全履歴アップロードOK: {gdrive_path}")
        return True
    except subprocess.CalledProcessError as e:
        log(f"エラー: rclone copy失敗 (full): {e.stderr}")
        return False

def backup_monthly():
    """前月データをSDカードとGoogleドライブにバックアップし、前月ファイルを削除"""
    now = datetime.now()
    last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    last_month_file = get_sensor_file(last_month)
    backup_file_sd = f"{BACKUP_DIR}/temp_humid_{last_month}.txt"
    backup_file_gdrive = get_gdrive_file(last_month)

    if not os.path.exists(last_month_file):
        log(f"警告: 前月ファイル {last_month_file} が存在しません。バックアップ処理をスキップします。")
        return True # ファイルがない場合は成功とみなして、メインループの再試行を防ぐ

    try:
        # SDカードにバックアップ
        os.makedirs(BACKUP_DIR, exist_ok=True)
        subprocess.run(["cp", last_month_file, backup_file_sd], capture_output=True, text=True, check=True)
        log(f"処理: SDカードにバックアップ完了: {backup_file_sd}")

        # Googleドライブにバックアップ
        upload_full_history(last_month_file, backup_file_gdrive)

        # 前月ファイルを削除
        os.remove(last_month_file)
        log(f"処理: 前月ファイル {last_month_file} を削除しました")

        log(f"処理: backup_monthlyが完了しました")
        return True
    except subprocess.CalledProcessError as e:
        log(f"エラー: バックアップ/削除処理失敗: {e.stderr}")
        return False
    except OSError as e:
        log(f"エラー: ファイルシステム操作失敗: {e}")
        return False
    except Exception as e:
        log(f"エラー: backup_monthly処理中に予期せぬエラー: {e}")
        return False

def main():
    """メインループ"""
    i2c = smbus.SMBus(I2C_BUS)
    dat = DATA_BUFFER.copy()
    sensor_error_count = 0
    last_backup_day_run = None
    backup_day_first_write_done = False  # 追加: バックアップ日の初回書き込み済みフラグ（バグ修正用）

    if not initialize_sensor(i2c):
        log("センサー初期化失敗。次のサイクルを試行")
        time.sleep(INTERVAL_SECONDS)
        return

    while True:
        start_time = datetime.now()
        current_date = start_time.date()

        # 月初バックアップ処理
        if current_date.day == BACKUP_DAY and last_backup_day_run != current_date:
            log(f"処理: 月初バックアップ処理を開始")
            if backup_monthly():
                # バックアップ成功後、当月ファイルに最初のデータを書き込む（初回のみ）
                if not backup_day_first_write_done:
                    results = read_sensor_data(i2c, dat)
                    sensor_file = get_sensor_file()
                    if results:
                        try:
                            os.makedirs(os.path.dirname(sensor_file), exist_ok=True)
                            with open(sensor_file, "a") as f:
                                f.write(results + "\n")
                            log(f"センサー読み取り: {results}")
                            backup_day_first_write_done = True  # フラグセット
                        except OSError as e:
                            log(f"エラー: {sensor_file} 書き込み失敗: {e}")
                    else:
                        log("エラー: 月初バックアップ後、最初のセンサーデータ読み取りに失敗")
                
                # バックアップ成功を記録して、同じ日に再実行しないようにする
                last_backup_day_run = current_date
                
            else:
                log("警告: バックアップ処理に失敗しました。15分後に再試行します。")
                time.sleep(INTERVAL_SECONDS)
                continue # 次のループへ

        # 通常のセンサー読み取りとアップロード（バグ修正: 条件を削除し、無条件実行。バックアップ日は初回フラグで重複避け）
        # バックアップ日の場合、初回書き込み済みならスキップせず、以降ループで記録（15分ごと）
        if current_date.day != BACKUP_DAY or (current_date.day == BACKUP_DAY and backup_day_first_write_done):
            # バックアップ日以外 or バックアップ日で初回済み: 通常記録
            results = read_sensor_data(i2c, dat)
            sensor_file = get_sensor_file()
            if results:
                try:
                    os.makedirs(os.path.dirname(sensor_file), exist_ok=True)
                    with open(sensor_file, "a") as f:
                        f.write(results + "\n")
                    log(f"センサー読み取り: {results}")
                    sensor_error_count = 0
                except OSError as e:
                    log(f"エラー: {sensor_file} 書き込み失敗: {e}")
            else:
                sensor_error_count += 1
                if sensor_error_count >= MAX_I2C_ERRORS:
                    log("I2Cエラー上限到達。次のサイクルを試行")
                    sensor_error_count = 0
                    time.sleep(INTERVAL_SECONDS)
                    continue
        else:
            # バックアップ日で初回未済み（バックアップ失敗時など）: ここはスキップせず通常処理（上記ifでカバー）
            pass

        upload_latest()
        upload_full_history(get_sensor_file(), get_gdrive_file())  # 修正: GDRIVE_PATH を get_gdrive_file() に統一（ディレクトリ指定を避け、ファイルパスで正確アップロード）

        # 処理時間ログ
        process_time = (datetime.now() - start_time).total_seconds()
        log(f"処理時間: {process_time:.2f}秒")

        # 次のサイクルまで待機
        sleep_time = INTERVAL_SECONDS - process_time
        if sleep_time > 0:
            time.sleep(sleep_time)

        # リセット: 翌日になったらフラグクリア（バックアップ日フラグ）
        if current_date.day != BACKUP_DAY:
            backup_day_first_write_done = False

if __name__ == "__main__":
    main()