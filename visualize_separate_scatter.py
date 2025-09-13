import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt

# MySQL接続
engine = create_engine('mysql+pymysql://root:19800801@localhost/sensor_data_db')

# データを取得
# SQLビューで計算済みの`hour`列を直接利用し、Pythonでの冗長な計算をなくします。
# これによりコードがDRYになり、効率も向上します。
query = "SELECT source, hour, temperature FROM hourly_data_separate;"
df = pd.read_sql(query, engine)
df1 = df[df['source'] == 'measurements']
df2 = df[df['source'] == 'sensor_data']

# グラフ作成
plt.figure(figsize=(12, 6))

# 7月の散布図
plt.scatter(df1['hour'], df1['temperature'], color='blue', alpha=0.5, s=10, label='July (Measurements)')

# 8月の散布図
plt.scatter(df2['hour'], df2['temperature'], color='red', alpha=0.5, s=10, label='August (Sensor Data)')

plt.title('Temperature Variation Across Hours (July vs August 2025)')
plt.xlabel('Hour of Day (0:00 to 24:00)')
plt.ylabel('Temperature (°C)')
plt.xticks(range(0, 25, 2))  # 2時間ごとの目盛
plt.ylim(25, 32)  # 温度範囲を調整（データに合わせて）
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()