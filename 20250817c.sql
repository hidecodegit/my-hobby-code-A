WITH avg_values AS (
    SELECT
        AVG (temperature) AS avg_temp,
        AVG (humidity) AS avg_humidity
    FROM measurements
    WHERE `year_month` = '2025-07'
)
SELECT
    m.timestamp,
    m.temperature,
    m.humidity
FROM
    measurements AS m, avg_values
WHERE
    m.`year_month` = '2025-07'
    AND m.temperature > avg_values.avg_temp + 0.5
    AND m.humidity > avg_values.avg_humidity + 0.5;