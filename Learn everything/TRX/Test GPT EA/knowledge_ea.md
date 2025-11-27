# Knowledge: Cách mình xây EA FVG 3 nến trên MT5 (v3)

Tài liệu này mô tả **quy tắc**, **thiết kế**, **API MT5 đã dùng**, **các quyết định kỹ thuật**, và **những lỗi phổ biến** để bất cứ ChatGPT nào cũng có thể tái tạo/duy trì EA trong các phiên chat sau.

---

## 0) Mục tiêu

* Tự động **phát hiện FVG 3 nến** trên timeframe cấu hình (mặc định M1) chỉ khi **3 nến đã đóng**.
* **Vẽ** vùng FVG từ lúc attach EA (không kéo tới hiện tại).
* **Đặt pending limit** theo rule:

  * **Bullish**: Buy Limit tại **Low(C)**, **SL = Low(B) − (StopBufferPts + SLExtraPts) × Point**, TP theo RR hoặc TP cố định.
  * **Bearish**: Sell Limit tại **High(C)**, **SL = High(B) + (StopBufferPts + SLExtraPts) × Point**.
* Nếu có **FVG mới ngược chiều** ⇒ **hủy mọi pending cũ** (cùng symbol+magic) rồi đặt pending mới.
* Không vượt quá `MaxPositions` (đếm **vị thế mở**, pending kiểm soát riêng bằng đếm/hủy).

---

## 1) Quy tắc FVG 3 nến (định nghĩa chuẩn)

* Ký hiệu: A = nến cũ hơn, B = nến giữa, C = nến mới hơn. **Tất cả đều đã đóng**.
* Chỉ số: A = `shift=3`, B = `2`, C = `1` trên `WorkTF`.
* **Bullish FVG:** `Low(C) > High(A)` ⇒ tồn tại khoảng trống [High(A) .. Low(C)].
* **Bearish FVG:** `High(C) < Low(A)` ⇒ tồn tại khoảng trống [High(C) .. Low(A)].
* Vẽ vùng A..C, sau đó áp dụng logic đặt pending như mục 0.

### Thời điểm tính

* Chỉ xử lý khi **nến mới** xuất hiện (`IsNewBar()`), tránh spam.
* Chỉ xét FVG mà **nến C** hình thành **sau khi attach** EA (`tC >= EAStartBarTime`).

---

## 2) Inputs chính (để người dùng chỉnh khi attach)

* `WorkTF` (default `PERIOD_M1`).
* EMA filter: `UseEMATrend`, `FastEMA`, `SlowEMA`.
* Vẽ: `LookbackBars`, `BullFVGColor`, `BearFVGColor`, `RectWidth`, `RectStyle`, `RectOpacity`, `MarkPreRange`, `RangeWindow`, `ATRPeriod`, `RangeATRMult`, `RangeColor`.
* Trade: `EnableTrading`, `AllowLong`, `AllowShort`, `OnlyWithTrend`, `Magic`, `DeviationPoints` *(market orders only)*, `MaxPositions`.
* Risk: `UseRiskPercent`, `RiskPercent`, `FixedLots`.
* SL/TP: `StopBufferPts`, **`SLExtraPts`** (mặc định 12), `UseRR`, `RR`, `TPPoints`.

> Lưu ý: `DeviationPoints` **không** truyền vào `BuyLimit/SellLimit`; chỉ áp dụng `trade.SetDeviationInPoints()` cho **market** `Buy/Sell`.

---

## 3) Luồng xử lý (pseudo)

```pseudo
OnInit:
  atrHandle = iATR(...)
  emaFast = iMA(... FastEMA)
  emaSlow = iMA(... SlowEMA)
  trade.SetExpertMagicNumber(Magic)
  trade.SetDeviationInPoints(DeviationPoints)  # chỉ market
  EAStartBarTime = iTime(Symbol, WorkTF, 0)

OnTick:
  if !IsNewBar(): return
  for s from 3 to min(Lookback, bars-1):
    A=s, B=s-1, C=s-2 (đều đã đóng)
    tC = iTime(..., C)
    if tC < EAStartBarTime: continue

    HA=iHigh(A), LA=iLow(A), HB=iHigh(B), LB=iLow(B), HC=iHigh(C), LC=iLow(C)

    bullFVG = (LC > HA)
    bearFVG = (HC < LA)
    if !(bullFVG || bearFVG): continue

    if OnlyWithTrend:
       fast>slow ? trend=1 : -1
       filter bull/bear theo trend

    vẽ rectangle A..C theo hướng tương ứng

    if EnableTrading and OpenPositions < MaxPositions:
       pendDir, pendCount = scanPending(Symbol,Magic)
       needDir = +1 if bullFVG else -1
       if pendCount>0 and pendDir != needDir:
          deleteAllPending(Symbol,Magic)

       if no pending:
          if bullFVG and AllowLong:
             entry = LC
             sl = LB - (StopBufferPts + SLExtraPts)*Point
             lots = byRisk(|entry-sl|)
             tp = byRRorFixed(entry, sl)
             trade.BuyLimit(lots, entry, Symbol, sl, tp)
          if bearFVG and AllowShort:
             entry = HC
             sl = HB + (StopBufferPts + SLExtraPts)*Point
             lots = byRisk(|entry-sl|)
             tp = byRRorFixed(entry, sl)
             trade.SellLimit(lots, entry, Symbol, sl, tp)

    break  # chỉ FVG đầu tiên trong lượt
```

