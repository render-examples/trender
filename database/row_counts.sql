-- Source - https://stackoverflow.com/a
-- Posted by Greg Smith, modified by community. See post 'Timeline' for change history
-- Retrieved 2026-01-24, License - CC BY-SA 4.0

WITH tbl AS (
    SELECT Table_Schema, Table_Name
    FROM   information_schema.Tables
    WHERE  Table_Name NOT LIKE 'pg_%'
    AND Table_Schema IN ('public')
)
SELECT 
Table_Schema AS Schema_Name,
Table_Name,
(xpath('/row/c/text()', query_to_xml(format(
          'SELECT count(*) AS c FROM %I.%I', Table_Schema, Table_Name
            ), FALSE, TRUE, '')))[1]::text::int
AS Records_Count
FROM tbl
ORDER BY Records_Count DESC;
