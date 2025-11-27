
# MQL5 EA Troubleshooting: “undeclared identifier” & “some operator expected”

This file documents the exact errors encountered, root causes, and standard fixes. It is written to prevent similar issues across other EAs.

---

## 1) Error messages
- `undeclared identifier`
- `'<var>' - some operator expected`
- `class type expected`
- `variable expected`
- Built-in signature hints such as:  
  `built-in: bool SymbolInfoTick(const string, MqlTick&)`

These errors often appear together even if the **actual problem** is a single bad call a few lines earlier.

---

## 2) Root causes

### 2.1 Calling a function with the wrong signature
**Example:** using an ampersand when calling `SymbolInfoTick`:
```mq5
MqlTick tk;
SymbolInfoTick(_Symbol, &tk);   // ❌ WRONG - '&' is for declarations in docs, not at call sites
```
**Fix:**
```mq5
MqlTick tk;
SymbolInfoTick(_Symbol, tk);    // ✅ Correct call
```

### 2.2 Fetching position properties with the wrong overload
Some builds are sensitive to the overload used for `PositionGetString`. Prefer the “by reference” variant:
```mq5
string sym = "";
if(!PositionGetString(POSITION_SYMBOL, sym)) return; // ✅ stable across builds
```
Avoid relying on forms that return `string` directly if your environment is flaky.

### 2.3 Parser confusion after a prior error
When the compiler stumbles on a bad call, it can misparse the next line, leading to:
- `undeclared identifier` at the loop index, and
- `'<var>' - some operator expected`.

This is not actually a missing declaration. The true cause is the previous line.

### 2.4 Hidden “fancy” characters and BOM issues
Copy/paste from chats can inject non‑ASCII characters or a Unicode BOM that breaks parsing. This may manifest as random syntax errors.

---

## 3) Safe patterns to avoid the errors

### 3.1 Iterate positions by **ticket**, then select by **ticket**
```mq5
int total = PositionsTotal();
for(int i = 0; i < total; i++)
{
    ulong ticket = PositionGetTicket(i);
    if(ticket == 0) continue;
    if(!PositionSelectByTicket(ticket)) continue;

    // Now read POSITION_* safely
    string sym = "";
    if(!PositionGetString(POSITION_SYMBOL, sym)) continue;
}
```

### 3.2 Read position fields with the “by-reference” forms
```mq5
string sym = "";
PositionGetString(POSITION_SYMBOL, sym);              // string out

long   type  = (long)PositionGetInteger(POSITION_TYPE);
double entry = PositionGetDouble(POSITION_PRICE_OPEN);
double sl    = PositionGetDouble(POSITION_SL);
double vol   = PositionGetDouble(POSITION_VOLUME);
```

### 3.3 Correct `SymbolInfoTick` usage
```mq5
MqlTick last;
if(!SymbolInfoTick(sym, last)) return;    // no '&' at the call site
```

### 3.4 Volume normalization
```mq5
double NormalizeVolume(const string sym, double v)
{
    double minlot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
    double maxlot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
    double step   = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);

    if(v < minlot) v = minlot;
    if(v > maxlot) v = maxlot;

    double steps = MathFloor((v + 1e-12)/step);
    v = steps * step;
    if(v < minlot - 1e-12) return 0.0;
    return v;
}
```

### 3.5 Partial close by **ticket** (hedging-safe)
```mq5
#include <Trade/Trade.mqh>
CTrade trade;

bool ClosePartialByTicket(ulong ticket, double reqVol)
{
    if(!PositionSelectByTicket(ticket)) return false;
    string sym = "";
    if(!PositionGetString(POSITION_SYMBOL, sym)) return false;

    double vol = NormalizeVolume(sym, reqVol);
    if(vol <= 0.0) return false;

    trade.SetDeviationInPoints(10);
    return trade.PositionClosePartial(ticket, vol);
}
```

---

## 4) Minimal checklist before compiling

1. **No ampersand at call sites** for API functions that list `&` in their documentation signatures.  
   Example: `SymbolInfoTick(sym, tick)` only.
2. Use **by‑reference** overloads for getters that return strings:  
   `PositionGetString(POSITION_SYMBOL, sym)`.
3. Loop positions with **tickets**:  
   `PositionGetTicket(i)` → `PositionSelectByTicket(ticket)`.
