# Unfair Flip
## Objective
Giả lập flip coin & kiếm tiền
Khởi đầu với một đồng xu có tỷ lệ 20% head, 80% tail
Người chơi sẽ phải flip đồng xu đó đạt head để có tiền
Giá trị mỗi đồng xu khởi đầu sẽ có giá 0.01$
Thời gian flip mỗi lần là 1.5 giây
Khi đạt được head combo sẽ được multiple value, thêm 1.2 mỗi combo head, cộng dồn

Mục tiêu cuối cùng là đạt được 10 lần flip head in a row

Có các nâng cấp sau:
- Tăng tỷ lệ head thêm 5%
- Tăng giá trị của đồng xu
- Giảm thời gian flip đi 0.1 giây mỗi lần
- Tăng multiple combo thêm 0.2 mỗi lần

## Build code
- Determine the main loop
- determine the variable