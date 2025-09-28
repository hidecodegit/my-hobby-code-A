import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Hiragino Sans' # ★ 日本語の文字化け対策
import matplotlib.animation as animation
from matplotlib.collections import LineCollection
import imageio
import os
from datetime import datetime, timedelta

# --- ステップ1 & 2: データの準備 ---
# 実際のファイルパスに置き換えてください
file_path = '/Users/kataokahideo/sensor_data_downloads/temp_humid_2025-08.txt'

# read_csvで直接パース
df_raw = pd.read_csv(
    file_path,
    header=None,
    names=['datetime_str', 'tmp_str', 'hum_str']
)

# データ前処理
df_raw['datetime'] = pd.to_datetime(df_raw['datetime_str'], errors='coerce')
df_raw['tmp'] = pd.to_numeric(df_raw['tmp_str'].str.extract(r'(\d+\.\d)')[0], errors='coerce')
df_raw['hum'] = pd.to_numeric(df_raw['hum_str'].str.extract(r'(\d+\.\d)')[0], errors='coerce')

df = df_raw[['datetime', 'tmp', 'hum']].dropna().sort_values('datetime').reset_index(drop=True)

# 8月1日から31日までのデータを抽出
start_date = datetime(2025, 8, 1)
end_date = start_date + timedelta(days=31) # 31日分を対象にする
df = df[(df['datetime'] >= start_date) & (df['datetime'] < end_date)].copy() # SettingWithCopyWarningを回避

# ★ データの最小・最大温度を動的に取得
min_temp = df['tmp'].min()
max_temp = df['tmp'].max()

# 螺旋軌跡のための列を計算
df['total_hours'] = (df['datetime'] - start_date) / timedelta(hours=1)
# ★ 半径を動的な温度範囲で正規化（オフセットは削除）
df['r'] = (df['tmp'] - min_temp) / (max_temp - min_temp)

# 角度は累積時間で計算
df['theta'] = 2 * np.pi * df['total_hours'] / 24

# --- ステップ3: アニメーションの準備 ---
POINTS_PER_FRAME = 72
TOTAL_DAYS = 31 # 31日分に変更
NUM_FRAMES = int(np.ceil(len(df) / POINTS_PER_FRAME)) + 1

fig = plt.figure(figsize=(8, 8))
ax = fig.add_subplot(111, projection='polar')
line_collection = LineCollection([], cmap='viridis', lw=1.5, alpha=0.6) # ★ 透明度を上げて見やすくする
ax.add_collection(line_collection)

# カラーバー用の設定
sm = plt.cm.ScalarMappable(cmap='viridis', norm=plt.Normalize(vmin=df['hum'].min(), vmax=df['hum'].max()))
cbar = fig.colorbar(sm, ax=ax, pad=0.1) # padでカラーバーとプロットの間隔を調整
cbar.set_label('Humidity (%)', weight='bold')

# ★ Grok提案3: 進行バー用のテキストオブジェクトを初期化
progress_text = fig.text(0.5, 0.02, '', ha='center', transform=fig.transFigure, fontsize=10)

# ★ 左上の注釈をプロット外に一度だけ描画
fig.suptitle('Temperature & Humidity Spiral (August 2025)', fontsize=16, weight='bold')
fig.text(0.05, 0.92, f'Radius: Temp ({min_temp:.1f}-{max_temp:.1f}°C)', transform=fig.transFigure)
fig.text(0.05, 0.89, 'Color: Humidity', transform=fig.transFigure)

# --- ステップ4: 各フレームの描画関数 ---
def animate(n):
    ax.set_rlim(0, 1.2) # ★ 半径の上限を1.2に
    ax.set_rticks([0.25, 0.5, 0.75, 1.0])
    ax.set_rlabel_position(22.5)
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # ★ 円周のラベルを角度から時刻に変更
    hours = np.arange(0, 24, 3)
    hour_labels = [f'{h}:00' for h in hours]
    hour_angles = hours * 2 * np.pi / 24
    ax.set_xticks(hour_angles)
    ax.set_xticklabels(hour_labels)
    
    end_index = min(n * POINTS_PER_FRAME, len(df))
    data_subset = df.iloc[:end_index]
    
    if data_subset.empty:
        ax.set_title("開始: 温度・湿度 螺旋軌跡 (2025/08)")
        return

    theta = data_subset['theta'].values
    r = data_subset['r'].values
    humidity = data_subset['hum'].values
    
    if len(theta) < 2:
        return

    points = np.array([theta, r]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    
    line_collection.set_segments(segments)
    segment_colors = (humidity[:-1] + humidity[1:]) / 2
    line_collection.set_array(segment_colors)

    current_date = start_date + timedelta(hours=data_subset['total_hours'].iloc[-1])
    ax.set_title(f'Date: {current_date.strftime("%Y-%m-%d %H:%M")} | Points: {len(data_subset)}', y=1.05)
    
    # ★ Grok提案3: 進行バーを更新
    progress_text.set_text(f'Progress: {n}/{NUM_FRAMES-1}')

# --- ステップ5: アニメーション生成とGIF/PNG出力 ---
ani = animation.FuncAnimation(fig, animate, frames=NUM_FRAMES, interval=50, blit=False)

# 成果物の保存先ディレクトリを設定
output_dir = '/Users/kataokahideo/Desktop/Summer2025/Results'
os.makedirs(output_dir, exist_ok=True)

output_gif_path = os.path.join(output_dir, 'temperature_humidity_spiral_enhanced.gif')
print(f"アニメーションを生成し、'{output_gif_path}' に保存します...")

# PillowWriterオブジェクトを作成し、durationとloopを直接渡す
writer = animation.PillowWriter(fps=20)
ani.save(output_gif_path, writer=writer, dpi=100) # dpiを指定してファイルサイズを調整
print("保存が完了しました。")

# 最終フレームをPNGで保存
final_png_path = os.path.join(output_dir, 'final_spiral_enhanced.png')
# ★ Grok提案4: bbox_inches='tight'で余白を最適化
fig.savefig(final_png_path, dpi=150, bbox_inches='tight')
print(f"最終フレームを '{final_png_path}' に保存しました。")