4. Ensure **ASCII/UTF‑8 (no BOM)** source. If in doubt: create a new EA file and paste the code.
5. Declare loop indices **before** or inside the `for(...)` in plain style:
   ```mq5
   int i;
   for(i = 0; i < total; i++) { ... }
   ```
6. If the compiler shows an unrelated error on a loop index, **re-check the line above** for a signature mismatch.

---

## 5) Common “do nots”

- Do not write `&var` when calling functions. The `&` in docs indicates a reference **parameter**, not syntax you type at the call site.
- Do not rely on symbol-wide operations in hedging accounts. Always target a **ticket**.
- Do not partial-close to a level that leaves less than `SYMBOL_VOLUME_MIN` remaining.
- Do not assume SL exists when computing “R”. If `sl <= 0`, skip until SL is set or use a dynamic policy.

---

## 6) Example: Trigger partial close at N × R, no SL move

```mq5
// inside OnTick(), after ticket + selection:
double R = 0.0;
double frozenR;
if(GetFrozenR(ticket, frozenR)) R = frozenR;
else R = ComputeLiveR((ENUM_POSITION_TYPE)type, entry, sl);

if(R > 0.0)
{
    double target = (type == POSITION_TYPE_BUY) ? entry + InpRMultiple * R
                                                : entry - InpRMultiple * R;

    MqlTick last;
    if(SymbolInfoTick(sym, last))
    {
        bool reached = (type == POSITION_TYPE_BUY) ? (last.bid >= target)
                                                   : (last.ask <= target);
        if(reached)
        {
            double closeVol = NormalizeVolume(sym, vol * InpClosePercent/100.0);
            double minlot   = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
            if(closeVol <= 0.0 || vol - closeVol < minlot - 1e-12)
                closeVol = NormalizeVolume(sym, vol - minlot);

            if(closeVol > 0.0)
                ClosePartialByTicket(ticket, closeVol); // no SL change
        }
    }
}
```

---

## 7) MetaEditor hygiene

- Create a **new EA file** if you suspect BOM or hidden characters.
- Save as **UTF‑8 without BOM** or ANSI.
- Avoid smart quotes, en‑dashes, or pasted non‑breaking spaces.

---

## 8) Quick reference

- `bool SymbolInfoTick(const string symbol, MqlTick &tick)` → call as `SymbolInfoTick(sym, tick)`
- `bool PositionGetString(enum POSITION_PROPERTY_STRING prop_id, string &value)`
- `ulong PositionGetTicket(int index)` to enumerate positions
- `bool PositionSelectByTicket(ulong ticket)` to address a specific position
- `double SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN|MAX|STEP)` for volume constraints

---

**Outcome:** Adopting these patterns eliminates the recurring “undeclared identifier” and “some operator expected” errors caused by mismatched function calls and fragile overloads, and makes EAs safer on hedging accounts.






# Ghi chú sửa lỗi cho `m1_fvg_trade.mq5`

Bản này tổng hợp nhanh những lỗi đã gặp khi build EA **FVG marker + auto-trade** trên MT5 và cách sửa tương ứng. Mục tiêu: lần sau đỡ cáu bẳn với compiler.

---

## 1) Trùng biến `OnlyWithTrend`

**Triệu chứng:** `variable already defined / identifier already used` ở phần Inputs.

**Nguyên nhân:** Khai báo `input bool OnlyWithTrend` hai lần (một ở khối hiển thị, một ở khối trading).

**Sửa:** Giữ đúng một dòng trong **Trading Inputs**, xóa dòng trùng còn lại.

---

## 2) Dùng sai chữ ký `ObjectName` của MT5

**Triệu chứng:** `wrong parameters count`, `implicit conversion`, đôi khi `unknown symbol` quanh chỗ lấy tên object.

**Nguyên nhân:** Gọi kiểu MT4 (`ObjectName(i)`) trên MT5.

**Sửa:** Dùng đúng chữ ký MT5:

```cpp
string name = ObjectName(0, i, -1, -1);
```

Thêm `if(StringLen(name)==0) continue;` để bỏ object rác.

---

## 3) Lấy toạ độ rectangle sai property

**Triệu chứng:** `undeclared identifier`, `cannot convert enum`, `wrong parameters count` ở `ObjectGetDouble`.

**Nguyên nhân:** Lẫn lộn property. Với **OBJ_RECTANGLE** trong MT5, lấy hai cạnh dùng `OBJPROP_PRICE` kèm **modifier** 0/1.

