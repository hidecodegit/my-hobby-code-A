#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime, timedelta
import os
import smbus

# 定数設定
LOG_FILE = "/tmp/20250901_LatestToGdrive.log"
LATEST_FILE = "/tmp/latest_temp_humid.txt"
BACKUP_DIR = "/home/hideo_81_g/sensor_data"
GDRIVE_PATH = "raspi_data:/sensor_data"
INTERVAL_SECONDS = 15 * 60
I2C_BUS = 1
SENSOR_ADDRESS = 0x38
TRIGGER_COMMAND = [0xAC, 0x33, 0x00]
DATA_BUFFER = [0x00] * 7
MAX_I2C_ERRORS = 3
BACKUP_DAY = 1  # 月初1日にバックアップ実行（信頼性確保のため1日中の試行）

def get_sensor_file():
    """現在の年月に基づくSENSOR_FILEのパス"""
    return f"/tmp/temp_humid_{datetime.now().strftime('%Y-%m')}.txt"

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
    """センサー初期化（20250728踏襲）"""
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
    """センサーからデータ読み取り（20250728踏襲）"""
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
    """SENSOR_FILEの最新行を取得（20250824踏襲）"""
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
    """最新データをLATEST_FILEに書き出し、Google Driveにアップロード（20250824踏襲）"""
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

def upload_full_history():
    """全履歴をGoogle Driveにアップロード"""
    sensor_file = get_sensor_file()
    gdrive_file = get_gdrive_file()
    if not os.path.exists(sensor_file):
        log(f"エラー: {sensor_file} が見つかりません")
        return False
    try:
        cmd = ["rclone", "copy", sensor_file, GDRIVE_PATH, "--checksum", "--no-traverse", "--bwlimit", "200k"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        log(f"処理: 全履歴アップロードOK: {gdrive_file}")
        return True
    except subprocess.CalledProcessError as e:
        log(f"エラー: rclone copy失敗 (full): {e.stderr}")
        return False

def backup_monthly():
    """前月データをSDカードとGoogleドライブにバックアップ（月初1日に実行）"""
    now = datetime.now()
    if now.day != BACKUP_DAY:  # 月初1日に限定（信頼性確保のため1日中試行）
        return False
    last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    sensor_file = get_sensor_file()
    backup_file = f"{BACKUP_DIR}/temp_humid_{last_month}.txt"
    gdrive_backup_file = get_gdrive_file(last_month)

    try:
        if not os.path.exists(sensor_file) or os.path.getsize(sensor_file) == 0:
            return False  # データがない場合はスキップ

        # 前月データのみを一時ファイルに抽出
        temp_file = f"/tmp/temp_humid_{last_month}_temp.txt"
        data_found = False
        with open(sensor_file, "r") as f, open(temp_file, "w") as temp_f:
            for line in f:
                if line.startswith(f"{last_month}-"):
                    temp_f.write(line)
                    data_found = True
        if not data_found:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False  # 前月データがない場合はスキップ

        # SDカードにバックアップ
        os.makedirs(BACKUP_DIR, exist_ok=True)
        try:
            cmd = ["cp", temp_file, backup_file]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            log(f"エラー: SDカードバックアップ失敗: {e.stderr}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False

        # Googleドライブにバックアップ
        try:
            cmd = ["rclone", "copy", temp_file, gdrive_backup_file, "--checksum", "--no-traverse", "--bwlimit", "200k"]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            log(f"エラー: Googleドライブバックアップ失敗: {e.stderr}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False

        # 一時ファイル削除
        if os.path.exists(temp_file):
            os.remove(temp_file)

        # SENSOR_FILEから前月データを削除
        try:
            with open(sensor_file, "r") as f:
                lines = [line for line in f if not line.startswith(f"{last_month}-")]
            with open(sensor_file, "w") as f:
                f.writelines(lines)
            log(f"処理: backup_monthlyが完了しました")
            return True
        except OSError as e:
            log(f"エラー: {sensor_file} リセット失敗: {e}")
            return False
    except Exception as e:
        log(f"エラー: backup_monthly処理中にエラー: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False

def main():
    """メインループ"""
    i2c = smbus.SMBus(I2C_BUS)
    dat = DATA_BUFFER.copy()
    sensor_error_count = 0
    last_backup_month = datetime.now().strftime("%Y-%m")

    if not initialize_sensor(i2c):
        log("センサー初期化失敗。次のサイクルを試行")
        time.sleep(INTERVAL_SECONDS)
        return

    while True:
        start_time = datetime.now()
        next_time = start_time + timedelta(seconds=INTERVAL_SECONDS)
        log(f"処理: 開始, 次の処理: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # センサー読み取り
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
                continue

        # 最新データと全履歴をアップロード
        upload_latest()
        upload_full_history()

        # 月初バックアップ
        current_month = datetime.now().strftime("%Y-%m")
        if current_month != last_backup_month:
            if backup_monthly():
                last_backup_month = current_month

        # 処理時間ログ
        process_time = (datetime.now() - start_time).total_seconds()
        log(f"処理時間: {process_time:.2f}秒")

        # 次のサイクルまで待機
        sleep_time = INTERVAL_SECONDS - process_time
        if sleep_time > 0:
            time.sleep(sleep_time)

if __name__ == "__main__":
    main()
