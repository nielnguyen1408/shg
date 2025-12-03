USE sunhouse6_tatthanh_net_sunhousecomvndb1;
GO

DECLARE @code NVARCHAR(255) = NULL;

SELECT
    p.Id,
    p.Code,
    p.Title,
    p.Status,
    p.Content
FROM dbo.Product AS p
WHERE p.Status = 1
  AND (@code IS NULL OR p.Code = @code)
  AND NULLIF(LTRIM(RTRIM(p.Code)), '') IS NOT NULL
  AND NULLIF(LTRIM(RTRIM(p.Title)), '') IS NOT NULL;

