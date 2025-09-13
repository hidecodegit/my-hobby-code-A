import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
import matplotlib.patches as mpatches # 凡例を自作するためにインポート

def plot_statistics(ax, df: pd.DataFrame, metric: str, color: str, label_prefix: str,
                   bin_interval: float = 0.25, density_alpha: float = 0.3):
    """
    指定された軸に統計情報をプロットする。
    背景に2次元密度プロット（データの密集度）、前面に平均線と中央値を描画。
    
    Parameters:
    - ax: Matplotlibの軸オブジェクト
    - df: データフレーム（source, hour, temperature, humidityを含む）
    - metric: プロット対象の列（'temperature'または'humidity'）
    - color: プロットの色（例：'blue'）
    - label_prefix: 凡例の接頭辞（例：'July'）
    - bin_interval: 時間ビニングの間隔（例：0.25=15分）
    - density_alpha: 密度プロットの透明度（0～1）
    """
    # ビニング：hourを指定間隔（例：0.25時間=15分）で区切り、平均/中央値を計算
    binned_hour = (df['hour'] // bin_interval * bin_interval).round(2)
    df_mean = df.groupby(binned_hour)[metric].mean().reset_index()
    df_median = df.groupby(binned_hour)[metric].median().reset_index()

    # 2次元密度プロット：時間（hour）と値（metric）の密集度を濃淡で表現
    sns.kdeplot(x=df['hour'], y=df[metric], cmap=f'{color.capitalize()}s', fill=True, alpha=density_alpha, ax=ax)
    
    # 平均線（実線）：時間ごとの平均値を接続
    ax.plot(df_mean['hour'], df_mean[metric], color=color, linestyle='-', linewidth=2.5, label=f'{label_prefix} Mean')
    # 中央値線（破線）：時間ごとの中央値を接続
    ax.plot(df_median['hour'], df_median[metric], color=color, linestyle='--', linewidth=2.5, label=f'{label_prefix} Median')

# --- メイン処理 ---
# MySQL接続
engine = create_engine('mysql+pymysql://root:19800801@localhost/sensor_data_db')
query = "SELECT source, hour, temperature, humidity FROM hourly_data_separate;"
df = pd.read_sql(query, engine)
df1 = df[df['source'] == 'measurements']  # 7月
df2 = df[df['source'] == 'sensor_data']   # 8月

# 外れ値リスト（例：温度35℃以上）の抽出と表示
outliers = df[df['temperature'] >= 35][['source', 'hour', 'temperature']]
if not outliers.empty:
    print("--- Temperature Outliers (>=35°C) Detected ---")
    print(outliers)
    print("--------------------------------------------")

# グラフ作成
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), sharex=True)

# --- 温度グラフ ---
plot_statistics(ax1, df1, 'temperature', 'blue', 'July')
plot_statistics(ax1, df2, 'temperature', 'red', 'August')
ax1.set_title('Temperature Variation Across Hours (Density, Mean, Median)')
ax1.set_ylabel('Temperature (°C)')
ax1.set_ylim(25, 32)
handles, labels = ax1.get_legend_handles_labels()
handles += [mpatches.Patch(color='blue', alpha=0.3, label='July Density'),
            mpatches.Patch(color='red', alpha=0.3, label='August Density')]
ax1.legend(handles=sorted(handles, key=lambda h: h.get_label()), loc='upper left', fontsize=9)
ax1.grid(True, linestyle='--', alpha=0.4)

# --- 湿度グラフ ---
plot_statistics(ax2, df1, 'humidity', 'green', 'July')
plot_statistics(ax2, df2, 'humidity', 'orange', 'August')
ax2.set_title('Humidity Variation Across Hours (Density, Mean, Median)')
ax2.set_xlabel('Hour of Day (0:00 to 24:00)')
ax2.set_ylabel('Humidity (%)')
ax2.set_ylim(45, 75)
ax2.set_xticks(range(0, 25, 2))
handles, labels = ax2.get_legend_handles_labels()
handles += [mpatches.Patch(color='green', alpha=0.3, label='July Density'),
            mpatches.Patch(color='orange', alpha=0.3, label='August Density')]
ax2.legend(handles=sorted(handles, key=lambda h: h.get_label()), loc='upper left', fontsize=9)
ax2.grid(True, linestyle='--', alpha=0.4)

# --- 全体の設定 ---
fig.suptitle('Temperature and Humidity Analysis (July vs August 2025)', fontsize=18, weight='bold')
plt.tight_layout()
plt.subplots_adjust(top=0.94)
plt.show()