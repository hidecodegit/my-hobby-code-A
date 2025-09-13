SELECT * FROM hourly_data_separate
WHERE source = 'sensor_data'
ORDER BY timestamp DESC
LIMIT 10;