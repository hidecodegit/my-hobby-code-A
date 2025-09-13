import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt

# MySQL接続
engine = create_engine('mysql+pymysql://root:19800801@localhost/sensor_data_db')

# measurementsのデータ（7月）
query1 = """
SELECT timestamp, temperature
FROM measurements
ORDER BY timestamp;
"""
df1 = pd.read_sql(query1, engine)

# sensor_dataのデータ（8月）
query2 = """
SELECT timestamp, temperature
FROM sensor_data
ORDER BY timestamp;
"""
df2 = pd.read_sql(query2, engine)

# グラフ作成
plt.plot(df1['timestamp'], df1['temperature'], color='blue', label='July (measurements)')
plt.plot(df2['timestamp'], df2['temperature'], color='red', label='August (sensor_data)')
plt.title('Temperature Comparison (July vs August 2025)')
plt.xlabel('Timestamp')
plt.ylabel('Temperature (°C)')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()