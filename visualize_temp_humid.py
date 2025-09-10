import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt

# MySQL接続
engine = create_engine('mysql+pymysql://root:19800801@localhost/sensor_data_db')

# データを取得（湿度も追加）
# SQLビューで計算済みの`hour`列を直接利用し、Pythonでの冗長な計算をなくします。
# これによりコードがDRYになり、効率も向上します。
query = "SELECT source, hour, temperature, humidity FROM hourly_data_separate;"
df = pd.read_sql(query, engine)
df1 = df[df['source'] == 'measurements']
df2 = df[df['source'] == 'sensor_data']

# グラフ作成（上下2段に分割）
# sharex=Trueで上下のグラフのX軸（時間）を連動させます
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

# --- 上段: 温度のグラフ ---
ax1.scatter(df1['hour'], df1['temperature'], color='blue', alpha=0.5, s=10, label='July (Measurements)')
ax1.scatter(df2['hour'], df2['temperature'], color='red', alpha=0.5, s=10, label='August (Sensor Data)')
ax1.set_title('Temperature Variation Across Hours')
ax1.set_ylabel('Temperature (°C)')
ax1.set_ylim(25, 32)  # 温度範囲を調整
ax1.legend()
ax1.grid(True)

# --- 下段: 湿度のグラフ ---
ax2.scatter(df1['hour'], df1['humidity'], color='green', alpha=0.5, s=10, label='July (Measurements)')
ax2.scatter(df2['hour'], df2['humidity'], color='orange', alpha=0.5, s=10, label='August (Sensor Data)')
ax2.set_title('Humidity Variation Across Hours')
ax2.set_xlabel('Hour of Day (0:00 to 24:00)')
ax2.set_ylabel('Humidity (%)')
ax2.legend()
ax2.grid(True)

# 全体の設定
fig.suptitle('Temperature and Humidity Comparison (July vs August 2025)', fontsize=16)
ax2.set_xticks(range(0, 25, 2))  # X軸の目盛は下段のグラフにのみ設定

# レイアウトを自動調整して、タイトルやラベルが重ならないようにします
plt.tight_layout()
# suptitleと上段グラフのタイトルが重なる場合があるので、さらに調整します
plt.subplots_adjust(top=0.94)
plt.show()