#!/bin/bash
# backup.sh: 手動バックアップ用スクリプト (Grok提案)
# 再起動前やメンテナンス前に実行してください

echo "--- 手動バックアップ開始 ---"

# 1. RAMディスクの内容をバックアップ用ディレクトリに退避
BACKUP_DIR="/home/hideo_81_g/sensor_data_backup"
mkdir -p "$BACKUP_DIR"
if [ -d "/tmp/sensor_data" ]; then
    rsync -av /tmp/sensor_data/ "$BACKUP_DIR/"
    echo "ローカルバックアップ完了: $BACKUP_DIR"
else
    echo "警告: RAMディスク(/tmp/sensor_data)が見つかりません"
fi

# 2. 永続領域をクラウド(Googleドライブ)へ同期
# bwlimitを設定して帯域制限
echo "クラウド同期を開始します..."
rclone sync /home/hideo_81_g/sensor_data raspi_data:/sensor_data/ --bwlimit 200k --progress

echo "--- バックアップ終了 ---"