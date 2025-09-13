WITH avg_temp
    AS (SELECT AVG(temperature)
    AS avg_value FROM measurements
    WHERE `year_month` = '2025-07')
    SELECT avg_value FROM avg_temp;