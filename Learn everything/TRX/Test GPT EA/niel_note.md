# Các rule đặt ra
- dùng m1 fvg
- kết hợp các vùng fvg
- cz zone di chuyển
- hạn chế ngược chiều khi cz vẫn hold
- timing london + ny

### v1.6
Cập nhật thay đổi fvg khi có lệnh chững -> sẽ di chuyển limit theo

Cập nhật input giờ giao dịch

Cập nhật input SL: Nằm ở nến A hoặc nằm ở nến B

Cập nhật cấu trúc động theo thị trường -> limit di chuyển -> vẫn chưa chuẩn xác lắm.

Không dời ngược chiều hoặc dời người chiều nếu có x fvg liên tiếp giảm.

### Next step
- Check lại định nghĩa của FVG là cây nến 2 không được trượt khỏi nến 1
- Thêm hàm xử lý conflict MTF và LTF -> ra được một phiên bản đa khung thời gian
- Thêm hàm xử lý BE
- Check lại hàm xử lý entry, hiện tại mặc định luôn vào 0.01 chứ không tính toán theo capital -> scale không ngon
- Cần thêm quy tắc về ranging zone
- Cần thêm so sánh giữa B và vùng FVG -> có thể dùng mặc định là 1/2 tính từ FVG đến range của A -> dùng để giảm SL
- Cần thêm quy tắc nếu đã fill fvg thì hủy lệnh