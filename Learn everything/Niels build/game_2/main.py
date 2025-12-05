"""
Simple idle bitcoin miner.

Run this file and it will keep incrementing the bitcoin balance stored in
save.json. Progress is persisted whenever the balance changes so the number
keeps going up even after restarts.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


SAVE_PATH = Path(__file__).with_name("save.json")
COIN_INTERVAL_SECONDS = 5  # 1 coin every 5 seconds
COIN_RATE = 1 / COIN_INTERVAL_SECONDS  # coins per second
WRITE_PRECISION = 8  # decimal places when persisting floats


def _default_state() -> dict[str, float]:
    now = time.time()
    return {"bitcoin": 0.0, "last_update": now}


def load_state() -> dict[str, float]:
    if not SAVE_PATH.exists() or SAVE_PATH.stat().st_size == 0:
        return _default_state()

    try:
        with SAVE_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return _default_state()

    bitcoin = float(data.get("bitcoin", 0.0))
    last_update = float(data.get("last_update", time.time()))
    return {"bitcoin": bitcoin, "last_update": last_update}


def save_state(state: dict[str, float]) -> None:
    serializable = {
        "bitcoin": round(state["bitcoin"], WRITE_PRECISION),
        "last_update": state["last_update"],
    }
    with SAVE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(serializable, fh, indent=2)


def accrue_income(state: dict[str, float]) -> float:
    now = time.time()
    elapsed = max(0.0, now - state.get("last_update", now))
    if elapsed <= 0:
        return 0.0

    earned = elapsed * COIN_RATE
    state["bitcoin"] += earned
    state["last_update"] = now
    return earned


def main() -> None:
    state = load_state()
    offline_earned = accrue_income(state)
    save_state(state)

    if offline_earned:
        print(
            f"Khoi dong lai, ban da kiem them {offline_earned:.4f} BTC trong luc offline."
        )

    print("Dang dao bitcoin... nhan Ctrl+C de dung.")

    try:
        while True:
            time.sleep(1)
            earned = accrue_income(state)
            if earned > 0:
                save_state(state)
                print(
                    f"+{earned:.4f} BTC | Tong cong: {state['bitcoin']:.4f} BTC",
                    flush=True,
                )
    except KeyboardInterrupt:
        save_state(state)
        print("\nDa luu tien trinh. Hen gap lai!")


if __name__ == "__main__":
    main()
