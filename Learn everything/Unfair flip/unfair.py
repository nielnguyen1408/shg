import random
import time
import json
from pathlib import Path

# Chỗ này để load từ file json ra thông tin
SAVE_PATH = Path("save.json")

def _load_progress():
    try:
        data = json.loads(SAVE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return 0.0, 0
    money = float(data.get("money", 0.0))
    streak = int(data.get("streak", 0))
    return money, streak

def _reset_progress():
    default_state = {"money": 0.0, "streak": 0}
    SAVE_PATH.write_text(json.dumps(default_state))
    return default_state["money"], default_state["streak"]

def _init_progress():
    user_choice = input("Type 'reset' to clear the save or press Enter to continue: ").strip().lower()
    if user_choice in {"reset", "r"}:
        return _reset_progress()
    return _load_progress()



# Main code
head_prob = 0.5
coin_value = 0.01
goal_combo = 10
flip_interval = 1
money, streak = _init_progress()

def flip_a_coin(prob = head_prob):
    result = random.random() < prob
    return result

def apply_flip_result(is_head, current_money):
    if is_head:
        current_money += coin_value
    return current_money

def main():
    while streak < goal_combo:
        flip_result = flip_a_coin()
        money = apply_flip_result(flip_result, money)
        streak = streak + 1 if flip_result else 0
        print(f"Flip #{streak}: {flip_result}, streak = {streak}, money = {money:.2f}")
        # Dữ liệu để lưu vào json
        data = {
            "money": round(money, 2),
            "streak": streak
            }
        SAVE_PATH.write_text(json.dumps(data))

        time.sleep(flip_interval)

main()