WITH avg_temp AS (
    SELECT AVG(temperature) AS avg_value
    FROM measurements
    WHERE `year_month` = '2025-07'
)
SELECT
    m.timestamp,
    m.temperature
FROM
    measurements AS m, avg_temp
WHERE
    m.`year_month` = '2025-07' AND m.temperature > avg_temp.avg_value + 0.5;