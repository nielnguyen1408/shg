# Hướng dẫn huấn luyện GPT từ file comment duyệt

## Chuẩn bị file
- Định dạng: CSV hoặc JSON  
- Cột bắt buộc: `content`, `tone`, `mood`, `label_approved`  
- Mỗi dòng = 1 comment được duyệt.

## Nạp file
1. Gõ: “Upload file approved_comments.csv”
2. GPT sẽ tự động đọc, phân tích đặc trưng:
   - Cấu trúc câu (độ dài, tần suất emoji, v.v.)
   - Sentiment (tích cực/trung lập/phản biện)
   - Mức độ tự nhiên

## Huấn luyện
GPT tạo embedding tạm thời trong phiên làm việc → sinh comment mới “bắt vibe” với bộ mẫu duyệt.

## Lưu ý
- Không lưu dữ liệu cá nhân.  
- Khi đổi chiến dịch, gõ: “reset training memory”.
