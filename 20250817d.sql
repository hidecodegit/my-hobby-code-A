WITH hourly_avg AS (
    SELECT
        HOUR(timestamp) AS hour_of_day,
        AVG(temperature) AS avg_temp,
        AVG(humidity) AS avg_humidity
    FROM measurements
    WHERE `year_month` = '2025-07'
    GROUP BY hour_of_day
    ORDER BY hour_of_day
)
    SELECT
        hour_of_day, avg_temp, avg_humidity
FROM hourly_avg;