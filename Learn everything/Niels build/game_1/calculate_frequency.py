from itertools import product


#high = sum(1 for roll in outcomes if 10 <= sum(roll) <= 18)
#low = sum(1 for roll in outcomes if 3 <= sum(roll) <= 9)
#print(high / len(outcomes), low / len(outcomes))

# Loop mọi kết hợp có thể xảy ra
outcomes = list(product(range(1,7), repeat = 3))
total_outcomes = sum(1 for _ in product(range(1,7), repeat =3)) # Tổng các thể loại có thể xảy ra

# Lưu các loại có thể xảy ra thành dict để chuẩn bị brute force đếm tần suất
counts = {
    "high" : {"count" : 0, "prob": 0.0},
    "low" : {"count" : 0, "prob": 0.0},
    "top" : {"count" : 0, "prob": 0.0},
    "bot" : {"count" : 0, "prob": 0.0},
    "dup" : {"count" : 0, "prob": 0.0},
    "con" : {"count" : 0, "prob": 0.0}
}

for roll in outcomes:
    s = sum(roll)
    if 11 <= s <= 18:
        counts["high"]["count"] += 1
    if 3 <= s <= 10:
        counts["low"]["count"] += 1
    
    if roll == (6, 6, 6):
        counts["top"]["count"] += 1
    elif roll == (1, 1, 1):
        counts["bot"]["count"] += 1
    elif len(set(roll)) == 1:
        counts["dup"]["count"] += 1 # Các triple khác
    
    sorted_roll = sorted(roll)
    if len(set(sorted_roll)) == 3 and sorted_roll[2] - sorted_roll[1] == sorted_roll[1] - sorted_roll[0] == 1:
        counts["con"]["count"] += 1

# Tinh toan probility
for bet, data in counts.items():
    print(f" {bet} , {data}")
    data["prob"] = data["count"] / total_outcomes

# Print ket qua cuoi cung
for bet, data in counts.items():
    print(f"{bet} : {data['prob']*100:.2f} % ")