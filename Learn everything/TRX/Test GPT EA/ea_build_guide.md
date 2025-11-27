# EA FVG Cluster (v2) — Logic, Hướng dẫn, Giải thích & Lưu ý

> Mục tiêu: giúp GPT/dev khác **hiểu nhanh**, **tái tạo**, **cập nhật** và **phát triển** EA FVG 3-nến (MQL5) theo đúng hành vi đã triển khai ở biến thể *cluster_fix3*.

---

## 1) Tổng quan chiến lược

* **Tín hiệu:** Fair Value Gap (FVG) theo **3 nến đóng**: A=3, B=2, C=1 (đều **đã đóng**).
* **Entry:** Đặt **pending limit** tại mép FVG (EDGE) hoặc trung điểm vùng (MID).
* **SL/TP:** SL theo **Low/High của A hoặc B** (chọn bằng `SLRef`); TP theo **RR** hoặc **Points**.
* **Anti-hedge:** Chỉ cho phép lệnh mới khi vùng đối diện **đã “thủng”** theo A/B (chọn bằng `ZoneBreakRef`).
* **Cluster logic:** FVG **liên tiếp cùng chiều** ⇒ **một cụm (cluster)**, **giữ** limit ở **FVG đầu cụm**. Chỉ **dời** khi có **nhịp dừng** *và* xuất hiện **FVG cùng chiều** sau nhịp dừng. Có tùy chọn dời theo **ngược chiều kề nhau K lần**.

---

## 2) Định nghĩa FVG 3-nến

Ký hiệu: A=3, B=2, C=1 (tính từ bar hiện tại 0).

* **Bullish FVG:** `Low(C) > High(A)` ⇒ vùng **[High(A) .. Low(C)]**.
* **Bearish FVG:** `High(C) < Low(A)` ⇒ vùng **[High(C) .. Low(A)]**.
* Chỉ xét tín hiệu có `Time(C) ≥ EAStartBarTime` (từ khi attach EA), đảm bảo **đợi nến C đóng**.

---

## 3) Entry, SL, TP

**Entry mode (`EntryMode`)**

* `EDGE`: BUY tại **Low(C)**, SELL tại **High(C)**.
* `MID`: BUY/SELL tại **trung điểm vùng FVG**.

**Stop Loss (`SLRef`)**

* `SL_FROM_A` hoặc `SL_FROM_B` (độc lập với BreakRef).

  * BUY: `SL = Low(ref) − (StopBufferPts + SLExtraPts) × Point`
  * SELL: `SL = High(ref) + (StopBufferPts + SLExtraPts) × Point`

**Take Profit**

* `UseRR=true`: TP theo **Risk:Reward** (RR).
* `UseRR=false`: TP = `TPPoints × Point` (theo hướng lệnh).

**Lot sizing**

* `UseRiskPercent=true`: lots = ( equity × risk% / (stop_points × value_per_point_per_lot) ), có `NormalizeLots()` theo min/max/step.
* `UseRiskPercent=false`: dùng `FixedLots` (đã normalize).

---

## 4) Anti‑Hedge (vùng “thủng” theo ZoneBreakRef)

* Lưu vùng gần nhất mỗi hướng:

  * **Bullish zone:** `[bottom=High(A) .. top=Low(C)]`.
  * **Bearish zone:** `[bottom=Low(A) .. top=High(C)]`.
* **ZoneBreakRef**: chọn **A** hoặc **B** để làm **mốc “thủng”** (độc lập `SLRef`).

  * Cho **SELL**: yêu cầu **thủng xuống** `Low(ref)` − `ZoneBreakBufferPts` × Point.
  * Cho **BUY**: yêu cầu **thủng lên** `High(ref)` + `ZoneBreakBufferPts` × Point.
* Kiểm tra trên **nến đã đóng gần nhất** (bar index 1) để tránh repaint.

> Kết hợp với **Cluster**: khi tạo **cụm mới**, cập nhật luôn mốc break cho cụm đó (để guard theo cụm).

---

## 5) Cluster logic (rất quan trọng)

Mục tiêu: **giữ limit** ở **FVG đầu tiên** khi **FVG xuất hiện liên tiếp cùng chiều**, chỉ dời khi có **nhịp dừng + FVG cùng chiều** sau đó.

**Trạng thái cụm**

* `clusterDir`: 1 (bull) / −1 (bear) / 0 (none).
* `clusterC`: thời điểm nến **C** của **FVG đầu cụm**.
* `clusterLastC`: thời điểm nến **C** của **FVG gần nhất** trong cùng cụm.
* `clusterEntry/SL/TP`: thông số **FVG đầu cụm** để đặt limit.
* `clusterBullBreakLevel / clusterBearBreakLevel`: mốc “thủng” **gắn với cụm** (theo `ZoneBreakRef`).

