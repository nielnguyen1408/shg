# Sử dụng các hàm mới của Google sheet
````excel
=BYROW(SEQUENCE(ROWS($C$2:$C$1000)),
    LAMBDA(r,
        IF(LEN(INDEX($C$2:$C$1000, r))),
            IFERROR(INDEX($D$2:$D$1000, r)/INDEX($C$2:$c$1000, r),""),
            ""
    )
    )
)

````
Chưa nắm rõ.
# Filter + condition "or" + search keyword
````
=FILTER(RAW!C:G, (RAW!B:B="máy xay") + (ISNUMBER(SEARCH("máy xay", RAW!C:C))))
````
Điều kiện "or" sử dụng + (TRUE + FALSE = TRUE)

Sử dụng search() để tìm kiếm từ khóa trong một dải ô, sau đó dùng isnumber() để xác định từ khóa có trong dải ô không

---
