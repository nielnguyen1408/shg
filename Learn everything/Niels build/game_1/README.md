# Betting game
Phiên bản dễ nhất là chúng ta bet vào một sự flip của đồng xu
Money = Deposit usdt
Bet = betting amount
Số xúc xắc: 3

High: Khi giá trị xúc xắc từ 10 tới 18
Low: Khi giá trị xúc xắc từ 3 tới 9
Top: Khi giá trị xúc xắc đạt 666
Bot: Khi giá trị xúc xắc đạt 111
Con: Khi giá trị xúc xắc đạt chuỗi số liên tiếp (ví dụ: 123 234 345)
Dup: Khi giá trị xúc xắc đạt 3 số giống nhau bất kỳ trừ 111 và 666 (222, 333, 444, 555)

Mỗi điểm sẽ có hệ số nhân nhất định
High: x2
Low: x2
Top/Bot: Tính toán tần suất rồi trả lại chỉ số
Con: Tính toán tần suất rồi trả lại chỉ số
Dup: Tính toán tần suất rồi trả lại chỉ số