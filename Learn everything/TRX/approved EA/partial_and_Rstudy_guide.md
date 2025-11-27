# Mục tiêu

Tài liệu này mô tả ngắn gọn cách thiết kế và triển khai hai EA cho MT5 (MQL5):

* **EA_PartialClose**: đóng một phần vị thế theo R-multiple (TP1, TP2) dựa trên Initial SL.
* **EA_Logger_RStudy**: ghi log nghiên cứu hiệu suất, tính R thực tế (profit/risk), đánh dấu TP0/TP1/TP2 đã hit (1/0), theo dõi MFE, nguyên nhân đóng lệnh…

Kèm theo là các lỗi thường gặp và cách sửa, dùng làm tham chiếu khi build/bảo trì.

---

## 1) EA_PartialClose: Thiết kế và luồng xử lý

**Mục tiêu**: partial close theo mốc TP1 = k1×R, TP2 = k2×R. R được cố định bằng **Initial SL** tại lần đầu EA thấy SL > 0 trên ticket.

### Inputs chính

* `TP1_RMultiple`, `TP2_RMultiple`: hệ số R cho TP1/TP2.
* `ClosePct1`, `ClosePct2`: phần trăm **trên INITIAL volume** cần đóng tại TP1/TP2.
* `UseInitialSL`: bật cơ chế “đóng băng” SL ban đầu.
* `DeviationPoints`, `FillPolicy`, `AllowRequote`, `RetryCount`, `RetryDelayMs`: xử lý thị trường chạy nhanh (requote/price change).
* Lọc `ApplyAllSymbols`/`SymbolFilter`/`MagicFilter` để giới hạn đối tượng.

### Dữ liệu trạng thái (Global Variables)

* `PC_INITSL_<ticket>`: lưu Initial SL dùng tính R.
* `PC_INITVOL_<ticket>`: lưu Initial volume làm mẫu số khi tính % partial close.
* `PC_DONE1_<ticket>`, `PC_DONE2_<ticket>`: cờ đã đóng TP1/TP2, tránh lặp.

### Luồng chính (OnTick)

1. Quét `PositionsTotal()` và `PositionSelectByTicket` cho từng ticket phù hợp filter.
2. **Freeze** Initial SL/Initial volume lần đầu thấy (nếu `UseInitialSL=true`).
3. Tính `R_price = |Entry − InitialSL|`. Nếu `R_price < MinRPoints×Point` thì **bỏ qua** cho đến khi hợp lệ.
4. Tính TP1/TP2 theo hướng BUY/SELL.
5. Kiểm tra giá chạm mốc:

   * BUY so `Bid ≥ target`, SELL so `Ask ≤ target`.
6. Khi chạm, gọi `ClosePartialWithRetry(ticket, volume)`:

   * Chuẩn hóa khối lượng theo `SYMBOL_VOLUME_MIN/MAX/STEP`.
   * Dùng `CTrade.PositionClosePartial` và lặp lại nếu retcode thuộc nhóm tạm thời: `REQUOTE`, `PRICE_CHANGED`, `PRICE_OFF`, `TOO_MANY_REQUESTS`, `CONNECTION`, `LOCKED`.
7. Khi vị thế đóng hẳn, dọn `GV` liên quan.

### Lưu ý triển khai

* **Partial close tính theo INITIAL volume**, không theo volume hiện tại.
* Nếu `UseInitialSL`, EA sẽ **chưa** partial-close cho đến khi có SL > 0 lần đầu.
* Mỗi chart chỉ gắn **một EA**; muốn chạy logger song song thì mở chart khác.

---

## 2) EA_Logger_RStudy: Thiết kế và luồng xử lý

**Mục tiêu**: tạo bảng log phục vụ phân tích R và hành vi TP.

### Khái niệm và tính toán