**Sửa ổn định:**

```cpp
double top = ObjectGetDouble(0, rectName, OBJPROP_PRICE, 0);
double bot = ObjectGetDouble(0, rectName, OBJPROP_PRICE, 1);
```

> Ghi chú: Một số build hỗ trợ `OBJPROP_PRICE1/PRICE2`, nhưng cách trên dùng được rộng hơn.

---

## 4) Set toạ độ rectangle bằng property gây lệch chữ ký

**Triệu chứng:** `cannot convert enum` khi set trực tiếp `OBJPROP_TIME/PRICE`.

**Nguyên nhân:** Overload và index nhạy cảm giữa các build.

**Sửa:** Cập nhật hai điểm neo bằng `ObjectMove` cho đơn giản và an toàn:

```cpp
ObjectMove(0, name, 0, time1,     top);
ObjectMove(0, name, 1, rightTime, bot);
```

---

## 5) Màu trong suốt và `OBJPROP_ALPHA`

**Triệu chứng:** Một số build không hỗ trợ hoặc dễ nhầm kiểu với `OBJPROP_ALPHA`.

**Sửa:** Dùng ARGB từ `ColorToARGB` và set vào `OBJPROP_COLOR`:

```cpp
color drawColor = (RectOpacity < 255) ? (color)ColorToARGB(c, RectOpacity) : c;
ObjectSetInteger(0, name, OBJPROP_COLOR, (long)drawColor);
```

---

## 6) Rác `$1` do replace hỏng

**Triệu chứng:** `unknown symbol '$'` ở vài dòng.

**Nguyên nhân:** Sửa tự động bằng regex lỗi để lại placeholder.

**Sửa:** Thay bằng biến thật (`i`, `rectName`) thủ công.

---

## 7) Getter Position lấy string

**Triệu chứng:** Cast string lộn hoặc hành vi không ổn định khi duyệt vị thế.

**Sửa:** Duyệt theo **ticket** rồi dùng getter **by-reference**:

```cpp
ulong ticket = PositionGetTicket(idx);
if(PositionSelectByTicket(ticket)){
    string sym = ""; PositionGetString(POSITION_SYMBOL, sym);
}
```

---

## 8) Chuẩn hoá lot theo step

**Triệu chứng:** Lệnh bị từ chối do lot không khớp step/min.

**Sửa:**

```cpp
lots = MathFloor((lots+1e-12)/step)*step;
if(lots < minlot - 1e-12) return 0.0;
```

---

## 9) Tránh vào nhiều lệnh cho cùng một vùng

**Giải pháp:** Đặt cờ bằng GlobalVariable theo tên rectangle:

```cpp
GlobalVariableSet("TRADED_" + rectName, TimeCurrent());
```

Kiểm tra trước khi vào lệnh với `GlobalVariableCheck`.

---

## 10) Chạy logic theo nến mới

**Lý do:** Giảm tải và tránh spam lệnh.

**Sửa:** Dùng `IsNewBar()` dựa trên `iTime(_Symbol, WorkTF, 0)` để chỉ xử lý khi nến mới xuất hiện.

---

## Kết quả

* Hết các lỗi kiểu `undeclared identifier / wrong parameters count / cannot convert enum`.
* Vùng FVG vẽ ổn định, auto-trade khi fill, SL ngoài mép vùng `StopBufferPts`, TP theo `RR` hoặc `TPPoints`.
* Tất cả tham số đều chỉnh ở tab **Inputs** khi attach EA, không cần compile lại trừ khi muốn đổi **mặc định**.

---

### Gợi ý test nhanh

1. Attach EA vào chart M1, bật `EnableTrading=true` nhưng test trên **demo**.
2. Giảm `LookbackBars` nếu nhiều object quá.
3. Bật `TradeOnClose=true` để giảm false fill khi giá chạm lướt.

> Nhắc lại: đừng đem ra tài khoản thật trước khi backtest/forward test đủ lâu. Chart xanh không có nghĩa là ví bạn cũng xanh.



# EA FVG MT5 — Tổng hợp lỗi & cách sửa

Tài liệu này tổng hợp các lỗi đã gặp khi build/compile và chạy EA đánh theo FVG 3 nến trên **MT5**, kèm cách sửa ổn định. Dùng để tra nhanh khi bạn (hoặc team) đụng lại lỗi tương tự.

