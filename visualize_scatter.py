import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt

# MySQL接続
engine = create_engine('mysql+pymysql://root:19800801@localhost/sensor_data_db')

# ビューからデータ取得
query = "SELECT hour, temperature FROM hourly_data;"
df = pd.read_sql(query, engine)

# グラフ作成
plt.figure(figsize=(12, 6))
plt.scatter(df['hour'], df['temperature'], color='purple', alpha=0.5, s=10, label='Temperature')
plt.title('Temperature Variation Across Hours (July vs August 2025)')
plt.xlabel('Hour of Day (0:00 to 24:00)')
plt.ylabel('Temperature (°C)')
plt.xticks(range(0, 25, 2))  # 2時間ごとの目盛
plt.ylim(25, 32)  # 温度範囲を調整（データに合わせて）
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()