import argparse
import logging
import os
import glob
import subprocess
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# ログ設定（ファイル出力、コンソール両対応）
LOG_DIR = os.path.expanduser('~/logs')  # デフォルトログディレクトリ
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'importer.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()  # コンソール出力も追加
    ]
)
logger = logging.getLogger(__name__)

def get_config():
    """設定情報を環境変数から一元取得（config.py相当）"""
    password = os.environ.get('DB_PASSWORD')
    if not password:
        logger.warning("環境変数 'DB_PASSWORD' が設定されていません。")
    return {
        'rclone_remote': os.environ.get('RCLONE_REMOTE', 'raspi_data'),
        'gdrive_sensor_dir': os.environ.get('GDRIVE_SENSOR_DIR', 'sensor_data/'),
        'local_download_dir': os.environ.get('LOCAL_DOWNLOAD_DIR', os.path.expanduser('~/sensor_data_downloads/')),
        'db': {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'user': os.environ.get('DB_USER', 'root'),
            'password': password,
            'database': os.environ.get('DB_NAME', 'sensor_data_db')
        }
    }

def check_rclone_config(remote):
    """rclone設定確認"""
    try:
        subprocess.run(['rclone', 'config', 'show', remote], capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError:
        logger.error(f"rcloneのリモート '{remote}' が未設定。`rclone config`で設定してください。")
        return False
    except FileNotFoundError:
        logger.error("rcloneが未インストール。`brew install rclone`などでインストールしてください。")
        return False

def download_from_gdrive(config):
    """Google Driveから同期ダウンロード（オプション）"""
    logger.info(f"Google Driveからダウンロード: {config['rclone_remote']}:{config['gdrive_sensor_dir']} -> {config['local_download_dir']}")
    print("\nGoogle Driveからダウンロード中...")
    os.makedirs(config['local_download_dir'], exist_ok=True)
    
    if not check_rclone_config(config['rclone_remote']):
        return False
    
    try:
        subprocess.run([
            'rclone', 'sync', '-v', '--progress',
            f"{config['rclone_remote']}:{config['gdrive_sensor_dir']}", config['local_download_dir']
        ], check=True)
        logger.info("ファイル同期完了。")
        print("ダウンロード完了！")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"ダウンロード失敗: {e}")
        print(f"エラー: ダウンロード失敗: {e}")
        return False

def get_last_timestamp(engine):
    """DBから最新タイムスタンプ取得"""
    last_timestamp = None
    try:
        with engine.connect() as connection:
            query = text("SELECT MAX(timestamp) FROM sensor_data")
            result = connection.execute(query).fetchone()
            if result and result[0]:
                last_timestamp = pd.to_datetime(result[0])
            logger.info(f"データベース内の最新時刻: {last_timestamp}")
    except Exception as e:
        logger.error(f"MySQLエラー: {e}")
    return last_timestamp

def preprocess_data(df_raw, chunksize=None):
    """データ前処理（共通関数: フィルタ、抽出、範囲チェック）"""
    if chunksize:
        # チャンク処理モード（大容量ファイル用）
        processed_chunks = []
        for chunk in df_raw:
            chunk_processed = _preprocess_single_chunk(chunk)
            if not chunk_processed.empty:
                processed_chunks.append(chunk_processed)
        return pd.concat(processed_chunks, ignore_index=True) if processed_chunks else pd.DataFrame()
    else:
        return _preprocess_single_chunk(df_raw)

def _preprocess_single_chunk(chunk):
    """単一チャンクの前処理（内部関数）"""
    try:
        chunk_copy = chunk.copy()
        # 正規表現フィルタ: 有効ログ行のみ
        chunk_copy = chunk_copy[
            chunk_copy['temperature_str'].str.match(r'tmp=\d+\.\d', na=False) &
            chunk_copy['humidity_str'].str.match(r'hum=\d+\.\d', na=False)
        ]
        
        chunk_copy['timestamp'] = pd.to_datetime(chunk_copy['datetime_str'], errors='coerce')
        chunk_copy['temperature'] = chunk_copy['temperature_str'].str.split('=').str[1].astype(float).round(2)
        chunk_copy['humidity'] = chunk_copy['humidity_str'].str.split('=').str[1].astype(float).round(2)
        
        chunk_copy = chunk_copy[['timestamp', 'temperature', 'humidity']].dropna()
        
        # 範囲チェック: 異常値除去
        chunk_copy = chunk_copy[
            (chunk_copy['temperature'].between(0, 50)) &
            (chunk_copy['humidity'].between(0, 100))
        ]
        
        logger.debug(f"前処理後: {len(chunk_copy)}行")
        return chunk_copy
    except Exception as e:
        logger.error(f"前処理エラー: {e}")
        return pd.DataFrame()

def insert_to_db(df, engine):
    """DB挿入（UPSERT） - SQLAlchemy 2.0 スタイル"""
    if df.empty:
        return 0
    
    inserted_count = 0
    try:
        data_dicts = df.to_dict(orient='records')
        
        with engine.connect() as connection:
            insert_query = text("""
            INSERT INTO sensor_data (timestamp, temperature, humidity)
            VALUES (:timestamp, :temperature, :humidity)
            ON DUPLICATE KEY UPDATE
                temperature = VALUES(temperature),
                humidity = VALUES(humidity);
            """)
            result = connection.execute(insert_query, data_dicts)
            connection.commit()
            inserted_count = result.rowcount
            logger.info(f"{inserted_count} 行を挿入/更新しました。")
            print(f"    {inserted_count} 行を挿入/更新しました。")
    except Exception as e:
        logger.error(f"DB挿入エラー: {e}")
    
    return inserted_count

