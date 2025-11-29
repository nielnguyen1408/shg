USE sunhouse6_tatthanh_net_sunhousecomvndb1;
GO

DECLARE @ProductCodes TABLE (Code NVARCHAR(50) PRIMARY KEY);

INSERT INTO @ProductCodes (Code)
VALUES (N'ST2210B-18'), (N'STI22M');

SELECT p.*
FROM dbo.Product AS p
JOIN @ProductCodes AS c ON p.Code = c.Code;
