WITH avg_values AS (
    SELECT
        AVG(temperature) AS avg_temp,
        AVG(humidity) AS avg_humidity
    FROM
        measurements
)
SELECT
    COUNT(CASE WHEN m.temperature > avg_values.avg_temp THEN 1 END) AS high_temp_only_count,
    COUNT(CASE WHEN m.temperature > avg_values.avg_temp AND m.humidity > avg_values.avg_humidity THEN 1 END) AS high_temp_high_humidity_count
FROM
    measurements AS m, avg_values;