**Khái niệm “liên tiếp (consecutive)”**

* Với FVG mới **cùng chiều**: gọi là **kề nhau** nếu `BarIndex(clusterLastC) − BarIndex(tC_new) == 1`.

  * **Kề nhau** ⇒ **liên tiếp** ⇒ **cùng cụm**, **không dời** limit (chỉ cập nhật `clusterLastC`).
  * **Không kề nhau** ⇒ có **nhịp dừng**.

**Khi nào tạo cụm mới (dời limit)?**

* **Chỉ** khi: *(1)* chưa có cụm **hoặc** *(2)* **cùng chiều** với cụm hiện tại **và** **không kề nhau** (tức **nhịp dừng**), rồi xuất hiện FVG **cùng chiều** đó.
  → **Hủy** pending cũ, **khởi tạo cụm mới**, cập nhật break levels theo `ZoneBreakRef`, đặt limit tại **FVG đầu cụm mới**.

**Ngược chiều & tuỳ chọn dời theo ngược chiều**

* Mặc định `AllowOppositeShift=false`: **không** dời cụm khi có FVG ngược chiều; limit **giữ nguyên**.
* Nếu `AllowOppositeShift=true`: dời cụm **chỉ khi** có **K** FVG **ngược chiều kề nhau** (K = `OppositeShiftConsecK`). Khi đủ K: xóa pending cũ, tạo **cụm mới** theo hướng ngược lại, cập nhật break levels, đặt limit mới.

---

## 6) Bộ lọc xu hướng (tuỳ chọn)

* `UseEMATrend=true`:

  * BUY yêu cầu `EMA_fast > EMA_slow`.
  * SELL yêu cầu `EMA_fast < EMA_slow`.

---

## 7) Vẽ & trực quan (tối giản, không kéo quá khứ)

* Vẽ `OBJ_RECTANGLE` cho mỗi vùng FVG **từ lúc EA chạy**.
* Màu/opacity/width/style cấu hình bằng inputs; cập nhật bằng `ObjectMove`.

---

## 8) Chu trình xử lý (Flow)

1. **OnInit**: tạo EMA handle, set `CTrade` (magic, deviation), `EAStartBarTime`.
2. **OnTick**: nếu **không phải nến mới** ⇒ return.
3. Quét A=3, B=2, C=1 (đã đóng), chỉ tín hiệu **sau** `EAStartBarTime`.
4. Kiểm tra FVG bull/bear; lọc EMA nếu bật.
5. Cập nhật **zones** & vẽ vùng.
6. Tính **entry** (EDGE/MID), **SL** (A/B), **TP** (RR/Points).
7. **Cluster decision**:

   * Nếu **cùng chiều & kề nhau** ⇒ cùng cụm, **không dời**; cập nhật `clusterLastC`.
   * Nếu **cùng chiều & không kề** ⇒ **nhịp dừng** → **tạo cụm mới**, **hủy** pending cũ, đặt limit mới.
   * Nếu **ngược chiều** ⇒ mặc định **không dời**; nếu bật `AllowOppositeShift` và đạt **K** ngược chiều kề nhau ⇒ **dời cụm**.
8. **Anti-hedge** theo cụm (hoặc vùng gần nhất nếu chưa có cụm):

   * BUY yêu cầu `BearZoneBroken()==true`.
   * SELL yêu cầu `BullZoneBroken()==true`.
9. Đặt pending nếu chưa có pending cùng chiều; **xóa pending đối nghịch** chỉ khi chuẩn bị dời cụm/đặt pending mới cùng chiều theo rules.
10. **Chỉ xử lý FVG đầu tiên** mỗi tick để tránh spam.

---

## 9) Pseudocode rút gọn

```text
if !IsNewBar(): return
scan s=3.. for A=3,B=2,C=1 closed and C_time>=EAStart
  detect bull=(LC>HA), bear=(HC<LA)
  if trend filter fails: continue

  update zones & draw
  entry = EDGE/MID; sl by SLRef; tp by RR/points

  newDir = bull?+1:-1
  sameDir = (clusterDir!=0 && newDir==clusterDir)
  isConsec = sameDir && (idx(clusterLastC)-idx(tC)==1)

  // opposite chain option
  if clusterDir!=0 && !sameDir:
     if AllowOppositeShift: count opposite-consecutive K; if reached:
        delete pendings; start new cluster(newDir); compute break levels; place pending
     // else keep old cluster & pending

  // same direction
  if clusterDir==0 OR (sameDir && !isConsec):
     // pause + same direction -> shift cluster
     delete pendings; start new cluster(newDir); compute break levels; place pending
  else if sameDir && isConsec:
     clusterLastC = tC // continue chain, keep pending

  sync runtime break levels with cluster
  break // first FVG per tick
```