* **Initial risk (RiskMoney)**: tiền rủi ro ban đầu cho **toàn vị thế**, từ khoảng cách Entry ↔ Initial SL quy đổi bằng `SYMBOL_TRADE_TICK_SIZE`/`SYMBOL_TRADE_TICK_VALUE` (fallback `SYMBOL_POINT` khi cần) nhân **Initial lots**.
* **R thực tế (cột `R`)**: `R = (profit + commission + swap) / RiskMoney`. Không kẹp giá trị. Nếu đóng bằng SL có slip/chi phí, `R ≤ -1` là bình thường.
* **MFE (Most Favorable Excursion)**: giá thuận lợi nhất kể từ khi mở lệnh (BUY dùng **Bid cao nhất**, SELL dùng **Ask thấp nhất**).
* **HighestRMultiple**: `(MFE − Entry)/R_price` cho BUY hoặc `(Entry − MFE)/R_price` cho SELL, với `R_price = |Entry − InitialSL|`.
* **TP0/TP1/TP2 Hit**: so sánh MFE với mốc giá TP tương ứng và ghi **1/0**.

### Cột CSV tiêu chuẩn (phiên bản gọn)

`TimeClose, Ticket, Symbol, Type, Entry, InitialSL, SL_Points, RiskMoney, R, TP0_Price, TP1_Price, TP2_Price, MFEPrice, HighestRMultiple, TP0_Hit, TP1_Hit, TP2_Hit, ClosePrice, CloseCause, CloseProfit, Commission, Swap, InitLots, Magic`

### Luồng chính

* **Ghi theo sự kiện**: `OnTradeTransaction` với `TRADE_TRANSACTION_DEAL_ADD` và `DEAL_ENTRY_OUT` để log ngay khi có deal đóng.
* **Theo dõi MFE**: cập nhật mỗi tick khi vị thế còn mở.
* **Freeze** `InitialSL`, `InitLots`, `Entry` bằng Global Variables lần đầu thấy.
* **Append file** trong **Common\Files**. Tên file tự động gắn hậu tố `_<ACCOUNT_LOGIN>` từ `InpLogFileName`.

### Hành vi khi restart MT5

* Giữ cơ chế append (mở file, nếu `FileSize==0` thì ghi header, sau đó `FileSeek(..., SEEK_END)`).
* Cờ `PC_LOGGED_<ticket>` lưu bằng Global Variables để tránh ghi trùng sau restart.

---

## 3) Lỗi thường gặp và cách sửa

### 3.1 Cảnh báo "possible loss of data due to type conversion" ở `switch(reason)`

* **Nguyên nhân**: dùng `long` thay vì enum khi switch trên `DEAL_REASON`.
* **Cách sửa**: đổi chữ ký hàm sang `ENUM_DEAL_REASON` và cast khi đọc:

  * `string CloseCauseToString(const ENUM_DEAL_REASON reason)`
  * `reason = (ENUM_DEAL_REASON)HistoryDealGetInteger(dtk, DEAL_REASON);`

### 3.2 `undeclared identifier` với `DEAL_REASON_SYMBOL_MIGRATION`

* **Nguyên nhân**: hằng này **không tồn tại** trong MQL5.
* **Cách sửa**: dùng `DEAL_REASON_CORPORATE_ACTION` hoặc ánh xạ các lý do khác (`VMARGIN`, `SPLIT`, `MOBILE`, `WEB`...).

### 3.3 Nhầm `DEAL_TYPE_*` với `ORDER_TYPE_*`

* **Triệu chứng**: `DEAL_TYPE_BUY_LIMIT`/`DEAL_TYPE_BUY_STOP` báo không khai báo.
* **Cách sửa**: chỉ dùng `DEAL_TYPE_BUY`/`DEAL_TYPE_SELL` cho deal khớp. Map sang `POSITION_TYPE_*` như:

  * `if(dtype==DEAL_TYPE_BUY) pos_type=POSITION_TYPE_BUY; else if(dtype==DEAL_TYPE_SELL) pos_type=POSITION_TYPE_SELL; else ignore;`

### 3.4 Logger không tạo file

* **Nguyên nhân**:

  * Gắn logger **sau** khi lệnh đã mở, không kịp freeze Initial SL/Entry.
  * Sai filter `Symbol/Magic`.
  * Không có lệnh **đóng** nên chưa ghi.
* **Cách kiểm tra**:

  * Bật `EnableLogging`.
  * Nhìn tab **Experts**: in đường dẫn `TerminalInfoString(TERMINAL_COMMONDATA_PATH)` và lỗi `GetLastError()` khi `FileOpen`.
  * Đường dẫn: `...\MetaQuotes\Terminal\Common\Files\<file>.csv`.

