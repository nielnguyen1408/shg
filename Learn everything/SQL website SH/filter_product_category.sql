USE sunhouse6_tatthanh_net_sunhousecomvndb1;
GO

DECLARE @code       NVARCHAR(255) = NULL;           -- ví dụ N'ST2210B-18'
DECLARE @titleLike  NVARCHAR(255) = NULL;           -- ví dụ N'%bếp từ%'
DECLARE @fullUrl    NVARCHAR(500) = NULL;           -- ví dụ N'https://sunhouse.com.vn/san-pham/...'
DECLARE @categoryId INT = NULL;                     -- lọc theo danh mục cụ thể

SELECT p.Id            AS ProductId,
       p.Code,
       p.Title,
       CONCAT(N'https://sunhouse.com.vn/', p.SeoUrl) AS ProductUrl,
       c.Id            AS CategoryId,
       c.Title         AS CategoryTitle,
       c.SeoUrl        AS CategorySeoUrl,
       parent.Id       AS ParentCategoryId,
       parent.Title    AS ParentCategoryTitle,
       parent.SeoUrl   AS ParentCategorySeoUrl
FROM dbo.Product AS p
JOIN dbo.CategoryProduct AS cp ON cp.ProductId = p.Id
JOIN dbo.Category        AS c  ON c.Id = cp.CategoryId
LEFT JOIN dbo.Category   AS parent ON parent.Id = c.ParentId
WHERE (@code      IS NULL OR p.Code = @code)
  AND (@titleLike IS NULL OR p.Title LIKE @titleLike)
  AND (@fullUrl   IS NULL OR CONCAT(N'https://sunhouse.com.vn/', p.SeoUrl) = @fullUrl)
  AND (@categoryId IS NULL OR c.Id = @categoryId);