---

## 1) Rule giao dịch (để đối chiếu)

* **FVG 3 nến**:

  * **Bullish**: `Low(nến 3) > High(nến 1)` ⇒ có khoảng trống.

    * Đặt **Buy Limit** tại **High(nến 1)** (mép dưới FVG).
    * **SL = Low(nến 2)** − `StopBufferPts` * Point.
  * **Bearish**: `High(nến 3) < Low(nến 1)`.

    * Đặt **Sell Limit** tại **Low(nến 1)** (mép trên FVG).
    * **SL = High(nến 2)** + `StopBufferPts` * Point.
* **Chỉ xử lý FVG đầu tiên** tìm thấy trong mỗi lượt quét.
* **Nếu xuất hiện FVG ngược chiều mới**: hủy toàn bộ pending limit cũ (cùng symbol + magic) rồi đặt pending theo hướng mới.
* Chỉ vẽ/đặt lệnh **kể từ lúc attach EA** (không kéo vùng tới hiện tại).

---

## 2) Lỗi compile/phát sinh thường gặp & cách sửa

### 2.1 Trùng biến `OnlyWithTrend`

* **Triệu chứng**: `variable already defined / identifier already used`.
* **Nguyên nhân**: Khai báo trùng `input bool OnlyWithTrend` ở 2 nơi.
* **Cách sửa**: Giữ đúng một khai báo ở block **Trading Inputs**, xóa bản trùng.

### 2.2 Sai chữ ký `ObjectName` (MT4 vs MT5)

* **Triệu chứng**: `wrong parameters count`, `implicit conversion`.
* **Nguyên nhân**: Dùng kiểu MT4 `ObjectName(i)` trên MT5.
* **Cách sửa**: Dùng chữ ký MT5:

  ```cpp
  string name = ObjectName(0, i, -1, -1);
  if(StringLen(name)==0) continue;
  ```

### 2.3 Lấy tọa độ rectangle sai property

* **Triệu chứng**: `undeclared identifier`, `cannot convert enum`, `wrong parameters count` ở `ObjectGetDouble`.
* **Nguyên nhân**: Dùng sai tổ hợp property cho `OBJ_RECTANGLE`.
* **Cách sửa ổn định**: Lấy hai cạnh bằng **modifier** 0/1:

  ```cpp
  double top = ObjectGetDouble(0, rectName, OBJPROP_PRICE, 0);
  double bot = ObjectGetDouble(0, rectName, OBJPROP_PRICE, 1);
  ```

  (Hoặc `OBJPROP_PRICE1/PRICE2` tùy build, nhưng `OBJPROP_PRICE`+modifier hoạt động rộng hơn.)

### 2.4 Set tọa độ rectangle gây lệch chữ ký

* **Triệu chứng**: `cannot convert enum` khi set `OBJPROP_TIME/PRICE` trực tiếp.
* **Cách sửa**: Cập nhật 2 điểm neo bằng `ObjectMove`:

  ```cpp
  ObjectMove(0, name, 0, time1, top);
  ObjectMove(0, name, 1, time3, bot);
  ```

### 2.5 Màu trong suốt & `OBJPROP_ALPHA`

* **Triệu chứng**: Một số build không hỗ trợ `OBJPROP_ALPHA`.
* **Cách sửa**: Trộn alpha sang ARGB rồi set vào `OBJPROP_COLOR`:

  ```cpp
  color draw = (RectOpacity<255) ? (color)ColorToARGB(base, RectOpacity) : base;
  ObjectSetInteger(0, name, OBJPROP_COLOR, (long)draw);
  ```

### 2.6 Rác `$1` từ replace hỏng

* **Triệu chứng**: `unknown symbol '$'`.
* **Cách sửa**: Thay bằng biến thật (`i`, `rectName`) thủ công.

### 2.7 Duyệt **orders** kiểu MT5 (pending)

* **Triệu chứng**: `OrderSelect` báo `wrong parameters count`.
* **Nguyên nhân**: Dùng cú pháp MT4 `OrderSelect(index, SELECT_BY_INDEX, ...)`.
* **Cách sửa**: MT5 cần **ticket**:

  ```cpp
  ulong ticket = OrderGetTicket(index);
  if(ticket && OrderSelect(ticket)) { /* ... */ }
  ```

