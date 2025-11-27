# Liquidity Add-on Entry System (Consolidated Framework)

## Tổng quan
Hệ thống hóa toàn bộ logic của các dạng entry liên quan đến Add-on Liquidity, Tempo và cấu trúc MTF/LTF. Mục tiêu: xác định được loại pha thị trường, tempo hiện tại và kiểu entry tối ưu tương ứng.

---

## Bảng hệ thống

| **Loại Entry** | **Bối cảnh thị trường** | **Mô tả cấu trúc & dòng tiền** | **Tempo đặc trưng** | **Chiến lược Entry** | **Quản trị & TP** | **Rủi ro đặc trưng** |
|----------------|--------------------------|--------------------------------|----------------------|----------------------|-------------------|-----------------------|
| **1. Add-on MTF Liquidity Entry (Macro Trap)** | Sau khi MTF quét vùng liquidity lớn (EQH/EQL, swing high/low rõ ràng). Giá bật mạnh tạo imbalance và OB trên MTF. | Cú sweep lấy thanh khoản “thấy được” trên MTF → thị trường tạm thời chạy mạnh cùng hướng với sweep, rồi đảo chiều. | Tempo nhanh giai đoạn đầu (price > time) → sau đó chậm lại (time > price) khi chuẩn bị đảo. | **Limit entry** tại OB/FVG LTF hình thành ngay sau MTF sweep. Xác nhận bằng displacement LTF. | - Chốt phần khi giá tiếp cận vùng OB hoặc FVG ngược hướng.<br>- Giữ phần còn lại nếu tempo giảm dần, volume suy yếu.<br>- RR cao (3–6R). | Entry sớm → có thể bị quét lần nữa nếu MTF chưa dứt add-on hoàn toàn. |
| **2. Add-on LTF Liquidity Entry (Micro Trap)** | Sau khi giá hồi gần vùng OB/FVG MTF nhưng chưa chạm. Trong LTF xuất hiện fake BOS giảm rồi bị quét ngược, sau đó đảo thật. | Đây là “liquidity trong liquidity”: cú add-on nhỏ để gom lệnh retail sell sớm. Sau đó giá đảo nhanh và tạo cấu trúc thật. | Tempo nén chặt (compression → snap). Time ≈ Price, tức là năng lượng đồng bộ. | **Flip zone entry** tại vùng vừa bị phá (zone bị quét rồi reclaim). Entry sau cú snap đảo chiều. | - Giữ lệnh khi tempo chuyển từ nén → mở (displacement rõ).<br>- Chốt khi giá chạm liquidity zone tiếp theo hoặc tempo chuyển sang sideway. | Bỏ lỡ nếu phản ứng quá nhanh; khó thấy trên MTF; dễ bị nhiễu trong high-volatility session. |
| **3. Add-on One-Leg Sweep Entry (Event Spike)** | Sau tích lũy kéo dài cả trên và dưới → xuất hiện cú spike mạnh (tin tức, open session). | Spike quét cả hai đầu liquidity, thường là kết thúc quá trình nén dài. Sau spike, giá đảo ngược và tạo xu hướng thật. | Price >> Time trong spike, sau đó Time ≈ Price khi thị trường ổn định lại. | **Follow-up entry** sau cú spike nếu xuất hiện vùng FVG/OB mới cùng chiều đảo; nếu giá không tạo vùng, **limit** ngay tại spike candle. | - Giữ lệnh khi giá xác nhận đảo bằng close ngược spike.<br>- TP theo thanh khoản gần nhất.<br>- Rủi ro cố định 1R, RR thường 5R+. | Biến động cực mạnh, slippage cao; nếu đọc sai hướng, bị dính stop nhanh. |
| **4. Add-on Extended Tempo Entry (Slow Exhaustion)** | Sau cú add-on, giá không đảo nhanh mà giảm đều theo cấu trúc LTF. OB tăng nằm xa. | Thị trường “xả có kiểm soát” – không panic, không flip mạnh. Vẫn có cấu trúc hồi giảm đều, dòng tiền rút ra từ từ. | Time > Price → tempo chậm, nhịp hồi đều. | **Limit entry short theo nhịp hồi LTF**, không đợi break mạnh. Entry theo nhịp thở thị trường. | - Chốt từng phần khi giá tiến gần OB xa.<br>- Không limit ở OB cũ vì vùng này hold yếu sau add-on. | Entry an toàn nhưng dễ bị bỏ lỡ cú đảo mạnh nếu tempo đột ngột đổi. |

---

## Mối liên hệ logic giữa các loại entry

1. **Add-on MTF → Add-on LTF → One-Leg Sweep**  
   Là chuỗi tiến hóa: thị trường từ *macro trap → micro trap → event release*.

2. **Tempo điều khiển chất lượng setup**  
   - Time > Price → thị trường đang phân phối → entry theo nhịp hồi.  
   - Time ≈ Price → thị trường chuẩn bị đảo → entry ở flip zone.  
   - Price > Time → thị trường đang dọn bàn → đứng ngoài hoặc chờ follow-up đảo ngược.  

3. **Loại entry quyết định vị trí entry trong pha thanh khoản**  
   - Limit → đầu pha, đón imbalance.  
   - Follow-up → giữa pha, đi cùng dòng tiền.  
   - Flip → cuối pha, xác nhận phe thắng thật.  

---

## Checklist tổng hợp trước khi vào lệnh
- [ ] MTF có sweep rõ (external liquidity taken).  
- [ ] Xác định loại add-on (MTF / LTF / One-Leg / Extended).  
- [ ] Tempo xác nhận (chậm / đồng bộ / nhanh).  
- [ ] LTF displacement cùng chiều dự kiến.  
- [ ] Có FVG/OB rõ → zone entry hợp lệ.  
- [ ] RR ≥ 3R, SL đặt ngoài liquidity zone gần nhất.  
- [ ] Không vào nếu tempo đang đổi pha (ví dụ sideway → acceleration).  

---

## Công thức khái quát
> **Entry = Context (Add-on type) × Tempo Alignment × Structure Confirmation**  

Công thức này giữ cho mọi quyết định có thứ tự:  
1. *Thị trường đang trong pha add-on nào?*  
2. *Tempo có ủng hộ entry không?*  
3. *Cấu trúc LTF đã xác nhận đủ chưa?*

Nếu ba câu này đều “có”, entry đó đáng tiền; nếu thiếu một, hãy đứng ngoài — vì thanh khoản chưa đủ “chín”.
