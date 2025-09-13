import pandas as pd
import mysql.connector
import subprocess
import os
import glob
import datetime
import logging

# --- 設定項目 ---
RCLONE_REMOTE = 'raspi_data'
GDRIVE_SENSOR_DIR = 'sensor_data/'
LOCAL_DOWNLOAD_DIR = '/Users/kataokahideo/sensor_data_downloads/'
LOG_FILE = '/Users/kataokahideo/プログラミング/MySQL連携/import_log.txt'  # ログパス変更

DB_CONFIG_MAC = {
    'host': 'localhost',
    'user': 'root',
    'password': '19800801',  # ここをrootパスワードに変更
    'database': 'sensor_data_db'
}
# --- 設定項目ここまで ---

# ログ設定
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)  # ログディレクトリを確保
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s: %(message)s')
os.makedirs(LOCAL_DOWNLOAD_DIR, exist_ok=True)
logging.info(f"ローカルダウンロードディレクトリ: {LOCAL_DOWNLOAD_DIR}")

def check_rclone_config():
    """rclone設定の確認"""
    try:
        subprocess.run(['rclone', 'config', 'show', RCLONE_REMOTE], capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        logging.error(f"rcloneのリモート '{RCLONE_REMOTE}' が未設定。`rclone config`で設定してください。")
        print(f"エラー: rcloneの '{RCLONE_REMOTE}' が未設定。`rclone config`で設定。")
        return False

def download_files_from_gdrive():
    """Google Driveからセンサーデータをダウンロード"""
    logging.info(f"Google Driveからダウンロード: {RCLONE_REMOTE}:{GDRIVE_SENSOR_DIR} -> {LOCAL_DOWNLOAD_DIR}")
    print(f"\nGoogle Driveからダウンロード中...")
    if not check_rclone_config():
        return False
    try:
        subprocess.run(['rclone', 'sync', '-v', '--progress',
                        f'{RCLONE_REMOTE}:{GDRIVE_SENSOR_DIR}', LOCAL_DOWNLOAD_DIR], check=True)
        logging.info("ファイルは正常にダウンロード/同期されました。")
        print("ダウンロード完了！")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"ダウンロード失敗: {e}")
        print(f"エラー: ダウンロード失敗: {e}")
        return False
    except FileNotFoundError:
        logging.error("rcloneが未インストール。`brew install rclone`でインストール。")
        print("エラー: rcloneが未インストール。`brew install rclone`でインストール。")
        return False

def process_and_insert_data():
    """ダウンロードしたファイルをMySQLに挿入"""
    logging.info("データ処理を開始")
    print("\nファイルを処理し、MySQLに挿入...")
    files_processed_count = 0
    data_inserted_count = 0
    
    # 最新のtimestampを取得
    try:
        cnx = mysql.connector.connect(**DB_CONFIG_MAC)
        cursor = cnx.cursor()
        cursor.execute("SELECT MAX(timestamp) FROM measurements")
        last_timestamp = cursor.fetchone()[0]
        cursor.close()
        cnx.close()
        logging.info(f"最新timestamp: {last_timestamp}")
    except mysql.connector.Error as e:
        logging.error(f"MySQL接続エラー: {e}")
        print(f"エラー: MySQL接続失敗: {e}")
        return

    for filepath in glob.glob(os.path.join(LOCAL_DOWNLOAD_DIR, 'temp_humid_*.txt')):
        logging.info(f"ファイル処理中: {filepath}")
        print(f"  ファイル '{filepath}' を処理中...")
        try:
            # データ読み込み
            df = pd.read_csv(filepath, header=None, names=['datetime_str', 'temperature_str', 'humidity_str'])
            df = df[df['temperature_str'].str.match(r'tmp=\d+\.\d') & df['humidity_str'].str.match(r'hum=\d+\.\d')]
            df['datetime'] = pd.to_datetime(df['datetime_str'], errors='coerce')
            df['temperature'] = df['temperature_str'].str.split('=').str[1].astype(float).round(2)
            df['humidity'] = df['humidity_str'].str.split('=').str[1].astype(float).round(2)
            df = df[['datetime', 'temperature', 'humidity']].dropna()
            df = df[(df['temperature'].between(0, 50)) & (df['humidity'].between(0, 100))]

            # 最新timestamp以降のデータ
            if last_timestamp:
                df = df[df['datetime'] > last_timestamp]
            if df.empty:
                logging.info(f"ファイル '{filepath}' に新しいデータなし。スキップ。")
                print(f"    新しいデータなし。スキップ。")
                continue

            # MySQL挿入
            cnx = mysql.connector.connect(**DB_CONFIG_MAC)
            cursor = cnx.cursor()
            insert_query = """
            INSERT INTO measurements (timestamp, temperature, humidity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                temperature = VALUES(temperature),
                humidity = VALUES(humidity);
            """
            data_to_insert = [tuple(row) for row in df.values]
            cursor.executemany(insert_query, data_to_insert)
            cnx.commit()
            logging.info(f"ファイル '{filepath}' から {cursor.rowcount} 行を挿入/更新")
            print(f"    {cursor.rowcount} 行を挿入/更新")
            data_inserted_count += cursor.rowcount
            files_processed_count += 1
            cursor.close()
            cnx.close()

        except Exception as e:
            logging.error(f"ファイル '{filepath}' の処理失敗: {e}")
            print(f"  エラー: 処理失敗: {e}")

    if files_processed_count == 0:
        logging.info("新しいファイルまたはデータなし")
        print("新しいファイルまたはデータなし。")
    else:
        logging.info(f"合計処理ファイル数: {files_processed_count}、合計挿入/更新行数: {data_inserted_count}")
        print(f"\n合計処理ファイル数: {files_processed_count}、合計挿入/更新行数: {data_inserted_count}")

# メイン処理
if download_files_from_gdrive():
    process_and_insert_data()
    print("\nデータ同期と挿入処理が完了しました。")
else:
    print("\nダウンロード失敗。処理をスキップ。")