---

## 10) Inputs chính (ý nghĩa)

* **WorkTF, LookbackBars**: khung quét & giới hạn hiệu năng.
* **EMA filter**: `UseEMATrend`, `FastEMA`, `SlowEMA`.
* **Hiển thị**: `BullFVGColor`, `BearFVGColor`, `RectOpacity`, `RectStyle`, `RectWidth`.
* **Trading**: `EnableTrading`, `AllowLong/Short`, `OnlyWithTrend`, `Magic`, `DeviationPoints`, `MaxPositions`.
* **Lot & Risk**: `UseRiskPercent`, `RiskPercent`, `FixedLots`.
* **SL/TP**: `SLRef`, `StopBufferPts`, `SLExtraPts`, `UseRR`, `RR`, `TPPoints`.
* **Entry**: `EntryMode` = `EDGE`/`MID`.
* **Anti-hedge**: `EnforceNoHedge`, `ZoneBreakRef`, `ZoneBreakBufferPts`.
* **Cluster optional**: `AllowOppositeShift`, `OppositeShiftConsecK`.

> Lưu ý: `SLRef` **độc lập** với `ZoneBreakRef` để A/B test.

---

## 11) Lưu ý & lỗi hay gặp

1. **Quên chờ nến C đóng** → vẽ/đặt sớm: luôn dò **A=3, B=2, C=1**.
2. **Lẫn API MT4/MT5** (`OrderSelect(index, ...)` của MT4) → dùng **MT5**: `OrderGetTicket(i)`, `OrderSelect(ticket)`.
3. **Sai chữ ký `BuyLimit/SellLimit`** → dùng đúng: `(vol, price, symbol, sl, tp, [time_type, expiration, comment])`.
4. **Implicit conversion** do sai thứ tự tham số hoặc ghép chuỗi với số.
5. **Khối lượng 0/âm** khi `stop_points<=0`: luôn validate & `NormalizeLots()`.
6. **Không normalize giá** trước khi gửi lệnh: `NormalizeDouble(price, SYMBOL_DIGITS)`.
7. **Anti-hedge không trúng** do `ZoneBreakBufferPts` quá nhỏ/lớn hoặc kiểm tra trên bar 0 thay vì bar 1.
8. **Cluster dời sai thời điểm**: đảm bảo điều kiện **pause + same direction**; ngược chiều chỉ dời khi bật tuỳ chọn và đủ **K**.

---

## 12) Checklist tái tạo nhanh

1. Khai báo **Inputs** (mục 10).
2. `OnInit`: EMA handles, `CTrade`, `EAStartBarTime`.
3. `IsNewBar()` để nhịp xử lý theo bar.
4. Detector FVG 3-nến: A=3, B=2, C=1; `Time(C)≥EAStart`.
5. Lọc EMA (nếu bật).
6. Cập nhật `zones` & vẽ rectangle.
7. Tính `entry/sl/tp` theo `EntryMode`, `SLRef`, `RR/Points`.
8. **Cluster**:

   * Cùng chiều & kề nhau → giữ cụm.
   * Cùng chiều & không kề → pause → dời cụm.
   * Ngược chiều → giữ cụm (trừ khi `AllowOppositeShift=true` & đủ K).
9. **Anti-hedge**: `BearZoneBroken()` cho BUY, `BullZoneBroken()` cho SELL.
10. Dọn pending đối nghịch khi **thực sự dời cụm/đặt mới**.
11. Dừng sau **FVG đầu tiên** mỗi tick.

---

## 13) Hướng nâng cấp

* **Session filter** (London/NY với cutoff cuối phiên).
* **Pause theo ATR** (độ sâu hồi) thay vì kề-nhau theo bar.
* **Quality filter** cho FVG (min gap, ATR, volume).
* **Quản trị lệnh**: trailing SL theo cấu trúc, partial TP, BE shift.
* **Multi‑TF confirm**: FVG M1 theo xu hướng M15/H1.
* **State persistence**: lưu/khôi phục cụm qua global variables/serialize khi restart.

---

**Kết luận**
Cấu trúc tách bạch **Detector → Cluster → Guard (anti‑hedge) → Execution** giúp mở rộng dễ dàng mà không làm rối lõi. Việc độc lập giữa `SLRef` và `ZoneBreakRef` cho phép A/B test linh hoạt, còn cơ chế **cluster** đảm bảo hành vi đặt lệnh **ổn định** khi thị trường tạo FVG liên tiếp.
