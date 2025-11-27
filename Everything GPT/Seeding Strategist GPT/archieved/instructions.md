# Hướng dẫn sử dụng Seeding Strategist GPT

## Quy trình vận hành
1. **Training (tùy chọn):** Upload file `approved_comments.csv` chứa các comment mẫu đã duyệt.
2. **Generate:** Gửi bài viết gốc và thông số seeding (tone, mood, định hướng...).
3. **Validate:** Kiểm tra kết quả trong trường `analysis`, chỉnh sửa tone/mood nếu cần.
4. **Refine:** Nếu kết quả tốt, lưu lại để bổ sung vào tập huấn luyện.
5. **Reset:** Khi cần khởi động chiến dịch mới, dùng lệnh “reset training memory”.

---

## Gợi ý prompt khởi động
```
Tạo 10 comment seeding cho bài viết dưới đây:
[Bài viết gốc]
Định hướng: [mô tả]
Tone: [tự nhiên]
Mood: [tích cực]
Độ dài trung bình: 2 câu
Yêu cầu: có tương tác qua lại, phù hợp mạng xã hội
```

---

## Cảnh báo sử dụng
- Không dùng để thao túng dư luận hoặc sản xuất bình luận giả mạo.  
- Không sinh thông tin sai lệch hoặc công kích người khác.  
- Toàn bộ dữ liệu huấn luyện chỉ được lưu cục bộ trong phiên làm việc.
