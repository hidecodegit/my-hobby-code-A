CREATE OR REPLACE VIEW hourly_data_separate AS
SELECT 'measurements' AS source, timestamp, temperature, humidity, HOUR(timestamp) + MINUTE(timestamp) / 60.0 AS hour
FROM measurements
UNION ALL
SELECT 'sensor_data' AS source, timestamp, temperature, humidity, HOUR(timestamp) + MINUTE(timestamp) / 60.0 AS hour
FROM sensor_data
ORDER BY timestamp;
