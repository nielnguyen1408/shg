# Vận hành GPT – SHG | Code Smith

## Quy ước giao tiếp
- [BỐI CẢNH]: stack, phiên bản, hosting.  
- [YÊU CẦU]: mục tiêu, đầu vào/đầu ra mong muốn.  
- [RÀNG BUỘC]: bảo mật, thời gian, hiệu năng.  
- [KIỂM THỬ]: test tối thiểu.  
- [TRIỂN KHAI]: môi trường, biến môi trường, DB migrate.

## Bug Report Template
- Môi trường (PHP/MySQL/OS)  
- Bước tái hiện  
- Kết quả thực tế vs mong đợi  
- Log/trace rút gọn  
- Ảnh hưởng & mức ưu tiên

## Rollback nhanh
- DB migration kèm file *down*.  
- Tính năng mới → bật/tắt qua feature flag (env).  
- Crawler: dùng domain-deny list.  
- Giữ bản build trước (tag/release) + script `revert.sh`.
