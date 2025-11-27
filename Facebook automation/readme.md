# ADS AUTOMATION

## Code automation
- Live được app của sunhouse trên meta api
    - Cần trang privacy policy
    - API call thành công

- Lấy dữ liệu từ API
    - Lấy dữ liệu quảng cáo (Đã xong version 1)
    - Phân tích dữ liệu quảng cáo bằng code/AI
- Push dữ liệu qua API
    - Tạo quảng cáo tùy chỉnh bằng file + code
    - Tạo quảng cáo tùy chỉnh bằng AI kết hợp knowledge

## Dữ liệu khác
- Lấy dữ liệu message
### Hướng dẫn terminal lấy dữ liệu Message
```
python fetch_page_messages.py --out page_inbox.csv
python fetch_page_messages.py --since 2025-08-01 --until 2025-09-25 --out inbox_aug_to_sep.csv
python fetch_page_messages.py --since 2025-09-01 --out inbox_sep.jsonl
```

## Khác
- Lấy page access token