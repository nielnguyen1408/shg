# Clean Database – Sunhouse Website Data

Tài liệu tóm tắt chức năng các script, nguồn dữ liệu và flow xử lý để ra bộ JSON/XLSX/HTML dùng cho viewer.

## Nguồn và đích
- **Nguồn thô (input gốc)**: `info.xlsx`, `new_website_tinhnang.xls` (hoặc `new_website_tinhnanh.xls`).
- **Đích sử dụng**: `clean_info_noimage.json` và `new_website_tinhnang_noimage.json` (đã gắn domain ảnh + ép size), được nhúng vào `product_viewer_v1.html`.

## Flow chuẩn theo bước
1) **Làm sạch mô tả sản phẩm**  
   `python clean_info.py info.xlsx`  
   - Đầu ra: `clean_info.json`, `clean_info.csv`, `clean_info.xlsx` (unescape HTML, giữ cấu trúc cột TongQuan/ThietKe/CongNang…).
2) **Tách tiêu chí (tuỳ chọn)**  
   `python clean_info_v2.py clean_info.xlsx`  
   - Đầu ra: `criteria_info.json/csv/xlsx` (mỗi tiêu chí một dòng theo Section/Order).
3) **Chuyển file tính năng**  
   `python new_web_convert.py`  
   - Đầu ra: `new_website_tinhnang.json`, `new_website_tinhnang.xlsx` (group theo Code, Features[] gồm Title/Content/Image).
4) **Gỡ <img> khỏi HTML (tuỳ chọn nếu cần bản không ảnh)**  
   `python clear_image_v1.py`  
   - Đầu ra: `clean_info_noimage.json`, `new_website_tinhnang_noimage.json` (cùng cấu trúc, chỉ bỏ thẻ img trong HTML).
5) **Gắn domain + ép size ảnh (450x450, object-fit: contain)**  
   - Tính năng (mặc định):  
     `python input_image_v1.py`  
     *Đầu vào/ra mặc định*: `new_website_tinhnang_noimage.json` → cùng tên file, base `https://preview6305.canhcam.com.vn/`.
   - Mô tả (ví dụ Sunhouse):  
     `python input_image_v1.py --input clean_info_noimage.json --output clean_info_noimage.json --base-url https://sunhouse.com.vn/ --width 450 --height 450`
   - Tác dụng: thêm base URL cho đường dẫn tương đối; ép style/width/height về 450x450 cho mọi thẻ `<img>` hoặc trường ảnh.
6) **Nhúng dữ liệu vào viewer**  
   `python build_product_viewer_v1.py`  
   - Đầu ra: `product_viewer_v1.html` (nhúng sẵn `clean_info_noimage.json` + `new_website_tinhnang_noimage.json`), dùng template `product_viewer.html` (CSS đã set max 450x450 cho ảnh tính năng).

## Quan hệ file và phụ thuộc
- `clean_info.py` → tạo `clean_info.*` từ `info.xlsx`/CSV.  
- `clean_info_v2.py` → đọc `clean_info.xlsx` → tạo `criteria_info.*`.  
- `new_web_convert.py` → đọc `new_website_tinhnang.xls`/`new_website_tinhnanh.xls` → tạo `new_website_tinhnang.*`.  
- `clear_image_v1.py` → đọc `clean_info.json` và `new_website_tinhnang.json` → tạo bản `*_noimage.json`.  
- `input_image_v1.py` → đọc một JSON (mặc định `new_website_tinhnang_noimage.json`) → gắn domain + ép size ảnh → ghi ra JSON đích.  
- `build_product_viewer_v1.py` → đọc `product_viewer.html` + `clean_info_noimage.json` + `new_website_tinhnang_noimage.json` → xuất `product_viewer_v1.html`.

## Lệnh nhanh hay dùng
- Chuẩn pipeline (tính năng + viewer):  
  ```
  python new_web_convert.py
  python clear_image_v1.py
  python input_image_v1.py  # xử lý new_website_tinhnang_noimage.json với preview6305
  python build_product_viewer_v1.py
  ```
- Chuẩn pipeline (mô tả + viewer):  
  ```
  python clean_info.py info.xlsx
  python clear_image_v1.py
  python input_image_v1.py --input clean_info_noimage.json --output clean_info_noimage.json --base-url https://sunhouse.com.vn/ --width 450 --height 450
  python build_product_viewer_v1.py
  ```

## Ghi chú thêm
- Nếu cần size khác, đổi `--width/--height` khi chạy `input_image_v1.py` (và build lại viewer).
- Nếu đổi domain, dùng `--base-url` tương ứng rồi chạy lại bước 5–6.
