import pandas as pd
from sqlalchemy import create_engine
import mysql.connector

# データファイルのパス
data_file = '/Users/kataokahideo/Desktop/Summer2025/temp_humid_2025-08.txt'

# --- MySQL接続設定 ---
DB_CONFIG = {
    'user': 'root',
    'password': '19800801',
    'host': 'localhost',
    'database': 'sensor_data_db'
}
engine = create_engine(f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}")
# --- 設定ここまで ---

# DBから最新のタイムスタンプを取得
last_timestamp = None
try:
    cnx = mysql.connector.connect(**DB_CONFIG)
    cursor = cnx.cursor()
    cursor.execute("SELECT MAX(timestamp) FROM sensor_data")
    result = cursor.fetchone()
    if result and result[0]:
        last_timestamp = pd.to_datetime(result[0])
    print(f"データベース内の最新時刻: {last_timestamp}")
    cursor.close()
    cnx.close()
except mysql.connector.Error as e:
    print(f"MySQLエラー: {e}")

# チャンク処理で大量データをインポート
chunksize = 10000  # 1万行ずつ処理（メモリ節約）
total_inserted = 0
print("ファイルの読み込みとインポートを開始します...")
for chunk_raw in pd.read_csv(data_file, names=['datetime_str', 'temperature_str', 'humidity_str'],
                             chunksize=chunksize, na_filter=False, skip_blank_lines=True):
    # --- データ前処理 ---
    chunk = chunk_raw.copy()
    chunk['timestamp'] = pd.to_datetime(chunk['datetime_str'], errors='coerce')
    chunk['temperature'] = chunk['temperature_str'].str.split('=').str[1].astype(float).round(2)
    chunk['humidity'] = chunk['humidity_str'].str.split('=').str[1].astype(float).round(2)
    
    chunk = chunk[['timestamp', 'temperature', 'humidity']].dropna()
    # --- 前処理ここまで ---

    if last_timestamp:
        chunk = chunk[chunk['timestamp'] > last_timestamp]
    
    if not chunk.empty:
        chunk.to_sql('sensor_data', engine, if_exists='append', index=False)
        total_inserted += len(chunk)
        print(f"  インポート成功: {len(chunk)}行")

print(f"\n全データインポート完了。合計 {total_inserted} 行が挿入されました。")