### 2.8 Chữ ký `BuyLimit/SellLimit` — *cannot convert enum*

* **Triệu chứng**: `cannot convert enum` ở tham số thứ 6 khi truyền `DeviationPoints`.
* **Nguyên nhân**: Tham số thứ 6 là `ENUM_ORDER_TYPE_TIME` (thời hạn), **không** phải deviation.
* **Cách sửa**: Dùng chữ ký ngắn gọn (không truyền deviation):

  ```cpp
  trade.BuyLimit(lots, entry, _Symbol, sl, tp);
  trade.SellLimit(lots, entry, _Symbol, sl, tp);
  ```

  (Deviation chỉ áp dụng cho **market orders**.)

### 2.9 Cảnh báo implicit conversion (string↔number)

* **Triệu chứng**: `implicit conversion from 'string' to 'number'`.
* **Nguyên nhân**: Thứ tự tham số sai khi gọi `BuyLimit/SellLimit` (đặt `_Symbol` vào chỗ `price`, v.v.).
* **Cách sửa**: Đảm bảo thứ tự **(volume, price, symbol, sl, tp [, time_type, expiration, comment])**.

### 2.10 Đặt SL vào giữa vùng FVG

* **Triệu chứng**: Lệnh thua do SL nằm giữa vùng.
* **Nguyên nhân**: Lấy nhầm cạnh trên/dưới của rectangle.
* **Cách sửa**: Luôn chuẩn hóa biên:

  ```cpp
  double fvgTop = MathMax(p0, p1);
  double fvgBottom = MathMin(p0, p1);
  // BUY: SL = fvgBottom - buffer; SELL: SL = fvgTop + buffer
  ```

### 2.11 Duyệt position & lấy string an toàn

* **Khuyến nghị**: Chọn theo **ticket** rồi lấy string by-ref (
  `PositionGetString(POSITION_SYMBOL, sym)`) để tránh lỗi overload/ép kiểu.

### 2.12 Chuẩn hóa lot theo step/min

* **Vấn đề**: Lệnh bị từ chối do volume không khớp step/min.
* **Sửa**:

  ```cpp
  lots = MathFloor((lots+1e-12)/step)*step;
  if(lots < minlot - 1e-12) return 0.0;
  ```

---

## 3) Hành vi EA sau khi fix

* Vẽ vùng FVG **từ lúc attach EA**; không kéo dài tới hiện tại.
* Phát hiện FVG 3 nến theo rule phía trên.
* Đặt **BuyLimit/SellLimit** tại mép vùng, **SL** theo nến 2 ± buffer, **TP** theo RR hoặc TP cố định.
* **Chỉ xử lý FVG đầu tiên** trong mỗi lượt quét; không spam lệnh.
* Khi **xuất hiện FVG ngược chiều mới**: hủy toàn bộ pending cũ (cùng symbol+magic) và đặt pending mới theo hướng mới.
* Tôn trọng `MaxPositions` đối với vị thế đang mở; pending được kiểm soát qua hàm đếm/hủy.

---

## 4) Checklist nhanh khi còn lỗi

1. `ObjectName` đã dùng chữ ký MT5 chưa? `ObjectName(0, i, -1, -1)`.
2. Lấy biên rectangle bằng `ObjectGetDouble(..., OBJPROP_PRICE, 0/1)`.
3. Cập nhật điểm rectangle bằng `ObjectMove`, tránh set property trực tiếp.
4. `OrderSelect` dùng **ticket**: `OrderGetTicket(index) → OrderSelect(ticket)`.
5. `BuyLimit/SellLimit`: thứ tự tham số đúng, **không** truyền deviation.
6. Chuẩn hóa **lots** theo step/min.
7. SL theo **nến 2**, BUY dưới vùng, SELL trên vùng (cộng/trừ buffer).

---

## 5) Gợi ý mở rộng (tùy chọn)

* Thêm `PendingExpiryMinutes` để tự động hủy pending sau X phút.
* Thêm chọn nguồn SL: `SLSource = FVGEdge / PreRange` (đặt SL theo vùng range trước FVG).
* Log ra comment lệnh: hướng, RR, kích thước gap, thời gian hết hạn.

> Hoàn tất. Nếu sau này phát sinh lỗi khác, bổ sung vào mục 2 cho đủ “bộ sưu tập”.
