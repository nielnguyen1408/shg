-- Build product table with URLs; optional filters by status and code/image
DECLARE @baseProductUrl NVARCHAR(200) = N'https://sunhouse.com.vn/';
DECLARE @baseImageUrl   NVARCHAR(200) = N'https://sunhouse.com.vn/pic/product/';
DECLARE @statusFilter   INT = NULL;               -- NULL = all; 1 = show; 0 = hide
DECLARE @targetImage    NVARCHAR(255) = NULL;     -- NULL = all; set filename to filter one image
DECLARE @code           NVARCHAR(255) = N'SHD8903'; -- NULL = all; set product code to filter

SELECT
    p.Id,
    p.Code,
    p.Title,
    p.Status,
    CASE WHEN p.Status = 1 THEN N'Hien thi' ELSE N'An' END AS StatusLabel,
    p.Image AS FileName,
    @baseImageUrl + p.Image AS ImageUrl,
    CONCAT(@baseProductUrl, p.SeoUrl) AS ProductUrl
FROM dbo.Product AS p
WHERE p.Image IS NOT NULL
  AND (@statusFilter IS NULL OR p.Status = @statusFilter)
  AND (@targetImage IS NULL OR p.Image = @targetImage)
  AND (@code IS NULL OR p.Code = @code);
