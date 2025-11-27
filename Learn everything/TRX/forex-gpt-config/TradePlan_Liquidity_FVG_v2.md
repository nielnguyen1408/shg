# Trade Plan – Liquidity + FVG Strategy

## 1. Giả thuyết giao dịch
- Giá thường có xu hướng quét thanh khoản (liquidity sweep) trước khi di chuyển theo hướng chính.
- Khi liquidity bị quét và xuất hiện phản ứng mạnh, kết hợp FVG (Fair Value Gap) & fractal, có thể hình thành setup entry.

## 2. Điều kiện thị trường phù hợp
- **Phù hợp:**
  - Daily bias rõ ràng (giá liên tục phá PDH/PDL cùng chiều).
  - MTF (M15) có xu hướng đồng thuận với Daily bias.
  - Xuất hiện liquidity sweep + tín hiệu đảo chiều rõ (FVG, fractal).
- **Không phù hợp:**
  - Tin tức high impact (NFP, FOMC).
  - Sideway kéo dài, PDH/PDL chưa rõ ràng.
  - Spread/volatility quá cao.

## 3. Khung thời gian & phiên giao dịch
- **Chính:** Phiên New York.
- **Phụ (nếu tín hiệu rõ ràng):** Phiên London.

## 4. Phân tích đa khung
- **HTF (Daily):** dùng PDH/PDL để xác định bias.
- **MTF (M15):**
  - Xác định xu hướng trong phiên.
  - Khi có liquidity sweep + phản ứng mạnh → chuẩn bị entry.
- **LTF (M1):**
  - Risk Entry: sau sweep, đảo chiều + FVG → đặt limit entry.
  - Re-test Entry: sau sweep, M15 đảo chiều + FVG, chờ M1 re-test thành công.
  - Extreme Limit Entry: nếu còn FVG unfilled vùng extreme, đặt limit entry tại đó.

## 5. Liquidity Concept
- **Inliquid (weak liquidity):**
  - Fake FVG, fake fractal → trap.
- **Sliquid (strong liquidity):**
  - PDH/PDL = target hoặc vùng entry.
  - Asia Range High/Low = medium liquidity, đôi khi nâng cấp thành strong liquidity.

## 6. Quản trị rủi ro
- Max Drawdown: 20%.
- Risk per trade: 1–2% equity.
- Chốt lời:
  - **Theo Daily bias:** TP1 tại 1:5, TP2 tại 1:10 hoặc PDH/L.
  - **Ngược Daily bias nhưng thuận MTF:** TP1 tại 1:3, TP2 tại 1:5.
- Không trade khi có news lớn.

## 7. Quản trị lệnh
- Có thể partial exit (chốt một phần) tại RR mục tiêu.
- Dời SL về BE khi đạt >1:3 (nếu phù hợp với setup).
- Giữ kỷ luật, tránh entry cảm tính.

## 8. Checklist trước phiên
- [ ] Daily bias xác định? (PDH/PDL break liên tục theo chiều nào?)
- [ ] MTF (M15) đồng thuận hay mâu thuẫn với Daily bias?
- [ ] Có liquidity sweep rõ ràng không?
- [ ] LTF (M1) cho tín hiệu entry đúng mẫu chưa (Risk / Re-test / Extreme)?
- [ ] Có tin tức lớn trong phiên không?

## 9. Kịch bản “What-if”
- Nếu **miss entry**: không chase, chờ re-test hoặc setup mới.
- Nếu **entry nhưng bị SL**: ghi lại screenshot, review liquidity + FVG alignment.
- Nếu **giá đi ngược Daily bias**: giảm kỳ vọng RR, thoát sớm hơn.
