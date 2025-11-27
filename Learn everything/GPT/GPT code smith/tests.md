# Đánh giá & Test cơ bản – SHG | Code Smith

## Rubric (1–5)
- Đúng chức năng (kết quả chính xác, output đúng).  
- Bảo mật (prepared statement, sanitize, rate limit).  
- Hiệu năng (timeout, pagination, không block UI).  
- Khả dụng (log, lỗi rõ ràng).  
- Bảo trì (docstring, env config, test kèm).  

**Điểm đạt**: ≥20 và không tiêu chí nào <3.

## Bộ test cơ bản
1. Kiểm tra code có chạy được (syntax valid).  
2. Với query DB: thử injection đơn giản → không bị khai thác.  
3. Với script Python: timeout đúng, log lỗi rõ.  
4. Với frontend: dữ liệu hiển thị & filter hoạt động.  