def process_files(filepaths, engine, last_timestamp, chunksize=None):
    """ファイル/ディレクトリ処理（複数/単一対応）"""
    if isinstance(filepaths, str) and os.path.isdir(filepaths):
        filepaths = glob.glob(os.path.join(filepaths, 'temp_humid_*.txt'))
    
    if not isinstance(filepaths, list):
        filepaths = [filepaths]
    
    total_files = 0
    total_inserted = 0
    
    for filepath in filepaths:
        if not os.path.exists(filepath):
            logger.warning(f"ファイルが存在しません: {filepath}")
            continue
        
        logger.info(f"ファイルを処理中: {filepath}")
        print(f"  ファイルを処理中: '{filepath}'...")
        
        try:
            if chunksize:
                df_raw_chunks = pd.read_csv(
                    filepath, names=['datetime_str', 'temperature_str', 'humidity_str'],
                    chunksize=chunksize, na_filter=False, skip_blank_lines=True
                )
                df = preprocess_data(df_raw_chunks, chunksize=chunksize)
            else:
                df_raw = pd.read_csv(
                    filepath, header=None, names=['datetime_str', 'temperature_str', 'humidity_str'],
                    na_filter=False, skip_blank_lines=True
                )
                df = preprocess_data(df_raw)

            if df.empty:
                logger.info(f"ファイル '{filepath}' に処理可能なデータがありません。")
                continue

            if last_timestamp:
                df = df[df['timestamp'] > last_timestamp]

            if df.empty:
                logger.info(f"ファイル '{filepath}' に新しいデータがありません。スキップします。")
                continue
            
            inserted = insert_to_db(df, engine)
            total_inserted += inserted
            if inserted > 0:
                total_files += 1
        
        except Exception as e:
            logger.error(f"ファイル処理中にエラーが発生しました '{filepath}': {e}")
            print(f"  エラー: 処理に失敗しました: {e}")
    
    logger.info(f"合計処理ファイル数: {total_files}、合計挿入/更新行数: {total_inserted}")
    print(f"\n合計処理ファイル数: {total_files}、合計挿入/更新行数: {total_inserted}")
    return total_inserted

def show_summary(engine):
    """インポート後統計表示"""
    try:
        query = text("SELECT AVG(temperature) as avg_temp, AVG(humidity) as avg_humid, COUNT(*) as total_rows FROM sensor_data")
        df_summary = pd.read_sql(query, engine)
        if not df_summary.empty:
            stats = df_summary.iloc[0]
            logger.info(f"全体統計: 総行数={stats['total_rows']:,}, 平均温度={stats['avg_temp']:.2f}℃, 平均湿度={stats['avg_humid']:.2f}%")
            print(f"\n全体統計: 総行数={stats['total_rows']:,}, 平均温度={stats['avg_temp']:.2f}℃, 平均湿度={stats['avg_humid']:.2f}%")
    except Exception as e:
        logger.warning(f"統計取得エラー: {e}")

def main():
    parser = argparse.ArgumentParser(description='温湿度データ統合インポーター（GDrive/ローカル対応）')
    parser.add_argument('--no-download', action='store_true', help='Google Driveダウンロードをスキップ')
    parser.add_argument('--source', type=str, help='処理対象: ファイルパス or ディレクトリパス（指定時はダウンロード無視）')
    parser.add_argument('--chunksize', type=int, default=None, help='チャンクサイズ（大容量ファイル用、デフォルト: 全読み込み）')
    args = parser.parse_args()
    
    config = get_config()
    logger.info(f"処理開始: {datetime.now()}")
    
    filepaths = None
    if args.source:
        filepaths = args.source
        logger.info(f"ローカルソースを指定: {filepaths}")
    elif not args.no_download:
        if download_from_gdrive(config):
            filepaths = config['local_download_dir']
    else:  # --no-download が指定され、--source は指定されていない
        filepaths = config['local_download_dir']
        logger.info(f"ローカルディレクトリを処理対象とします: {filepaths}")
    
    if not filepaths:
        logger.warning("処理対象のファイルまたはディレクトリが見つかりませんでした。処理を終了します。")
        print("処理対象なし。終了。")
        return
    
    db_config = config['db']
    if not db_config.get('password'):
        logger.error("データベースのパスワードが設定されていません。環境変数 'DB_PASSWORD' を設定してください。")
        return

    # SQLAlchemyエンジン作成
    db_uri = f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}/{db_config['database']}"
    engine = create_engine(db_uri)

    last_timestamp = get_last_timestamp(engine)
    total_inserted = process_files(filepaths, engine, last_timestamp, args.chunksize)
    
    if total_inserted > 0:
        show_summary(engine)
    
    logger.info(f"処理完了: 合計 {total_inserted} 行を挿入/更新しました。")
    print("\nデータ同期と挿入処理が完了しました。")

if __name__ == "__main__":
    main()
