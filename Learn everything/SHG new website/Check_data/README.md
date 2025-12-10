# Kiểm tra nội dung link SHG

Thư mục này chứa công cụ Python để quét danh sách URL (site preview6305.canhcam.com.vn) và kiểm tra xem trang có chứa một hoặc nhiều đoạn text mục tiêu hay không, sau đó xuất kết quả ra Excel.

## Thành phần chính
- `check_links.py`: script chính. Đọc danh sách URL từ CSV, tải từng trang, loại bỏ `<script>/<style>`, chuẩn hóa text rồi kiểm tra sự xuất hiện của các chuỗi mục tiêu.
- `requirements.txt`: hướng dẫn tạo môi trường ảo và cài `requests`, `pandas`, `openpyxl`.
- `links_final.csv`: danh sách link đầy đủ (mỗi dòng 1 URL).
- `links_test.csv`: danh sách link ngắn để chạy thử nhanh.
- `links_an_hoac_key.xlsx`: bản Excel của danh sách link (sheet `Sheet1`, cột `link`).
- `.venv/`: môi trường ảo cục bộ (có thể tạo lại, không cần commit).

## Cài đặt nhanh
```bash
python -m venv .venv
.venv\\Scripts\\activate        # Windows
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Cách chạy
- Chạy thử với bộ link nhỏ:
```bash
python check_links.py links_test.csv --output links_test_result.xlsx
```
- Chạy với danh sách đầy đủ:
```bash
python check_links.py links_final.csv --output links_result.xlsx
```
- Kiểm tra nhiều chuỗi cùng lúc (ví dụ):
```bash
python check_links.py links_final.csv --target "cA'ng nŽŸng" --target "thA'ng s ¯` k ¯1 thu §-t"
```
Mặc định script dùng chuỗi `TARGET_TEXT` khai báo trong file (hiện đang bị lỗi ký tự gốc, nên nên truyền `--target` với chuỗi đúng của bạn).

## Cách hoạt động & đầu ra
- Với mỗi URL, script gửi GET với user-agent Chrome, timeout mặc định 15s, giải mã theo `apparent_encoding` nếu cần.
- HTML được lọc bỏ script/style, chuẩn hóa Unicode NFC và chuyển lowercase để so khớp chắc chắn hơn.
- Kết quả in ra console theo dạng `[index/total] link -> trạng thái`, đồng thời lưu thành Excel (mặc định `links_result.xlsx`) với các cột: `link`, `status`/`status_code`, mỗi cột mục tiêu (`found/not found`). Nếu request lỗi hoặc HTTP 4xx/5xx thì `status` hiển thị `request_error`/`http_error` và sẽ không có kết quả tìm text.

## Lưu ý
- Nếu trang chậm/treo, dùng `--timeout` để chỉnh thời gian chờ; nếu cần bỏ qua lỗi, có thể chia nhỏ danh sách và chạy nhiều lần.
- Dữ liệu đầu vào nên ở UTF-8 (file CSV hiện dùng BOM UTF-8), mỗi dòng một URL; bỏ dòng trống hoặc dòng bắt đầu bằng `#`.
- Kiểm tra tường lửa/proxy nếu thấy nhiều lỗi kết nối.
