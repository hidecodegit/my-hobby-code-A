CREATE VIEW time_slot_stats AS
SELECT 
    source,
    time_slot,
    AVG(temperature) AS avg_temp,
    VARIANCE(temperature) AS var_temp,
    STDDEV(temperature) AS std_temp
FROM (
    SELECT 'measurements' AS source,
           CASE 
               WHEN HOUR(timestamp) BETWEEN 6 AND 11 THEN 'Morning (06:00-11:59)'
               WHEN HOUR(timestamp) BETWEEN 12 AND 17 THEN 'Afternoon (12:00-17:59)'
               ELSE 'Night (18:00-05:59)'
           END AS time_slot,
           temperature
    FROM measurements
    UNION ALL
    SELECT 'sensor_data' AS source,
           CASE 
               WHEN HOUR(timestamp) BETWEEN 6 AND 11 THEN 'Morning (06:00-11:59)'
               WHEN HOUR(timestamp) BETWEEN 12 AND 17 THEN 'Afternoon (12:00-17:59)'
               ELSE 'Night (18:00-05:59)'
           END AS time_slot,
           temperature
    FROM sensor_data
) AS combined
GROUP BY source, time_slot;