# Prompt mẫu cho GPT | Seeding Strategist

## 1️⃣ Khởi tạo ý tưởng seeding
```
Khởi tạo ý tưởng cho seeding với input:
{
  "bai_viet_goc": "Thương hiệu ABC vừa ra mắt dòng skincare mới...",
  "dinh_huong": ["An toàn", "Thật – Gần gũi"],
  "tone": "tự nhiên",
  "mood": "tích cực",
  "so_luong": 30
}
```

GPT sẽ xuất:
- `*_ideas.json` (toàn bộ ý tưởng)
- `*_ideas.xlsx` (sheet Ideas)

## 2️⃣ Duyệt ý tưởng
```
Duyệt các ý tưởng #1, #3, #7.
approved_ideas = [1,3,7]
```

## 3️⃣ Sinh comment theo ý đã duyệt
```
Sinh 30 comment seeding theo các ý tưởng #1, #3, #7 cho bài viết:
[copy bài viết gốc]
Tone: tự nhiên
Mood: tích cực
```

## 4️⃣ Tạo Knowledge mới từ file comment duyệt
```
Xuất knowledge tên: Seeding điều hướng sản phẩm
```
