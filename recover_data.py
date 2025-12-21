import re
import os

# 読み込むログファイルのリスト
LOG_FILES = [
    "/home/hideo_81_g/logs/sensor_copier.log",       # v1系 (12/13以前)
    "/home/hideo_81_g/logs/sensor_copier_v2.log",    # v2系 (12/13〜12/20)
    "/home/hideo_81_g/logs/sensor_copier_v3.log"     # v3系 (念のため最新も)
]

# 復元データの出力先
OUTPUT_FILE = "recovered_temp_humid_2025-12.txt"

# 抽出対象の年月 (2025-12 のデータのみを抽出)
TARGET_MONTH_PREFIX = "2025-12"

def main():
    data_set = set()
    
    # 正規表現: "月次ファイルに追記: " の後ろのデータを取得
    # v1ログ: "... - INFO - 月次ファイルに追記: 2025-..."
    # v2/v3ログ: "... - INFO - RAMバッファの月次ファイルに追記: 2025-..."
    pattern = re.compile(r"月次ファイルに追記:\s*(.*)")

    print("ログ解析とデータ抽出を開始します...")

    for log_path in LOG_FILES:
        if not os.path.exists(log_path):
            print(f"スキップ (ファイルなし): {log_path}")
            continue
        
        print(f"読み込み中: {log_path}")
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    match = pattern.search(line)
                    if match:
                        data_part = match.group(1).strip()
                        
                        # データの簡易検証 (2025-12のデータで、CSV形式か)
                        if data_part.startswith(TARGET_MONTH_PREFIX) and ",tmp=" in data_part and ",hum=" in data_part:
                            data_set.add(data_part)
        except Exception as e:
            print(f"エラー ({log_path}): {e}")

    # タイムスタンプ順にソート
    sorted_data = sorted(list(data_set))

    print(f"抽出データ件数: {len(sorted_data)} 件")

    if sorted_data:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted_data) + "\n")
        print(f"復旧完了！ファイルを作成しました: {OUTPUT_FILE}")
        print(f"内容を確認後、以下のコマンドで適用してください:\n"
              f"cp {OUTPUT_FILE} /home/hideo_81_g/sensor_data/temp_humid_2025-12.txt")
    else:
        print("復旧対象のデータが見つかりませんでした。")

if __name__ == "__main__":
    main()