---

## 4) API/chiêu thức MT5 đã dùng

* **Bars & series**: `iTime`, `iOpen`, `iHigh`, `iLow`, `iClose`, `iBars`, `CopyBuffer`.
* **Indicators**: `iATR`, `iMA` (EMA with `MODE_EMA`, `PRICE_CLOSE`).
* **Objects**: `ObjectCreate(..., OBJ_RECTANGLE, ...)`, `ObjectMove`, `ObjectSetInteger(OBJPROP_COLOR/STYLE/WIDTH/BACK/FILL/ZORDER)`.

  * Lấy biên rectangle: `ObjectGetDouble(0, name, OBJPROP_PRICE, 0/1)` *(modifier)*.
* **Trade class**: `CTrade` → `SetExpertMagicNumber`, `SetDeviationInPoints` (market), `BuyLimit`, `SellLimit`, `OrderDelete`.
* **Orders/Positions**:

  * Duyệt **pending**: `for index: ticket = OrderGetTicket(index) → OrderSelect(ticket)`; lấy `ORDER_SYMBOL`, `ORDER_MAGIC`, `ORDER_TYPE`.
  * Duyệt **positions**: `PositionGetTicket(i) → PositionSelectByTicket(ticket)`; lấy `POSITION_SYMBOL`, `POSITION_MAGIC`.

---

## 5) Các lưu ý & lỗi phổ biến (đã khắc phục)

1. **MT4 vs MT5**: `OrderSelect(index, SELECT_BY_INDEX)` **không dùng** trong MT5. Phải dùng `OrderGetTicket(index)` rồi `OrderSelect(ticket)`.
2. `ObjectName` MT5: dùng `ObjectName(0, i, -1, -1)` khi duyệt object.
3. Rectangle prices: dùng `OBJPROP_PRICE` + modifier `0/1` để đọc 2 cạnh.
4. Không đặt SL ở giữa vùng: luôn chuẩn hóa `fvgTop = max(p0,p1)`, `fvgBottom = min(p0,p1)` khi cần.
5. Chữ ký `BuyLimit/SellLimit`: `(volume, price, symbol, sl, tp [, time_type, expiration, comment])`. **Không** truyền `DeviationPoints`.
6. Chờ **3 nến đóng**: A=3, B=2, C=1. Không xử lý khi nến C đang chạy.
7. Chỉ cần **C sau attach** (dựa `tC >= EAStartBarTime`), không cần A/B sau attach.
8. Lot chuẩn hóa: bám `SYMBOL_VOLUME_MIN/MAX/STEP`, tránh lệnh bị từ chối.
9. EMA filter tùy chọn: nếu bật, BUY yêu cầu `EMA_fast > EMA_slow`, SELL yêu cầu `EMA_fast < EMA_slow` tại `shift=s`.
10. Hủy pending ngược chiều trước khi đặt pending mới, để bám quy tắc “một FVG đầu tiên mỗi lượt”.

---

## 6) Cấu trúc file (một-file .mq5)

* `Inputs`: toàn bộ tham số cấu hình.
* `Globals`: handle chỉ báo, `CTrade`, `EAStartBarTime`, v.v.
* Helpers: `IsNewBar`, `ColorWithAlpha`, `TFToString`, dựng tên rectangle, `DrawRect`, `GetEMATrend`, `FindPreRangeBeforeA_TF`.
* Quản lý lệnh: `CountOpenPositionsBySymbolMagic`, `CountPendingsBySymbolMagic`, `DeleteAllPendingsBySymbolMagic`, rủi ro & khối lượng.
* Lifecycle: `OnInit`, `OnTick` (main loop như pseudo ở trên).

---

## 7) Tham số khuyến nghị ban đầu

* `WorkTF = M1` (tùy nhu cầu).
* `UseEMATrend = true`, `FastEMA=50`, `SlowEMA=200`.
* `StopBufferPts = 5`, **`SLExtraPts = 12`** (tùy spread từng symbol).
* `UseRR = true`, `RR = 2.0`.
* `EnableTrading = true` chỉ trên **demo/backtest** trước khi live.

---

## 8) Mở rộng tương lai

* `PendingExpiryMinutes`: tự hủy pending quá thời gian.
* Tuỳ chọn `SLSource = FVGEdge / PreRange` để đặt SL theo vùng **range** trước FVG.
* Multi-symbol/multi-timeframe quản lý state theo `GlobalVariable`/comment lệnh.
* Logging chi tiết (RR, kích thước gap, EMA-trend tại thời điểm tạo).

---

### Ghi chú bàn giao

* Bản hiện tại là **v3** (đợi 3 nến đóng, đặt limit ở Low(C)/High(C), SL ở Low(B)/High(B) ± buffers, `SLExtraPts` để bù spread).
* Khi tái tạo, chỉ cần bám mục **3) Luồng xử lý** + **4) API** + **5) Lưu ý** là ra đúng hành vi.
