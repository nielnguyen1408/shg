## Liquidity Add-on Framework (Draft)

### Khái niệm
Add-on là pha *bổ sung thanh khoản giả* sau khi thị trường đã quét một vùng liquidity lớn (MTF hoặc HTF).
Mục đích của pha này là:
- Lôi kéo trader vào sai hướng (false continuation).
- Tạo thêm stop và pending order để tích lũy dòng tiền ngược.
- Chuẩn bị cho cú *real expansion* theo hướng còn lại.

Add-on không phải là pullback thuần túy, mà là **quá trình “mở rộng vùng săn mồi”**.

---

### Phân loại

#### 1. Add-on MTF Liquidity (Macro Trap)
**Đặc điểm**
- Xuất hiện sau một cú sweep rõ ràng ở MTF/HTF.
- Giá chạm hoặc vượt đỉnh/đáy MTF liquidity zone.
- Thường có:
  - Wick dài hoặc engulf đảo chiều.
  - Volume spike không có follow-up.
  - LTF hình thành lower-high / higher-low đầu tiên.

**Ý nghĩa**
- Quét *visible liquidity* trên khung cao.
- Kết thúc giai đoạn “cleanup”, mở đầu cho trend đảo chiều thực sự.

**Entry Hint**
- Chờ displacement LTF xác nhận (break of structure theo hướng mới).
- Limit tại OB/FVG nhỏ hình thành sau cú MTF sweep.
- SL ngoài vùng sweep cuối cùng.

---

#### 2. Add-on LTF Liquidity (Micro Trap)
**Đặc điểm**
- Không quét trực tiếp vùng liquidity MTF.
- Giá chỉ hồi tới gần FVG/OB của MTF.
- Trong LTF:
  - Giả vờ đảo chiều (fake BOS).
  - Tạo micro FVG rồi bị quét ngược chính vùng đó.
  - Sau cú quét ngược, giá mới thật sự đi theo hướng chính.

**Ý nghĩa**
- Tạo “liquidity ảo” nội bộ để hấp thu trader entry sớm.
- Giúp thị trường gom thêm volume mà không làm hỏng cấu trúc MTF.

**Entry Hint**
- Quan sát LTF reclaim sau fake BOS.
- Limit tại FVG/LH mới hình thành sau cú quét ngược.
- RR tốt hơn vì SL ngắn, nhưng cần xác nhận rõ displacement.

---

### Chuỗi logic tổng quát
MTF sweep → pullback → add-on phase
  ├── Add-on MTF Liquidity → sweep visible zone
  └── Add-on LTF Liquidity → fake micro structure
→ LTF BOS/displacement → true expansion

---

### Checklist quan sát
- [ ] Có cú MTF sweep thật sự (clear external liquidity taken).
- [ ] Volume/volatility shift rõ ràng tại vùng sweep.
- [ ] Add-on hình thành → xác định loại (MTF / LTF).
- [ ] LTF xác nhận direction bằng BOS thật.
- [ ] Entry hợp lệ chỉ sau khi add-on hoàn tất.

---

### Mục tiêu Backtest
- Xác định tần suất mỗi loại add-on.
- So sánh RR trung bình, winrate, expectancy.
- Đánh giá EV theo từng cặp & phiên.
- Ghi lại đặc điểm thời gian hình thành (London, NY, overlap).
