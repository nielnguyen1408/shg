USE sunhouse6_tatthanh_net_sunhousecomvndb1;
GO

DECLARE @searchValue NVARCHAR(4000) = N'https://sunhouse.com.vn/pic/general/images/1(70).jpg';
DECLARE @pattern     NVARCHAR(4000);
DECLARE @escapedPattern NVARCHAR(4000);

IF LEN(@searchValue) > 3998
BEGIN
    RAISERROR(N'Search term is too long for NVARCHAR(4000).', 16, 1);
    RETURN;
END;

SET @pattern = N'%' + @searchValue + N'%';
SET @escapedPattern = REPLACE(@pattern, N'''', N'''''');

IF OBJECT_ID('tempdb..#results') IS NOT NULL
    DROP TABLE #results;

CREATE TABLE #results
(
    TableName  NVARCHAR(256),
    ColumnName NVARCHAR(128),
    MatchCount INT
);

DECLARE @schemaName NVARCHAR(128);
DECLARE @tableName  NVARCHAR(128);
DECLARE @columnName NVARCHAR(128);
DECLARE @sql        NVARCHAR(MAX);

DECLARE col_cursor CURSOR FAST_FORWARD FOR
SELECT
    s.name AS SchemaName,
    t.name AS TableName,
    c.name AS ColumnName
FROM sys.columns AS c
JOIN sys.tables  AS t ON c.object_id = t.object_id
JOIN sys.schemas AS s ON t.schema_id = s.schema_id
JOIN sys.types   AS ty ON c.user_type_id = ty.user_type_id
WHERE ty.name IN (N'nchar', N'nvarchar', N'varchar', N'char', N'text', N'ntext', N'sysname');

OPEN col_cursor;

FETCH NEXT FROM col_cursor INTO @schemaName, @tableName, @columnName;

WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sql = N'
    INSERT INTO #results (TableName, ColumnName, MatchCount)
    SELECT
        N''' + @schemaName + N'.' + @tableName + N''',
        N''' + @columnName + N''',
        COUNT(*)
    FROM ' + QUOTENAME(@schemaName) + N'.' + QUOTENAME(@tableName) + N'
    WHERE ' + QUOTENAME(@columnName) + N' LIKE N''' + @escapedPattern + N''';';

    EXEC sys.sp_executesql @sql;

    FETCH NEXT FROM col_cursor INTO @schemaName, @tableName, @columnName;
END

CLOSE col_cursor;
DEALLOCATE col_cursor;

SELECT *
FROM #results
ORDER BY MatchCount DESC, TableName, ColumnName;

DROP TABLE #results;
