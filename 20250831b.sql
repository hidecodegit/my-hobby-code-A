CREATE VIEW hourly_data AS
SELECT 
    timestamp,
    temperature,
    HOUR(timestamp) + MINUTE(timestamp) / 60.0 AS hour
FROM (
    SELECT timestamp, temperature FROM measurements
    UNION ALL
    SELECT timestamp, temperature FROM sensor_data
) AS combined
ORDER BY timestamp;