### 3.5 Một chart gắn hai EA?

* Không được. Mỗi chart chỉ gắn **một** EA. Dùng hai chart riêng (có thể cùng symbol/timeframe).

### 3.6 CSV mở ra dính một cột trong Excel

* **Nguyên nhân**: file xuất theo **Tab** hoặc dấu phân cách khác.
* **Cách xử lý**: khi mở bằng Excel, chọn **Data → From Text/CSV** và chọn delimiter đúng (Tab/Comma/Semicolon). Hoặc chuyển sang Excel bằng script nếu cần.

### 3.7 R bị hiểu nhầm

* `R` trong logger chuẩn là **R thực tế** = `NetProfit / RiskMoney`, đã gộp partial. Không phải khoảng cách giá. Nếu đóng bằng SL có phí/slippage, `R ≤ -1` là đúng.

### 3.8 TP hit ghi sai mục đích

* Đừng chỉ log giá TP; cần **so sánh MFE** với TP và ghi `TPx_Hit` **1/0**. BUY: `MFE ≥ TPx_Price`. SELL: `MFE ≤ TPx_Price`.

### 3.9 SL đặt sau khi vào market order

* Logger/PartialClose sẽ freeze **Initial SL** ngay khi thấy SL > 0 lần đầu. Trước thời điểm đó partial-close chưa hoạt động (nếu phụ thuộc R). Khuyến nghị đặt SL **ngay** sau khi khớp lệnh.

### 3.10 Tranh chấp ghi file khi nhiều EA cùng ghi

* Giải pháp nhanh gọn: dùng **một** logger, hoặc thêm hậu tố `_ACCOUNT_LOGIN` để tách file giữa tài khoản. Nếu vẫn cần nhiều logger ghi chung, có thể khóa nhẹ bằng Global Variable (mutex) khi ghi.

---

## 4) Tích hợp nhanh cho GPT triển khai

* **Partial Close EA**:

  * Lưu Initial SL/Initial volume bằng Global Variables.
  * Tính R từ Initial SL, xác định TP1/TP2 theo R-multiple.
  * Kiểm tra mốc theo Bid/Ask tương ứng hướng lệnh.
  * Partial close theo **INITIAL volume**, chuẩn hóa khối lượng, retry trên retcode tạm thời.
* **Logger EA**:

  * Theo dõi MFE theo tick; freeze Initial SL/Entry/InitLots khi thấy lần đầu.
  * Bắt sự kiện `OnTradeTransaction` khi `DEAL_ENTRY_OUT`, gom toàn bộ deal OUT để lấy `profit/commission/swap`.
  * Tính `RiskMoney`, `R` thực tế, `HighestRMultiple`, `TPx_Hit` (1/0).
  * Ghi CSV vào **Common\Files**, tên file = `<InpLogFileName>_<ACCOUNT_LOGIN>.csv`, **append** theo thời gian.

---

## 5) Checklist test nhanh

* [ ] Đặt SL ngay sau khi vào lệnh market; kiểm tra `PC_INITSL_<ticket>` xuất hiện.
* [ ] Cho giá chạm TP1 rồi quay lại: `Done1=1`, volume giảm đúng theo % INITIAL.
* [ ] Đóng lệnh hoàn toàn: logger ghi một dòng; `R` âm/xấp xỉ −1 nếu bị SL, dương nếu có lãi.
* [ ] MFE vượt TP0/1/2: cột `TPx_Hit` phản ánh 1/0 đúng hướng BUY/SELL.
* [ ] CSV mở bằng Excel hiển thị đúng cột; nếu không, import qua Data → From Text/CSV và chọn delimiter phù hợp.

---

### Ghi chú cuối

* Tách nhiệm vụ: PartialClose xử lý giao dịch, Logger xử lý dữ liệu. Cặp đôi này giảm rủi ro bug và dễ bảo trì.
* Khi cần mở rộng phân tích (MAE, R tại điểm đóng, phân nhóm theo symbol/magic), thêm cột **có chủ đích**, tránh phình bảng vô ích.
