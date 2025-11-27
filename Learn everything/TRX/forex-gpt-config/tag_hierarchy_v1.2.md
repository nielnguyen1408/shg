# Tag Hierarchy v1.2 – Liquidity-Based Trading System

| Category   | Tag                         | Description                                                                    | Logic Group        |
|:-----------|:----------------------------|:-------------------------------------------------------------------------------|:-------------------|
| Context    | #mtf_swept_strong_liquid    | HTF vừa quét external liquidity mạnh (equal highs/lows hoặc swing major)       | MTF Liquidity      |
| Context    | #mtf_swept_new_liquid       | HTF hình thành vùng liquidity mới sau break, chưa sweep lại                    | MTF Liquidity      |
| Context    | #mtf_external_liquid_active | External liquidity chưa bị quét, còn khả năng kéo tiếp                         | MTF Liquidity      |
| Context    | #mtf_fvg_active             | FVG trên khung lớn chưa lấp, giữ bias cùng xu hướng                            | MTF Imbalance      |
| Context    | #mtf_fvg_filled             | FVG đã được lấp, thị trường có thể vào phase tái tích lũy                      | MTF Imbalance      |
| Context    | #trend_context              | Cấu trúc HTF intact, bias theo trend chính                                     | Structure Context  |
| Context    | #transition_context         | HTF xuất hiện BOS hoặc shift, dòng tiền đang chuyển pha                        | Structure Context  |
| Context    | #reversal_context           | Sau external sweep + BOS rõ, bias ngược trend                                  | Structure Context  |
| Behaviour  | #ltf_ranging                | Giá M15–M5 đi ngang, internal liquidity đang tích tụ                           | Micro Structure    |
| Behaviour  | #ltf_cz_forming             | CZ đang hình thành sau impulsive leg                                           | Micro Structure    |
| Behaviour  | #ltf_cz_hold                | CZ giữ ổn định sau sweep, chưa phá cấu trúc                                    | Micro Structure    |
| Behaviour  | #ltf_cz_break               | CZ bị phá, chuyển sang pullback hoặc đảo chiều                                 | Micro Structure    |
| Behaviour  | #ltf_internal_sweep         | Sweep liquidity nội bộ trong CZ hoặc compression zone                          | Liquidity Event    |
| Behaviour  | #ltf_external_sweep         | Sweep liquidity ngoài CZ (ví dụ equal high/low)                                | Liquidity Event    |
| Behaviour  | #ltf_fvg                    | FVG nội bộ còn mở, bias cùng chiều vẫn hoạt động                               | Imbalance          |
| Behaviour  | #ltf_fvg_filled             | FVG nội bộ được lấp, giá có thể nghỉ hoặc đảo                                  | Imbalance          |
| Execution  | #entry_extreme              | Entry tại vùng cực (sweep + rejection)                                         | Entry              |
| Execution  | #entry_followup             | Entry xác nhận flow sau sweep hoặc BOS                                         | Entry              |
| Execution  | #entry_skip_no_liquid       | Bỏ qua setup vì không có sweep hoặc liquidity rõ                               | Filter             |
| Execution  | #reentry_same_flow          | Entry lại cùng hướng sau CZ giữ                                                | Trade Management   |
| Execution  | #reverse_after_cz_break     | Entry ngược chiều sau khi CZ bị phá                                            | Trade Management   |
| Execution  | #exit_partial               | Thoát một phần khi momentum giảm hoặc CZ mới hình thành                        | Exit               |
| Execution  | #exit_full                  | Đóng hoàn toàn (TP, SL hoặc mất cấu trúc)                                      | Exit               |
| Execution  | #exit_early                 | Thoát sớm vì sideway, cảm xúc hoặc thiếu momentum                              | Exit               |
| Meta       | #continuation_setup         | CZ giữ + internal sweep → tiếp diễn xu hướng                                   | Setup Type         |
| Meta       | #reversal_setup             | External sweep + CZ break → đảo chiều                                          | Setup Type         |
| Meta       | #liquid_based_entry         | Entry được xác nhận bằng sweep rõ ràng                                         | Entry Validation   |
| Meta       | #no_liquidity_skip          | Không vào do thiếu thanh khoản                                                 | Entry Validation   |
| Meta       | #trap_zone                  | CZ bật không sweep → khả năng trap cao                                         | Trap Warning       |
| Meta       | #high_quality_flow          | Có alignment rõ giữa HTF liquidity và LTF sweep                                | Confidence Layer   |
| Meta       | #low_quality_flow           | Liquidity mơ hồ, flow lệch giữa các khung                                      | Confidence Layer   |
| Session    | #asia_session               | Entry/price action hình thành trong phiên Á (thanh khoản thấp, range nhỏ)      | Session Context    |
| Session    | #london_session             | Biến động mở rộng, breakout CZ phổ biến                                        | Session Context    |
| Session    | #ny_session                 | Pha quyết định, thường sweep London high/low trước chạy                        | Session Context    |
| Session    | #pre_london                 | Giai đoạn tích lũy trước London open                                           | Session Context    |
| Session    | #post_ny                    | Phiên NY muộn, thanh khoản giảm, dễ trap                                       | Session Context    |
| Event      | #pre_event                  | 30–60 phút trước tin, thị trường nén, tạo trap liquidity                       | News Context       |
| Event      | #post_event                 | Sau tin mạnh (CPI, NFP, FOMC…), dòng tiền reset hoặc làm BOS                   | News Context       |
| Event      | #event_volatility_spike     | Tin tức vừa ra, spike mạnh tạo external sweep                                  | News Context       |
| Event      | #event_consolidation        | Sau biến động tin, giá tái tích lũy quanh range                                | News Context       |
| Psych      | #revenge_trade              | Vào lệnh do cảm xúc muốn “lấy lại”, không theo setup                           | Emotional Trigger  |
| Psych      | #missed_profit_bias         | Bị ảnh hưởng bởi việc vừa bỏ lỡ cơ hội lớn, vào lệnh vội                       | Emotional Trigger  |
| Psych      | #tilt_after_loss            | Thua chuỗi lệnh → mất trung tính, ép trade                                     | Emotional Trigger  |
| Psych      | #pre_event_fomo             | Giao dịch quá gần thời điểm tin vì sợ “bỏ lỡ sóng”                             | Event-Induced Bias |
| Psych      | #execution_error_reentry    | Re-entry sau lỗi kỹ thuật (slippage, disconnect...) mà không có setup xác nhận | Recovery Bias      |
| Psych      | #frustration_trade          | Vào lệnh do bực, chán chờ, hoặc mất kiên nhẫn                                  | Impulse Trade      |
| Psych      | #slippage_triggered_emotion | Cảm xúc nảy sinh sau khi SL bị trượt mạnh                                      | Execution Emotion  |