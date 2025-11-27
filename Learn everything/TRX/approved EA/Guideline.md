Thả file vào MQL5/Experts/ rồi Compile.

Kéo EA lên chart cặp bạn trade.

Đặt input:
```
InpRMultiple = 5.0 nếu bạn muốn đúng 5R.

InpClosePercent = phần trăm khối lượng sẽ đóng khi chạm mục tiêu.

InpMoveSLtoBE = true để dời SL về hòa vốn sau khi chốt bớt.

InpManageAllSymbols = true để EA quản lý tất cả vị thế, hoặc false chỉ quản lý symbol của chart.

InpFilterByMagic + InpMagicNumber nếu bạn chỉ muốn quản lý lệnh do một system cụ thể mở.

InpDeviationPoints = độ trượt giá cho phép.

InpOneTimeOnly = true để chỉ chốt một lần cho mỗi vị thế.

InpFreezeInitialSL = true -> để khóa SL lần đầu tiên xuất hiện, tránh luôn việc kéo BE.
```
Nó hoạt động thế nào

R được tính bằng khoảng cách từ Entry đến SL ban đầu. Không có SL thì khỏi mơ R, EA sẽ bỏ qua lệnh đó.

Với lệnh Buy, trigger khi Bid ≥ Entry + 5R; lệnh Sell, trigger khi Ask ≤ Entry − 5R.

Khi chạm mục tiêu, EA:

Đóng % khối lượng theo InpClosePercent, tôn trọng min lot và bước lot của symbol.

Tùy chọn dời SL về hòa vốn.

Đánh dấu “đã chốt” bằng Global Variable để tránh chốt lặp.