# Hướng dẫn huấn luyện GPT | Seeding Strategist

## Mục tiêu
Huấn luyện GPT hiểu phong cách bình luận của từng thương hiệu hoặc chiến dịch.

## Dữ liệu cần
- `approved_comments.csv`: gồm các bình luận thật, đã duyệt.
  | content | tone | mood | label_approved |
  |----------|------|------|----------------|

## Các bước huấn luyện
1. Upload `approved_comments.csv`  
2. Dùng lệnh:  
   ```
   Xuất knowledge tên: Seeding điều hướng thương hiệu
   ```
3. GPT sẽ tạo file:  
   - `seeding_dieu_huong_branding.md`
   - `seeding_dieu_huong_branding_flat.json`
   - `seeding_dieu_huong_branding.xlsx`
4. Upload `.md` đó vào Knowledge để cố định phong cách.

## Kiểm tra
- So sánh các bình luận mới với mẫu duyệt: giọng văn, độ dài, cảm xúc, mục đích (`muc_dich`) phải tương đồng.
