import random
import time

from game_config import (
    BET_HOTKEY,
    BET_SUCCESS_PROB,
    BET_WIN_MULTIPLIER,
    FINAL_STREAK_HEADCAP,
    GOAL_COMBO,
    UPGRADE_HOTKEY,
)
from save_load import init_progress, reset_progress, save_progress
from upgrades import list_upgrades, purchase_upgrade

try:
    import msvcrt
except ImportError:
    msvcrt = None


goal_combo = GOAL_COMBO
state = init_progress()


def flip_a_coin(probability):
    return random.random() < probability


def combo_reward(streak, base_value, multiplier):
    if streak <= 0:
        return 0.0
    return base_value * (multiplier ** (streak - 1))


def prompt_upgrade_menu():
    upgrade_infos = list_upgrades(state)
    print(f"\n=== Upgrade Shop === (money: {_format_money(state['money'])}$)")
    for idx, info in enumerate(upgrade_infos, start=1):
        max_info = ""
        if info["max_level"] is not None:
            max_info = f"/{info['max_level']}"
        if info["maxed"]:
            cost_text = "MAXED"
            status = "MAX"
        else:
            cost_text = f"{_format_money(info['cost'])}$"
            status = "BUY" if info["affordable"] else "locked"
        current_value = _format_upgrade_current_value(info["name"])
        print(
            f" {idx}. {info['label']} (lvl {info['level']}{max_info})"
            f" | Current: {current_value}"
        )
        print(f"      Cost: {cost_text} [{status}]")
        print(f"      Effect: {info['description']}")

    if not any(info["affordable"] for info in upgrade_infos):
        print("No affordable upgrades right now.")
        return

    choice = input("Select upgrade number or press Enter to cancel: ").strip()
    if not choice:
        return
    if not choice.isdigit():
        print("Invalid selection.")
        return
    selection = int(choice)
    if not 1 <= selection <= len(upgrade_infos):
        print("Invalid selection.")
        return
    selected = upgrade_infos[selection - 1]
    if selected["maxed"]:
        print(f"{selected['label']} is already maxed out.")
        return
    if not selected["affordable"]:
        print(f"Not enough money for {selected['label']}.")
        return
    try:
        purchased = purchase_upgrade(state, selected["name"])
    except ValueError as err:
        print(err)
        return
    print(
        f"Purchased {purchased.label}! "
        f"New level {state['upgrades'][purchased.key]}, "
        f"money left {_format_money(state['money'])}$."
    )
    save_progress(state)


def _affordable_upgrade_available():
    return any(info["affordable"] for info in list_upgrades(state))


def _bet_available():
    return state["money"] > 0


def _poll_hotkeys():
    if not msvcrt:
        return set()
    pressed = set()
    while msvcrt.kbhit():
        key = msvcrt.getwch().lower()
        pressed.add(key)
    return pressed


def _format_money(value):
    return f"{value:,.2f}"


def _format_upgrade_current_value(name):
    if name == "coin_value":
        return f"{_format_money(state['coin_value'])}$"
    if name == "head_prob":
        return f"{state['head_prob'] * 100:.1f}%"
    if name == "flip_interval":
        return f"{state['flip_interval']:.1f}s"
    if name == "combo_multiplier":
        return f"{state['combo_multiplier']:.1f}x"
    return "-"


def _format_duration(seconds):
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes or hours:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def _perform_bet():
    global state
    bankroll = state["money"]
    if bankroll <= 0:
        print("No money to bet.")
        return
    print(
        f"\nBetting all-in: {_format_money(bankroll)}$ "
        f"with {BET_SUCCESS_PROB * 100:.0f}% chance to x{BET_WIN_MULTIPLIER}."
    )
    win = random.random() < BET_SUCCESS_PROB
    if win:
        state["money"] *= BET_WIN_MULTIPLIER
        print(f"Bet won! New balance: {_format_money(state['money'])}$.")
    else:
        state["money"] = 0.0
        print("Bet lost! Balance dropped to 0$.")
        state["streak"] = 0
    save_progress(state)


def _already_won():
    return state["streak"] >= goal_combo


def _prompt_play_again():
    while True:
        choice = input("You win! Play again? (y/N): ").strip().lower()
        if choice in {"y", "yes"}:
            return True
        if choice in {"", "n", "no"}:
            return False
        print("Please answer y or n.")


def _play_until_goal():
    global state
    upgrade_notice_shown = False
    bet_notice_shown = False
    session_start = time.time()
    base_elapsed = state.get("elapsed_seconds", 0.0)
    while state["streak"] < goal_combo:
        probability = state["head_prob"]
        if state["streak"] == goal_combo - 1:
            probability = min(probability, FINAL_STREAK_HEADCAP)
        flip_result = flip_a_coin(probability)
        reward = 0.0
        if flip_result:
            state["streak"] += 1
            reward = combo_reward(state["streak"], state["coin_value"], state["combo_multiplier"])
            state["money"] += reward
        else:
            state["streak"] = 0
        state["flips"] += 1
        elapsed = base_elapsed + (time.time() - session_start)
        flip_label = "Head" if flip_result else "Tail"
        reward_text = f" | reward = +{_format_money(reward)}$" if flip_result and state["streak"] > 1 else ""
        print(
            f"Flip #{state['flips']}: {flip_label}, "
            f"streak = {state['streak']}, money = {_format_money(state['money'])}$"
            f" | total flips: {state['flips']} | time: {_format_duration(elapsed)}{reward_text}",
        )
        state["elapsed_seconds"] = elapsed
        save_progress(state)
        pressed_keys = _poll_hotkeys()
        has_affordable = _affordable_upgrade_available()
        bet_possible = _bet_available()
        if BET_HOTKEY in pressed_keys:
            _perform_bet()
            bet_notice_shown = False
            upgrade_notice_shown = False
        elif UPGRADE_HOTKEY in pressed_keys:
            prompt_upgrade_menu()
            upgrade_notice_shown = False
        elif has_affordable:
            if not upgrade_notice_shown:
                print(f"Press '{UPGRADE_HOTKEY.upper()}' to open the upgrade shop.")
                upgrade_notice_shown = True
        else:
            upgrade_notice_shown = False
        if bet_possible and BET_HOTKEY not in pressed_keys:
            if not bet_notice_shown:
                print(
                    f"Press '{BET_HOTKEY.upper()}' to bet all-in "
                    f"({BET_SUCCESS_PROB * 100:.0f}% chance to x{BET_WIN_MULTIPLIER})."
                )
                bet_notice_shown = True
        elif not bet_possible:
            bet_notice_shown = False
        time.sleep(state["flip_interval"])
    print(f"\nReached goal streak of {goal_combo}! You win!")


def main():
    global state
    while True:
        if _already_won():
            if not _prompt_play_again():
                print("Thanks for playing!")
                break
            state = reset_progress()
            continue
        _play_until_goal()
        if not _prompt_play_again():
            print("Thanks for playing!")
            break
        state = reset_progress()


if __name__ == "__main__":
    main()
