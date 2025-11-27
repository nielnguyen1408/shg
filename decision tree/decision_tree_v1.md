# **Decision Tree – 2 Phase Entry trong Xu Hướng M15**

Tài liệu này mô tả chi tiết framework ra quyết định chuẩn cho 2 phase entry trong xu hướng M15: **Phase Expansion** và **Phase Retest**. Bao gồm định nghĩa chuẩn về microstructure (MSS, displacement, liquidity sweep, FVG...).

---

# **I. KHÁI NIỆM CỐT LÕI**

Dưới đây là các định nghĩa kỹ lưỡng, chuẩn xác để một trader mới có thể hiểu và áp dụng đúng.

## **1. Market Structure Shift (MSS)**

MSS là tín hiệu đảo chiều trong short-term microstructure (M1). Nó là điều kiện bắt buộc để xác nhận rằng thị trường đã chuyển từ xu hướng nhỏ (internal trend) sang hướng ngược lại.

### **Đặc điểm MSS chuẩn:**

* Cần có **liquidity sweep** trước khi MSS xảy ra.
* Cây nến tạo MSS phải phá qua **swing structure gần nhất** bằng một cú đóng nến mạnh.
* Break phải có sự thay đổi rõ rệt về tốc độ và độ dài nến.
* Không chấp nhận MSS bằng wick — phải phá bằng body.

### **Ví dụ MSS giảm (bearish MSS)**:

1. Giá tạo ra một swing high mới hoặc quét liquidity bên trên.
2. Giá rơi xuống phá **higher low (HL)** gần nhất bằng một nến mạnh.
3. Đóng cửa dưới HL → xác nhận MSS.

## **2. Displacement**

Displacement là chuyển động giá mạnh, dứt khoát, thường do smart money tạo ra để điều hướng dòng tiền.

### **Đặc điểm nhận diện displacement:**

* Nến thân dài, body-to-wick ratio > 2/1.
* Tốc độ tăng/giảm đột ngột.
* Spread mở rộng.
* Volume tăng.
* Thường để lại **FVG** (Fair Value Gap).

Displacement cho thấy thị trường đã chọn hướng và loại bỏ một lượng lớn thanh khoản đối lập.

## **3. Liquidity Sweep**

Là hành động giá **quét qua một vùng thanh khoản** (high/low của swing gần nhất, equal highs/lows, hoặc nội bộ trong range) rồi đảo chiều.

### **Đặc điểm sweep hợp lệ:**

* Phải là **intentional sweep**, không phải chỉ chọt wick nhẹ.
* Phải rõ ràng trên timeframe quan sát (M1 hoặc M15 tùy ngữ cảnh).
* Sweep xong phải có phản ứng: nến rejection, displacement ngược hướng.
* Sweep càng sâu → setup càng giá trị.

### **3 dạng sweep cơ bản:**

1. **Internal liquidity sweep** → trước MSS M1.
2. **External liquidity sweep** → trước BOS trên timeframe lớn (ví dụ M15).
3. **Equal highs/lows sweep** → tín hiệu mô hình classic.

## **4. Fair Value Gap (FVG)**

FVG là khoảng giá ba nến liên tiếp không giao nhau tạo ra vùng mất cân bằng.

* Nến 1 và nến 3 không có overlap body/wick.
* Luôn xuất hiện cùng displacement.
* Dùng để làm vùng retest entry.

---

# **II. DECISION TREE – ENTRY THEO 2 PHASE**

Phần này thiết kế như một cây quyết định đầy đủ.

---

# **A. CHECK FRAMEWORK M15 TRƯỚC**

### **1. M15 có trend rõ không?**

* Nếu không → KHÔNG trade phase expansion. Chỉ dùng retest hoặc tránh trade.

### **2. Có external liquidity bị sweep trước khi phá cấu trúc không?**

* Nếu CÓ → xu hướng mạnh → ưu tiên cả 2 phase.
* Nếu KHÔNG → bỏ expansion entry → chỉ đánh retest.

### **3. Nến phá BOS M15 có displacement không?**

* Nếu CÓ → đánh expansion được.
* Nếu YẾU → chỉ retest.

---

# **B. PHASE 1 – EXPANSION ENTRY**

Entry này nhắm theo lực đẩy đầu tiên sau BOS M15.

### **1. Điều kiện trước khi được phép tìm entry M1:**

* M15 BOS thật (phải đóng nến).
* Có displacement.
* Có FVG mới sinh.
* Có liquidity vừa bị quét.

Nếu thiếu một trong các điều kiện trên → KHÔNG đánh phase expansion.

---

## **2. Decision Tree M1 trong phase expansion**

### **B1. Giá có pullback nhẹ lên M1?**

* Nếu giá chạy thẳng không thở → KHÔNG entry.
* Nếu có pullback nhỏ, kiểm tra tiếp.

### **B2. Pullback có sweep internal liquidity?**

* Nếu CÓ → hợp lệ.
* Nếu KHÔNG → chờ tiếp.

### **B3. Sau sweep có MSS không?**

* Nếu KHÔNG → không entry.
* Nếu CÓ → hợp lệ.

### **B4. Entry tại đâu?**

* FVG ngay sau MSS.
* Hoặc micro OB nếu orderflow mạnh.

### **B5. SL đặt ở đâu?**

* Trên internal sweep vừa rồi.

### **B6. TP?**

* Target thấp nhất gần nhất của M15.
* Hoặc external liquidity bên dưới.

---

# **C. PHASE 2 – RE-TEST ENTRY**

Đây là entry an toàn nhất và chuẩn nhất cho trader mới.

Gồm 2 vùng retest chính:

* FVG M15 sinh ra sau displacement.
* Zone cao nhất (origin zone) của sóng BOS.

---

## **1. Kiểm tra hành vi hồi về zone**

### **C1. Giá hồi có tốc độ chậm, wicky?**

* Nếu CÓ → khả năng retest chuẩn.
* Nếu hồi mạnh đối lực → chờ thêm, xem lại bias.

### **C2. Giá chạm zone:**

* Tìm **liquidity sweep** phía trên zone đó.

### **C3. Sau sweep có reaction M1 mạnh không?**

* Một hoặc hai nến từ chối mạnh.
* Đổi tốc độ rõ rệt.

### **C4. M1 có MSS không?**

* Nếu KHÔNG → chưa entry.
* Nếu CÓ → hợp lệ để setup.

---

## **2. Entry trong phase retest**

### **Entry point:**

* FVG ngay sau MSS M1.
* OB M1 sinh sau MSS.

### **SL:**

* Trên đỉnh sweep.

### **TP:**

* Mức thấp M15 gần nhất.
* Liquidity tiếp theo.

---

# **III. TÓM TẮT QUY TẮC CHÍNH**

### **1) Phase Expansion – ưu tiên khi:**

* M15 trend rõ.
* Có external sweep trước BOS.
* Displacement mạnh.
* M1 phản ứng nhanh → MSS + FVG.

### **2) Phase Retest – ưu tiên khi:**

* Cú hồi về zone đủ sâu.
* Giá chậm, yếu → tạo động lực đảo chiều.
* M1 quét sạch liquidity nội bộ.
* MSS rõ ràng.

---

# **IV. GỢI Ý TRAINING CHO TRADER MỚI**

Trader mới nên bắt đầu với:

* 3 tháng chỉ đánh **Phase Retest**.
* Tránh expansion trong các phiên nhiễu (Asia).
* Replay chart M1 100 lần để nhìn MSS và sweep.

---