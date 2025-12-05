import copy
import json

from game_config import DEFAULT_STATE, save_path


SAVE_PATH = save_path()


def _default_state():
    return copy.deepcopy(DEFAULT_STATE)


def _normalize_state(raw_state):
    state = _default_state()
    state.update(raw_state or {})
    state["money"] = float(state.get("money", 0.0))
    state["streak"] = int(state.get("streak", 0))
    state["coin_value"] = float(state.get("coin_value", DEFAULT_STATE["coin_value"]))
    state["flip_interval"] = float(state.get("flip_interval", DEFAULT_STATE["flip_interval"]))
    state["head_prob"] = float(state.get("head_prob", DEFAULT_STATE["head_prob"]))
    state["combo_multiplier"] = float(state.get("combo_multiplier", DEFAULT_STATE["combo_multiplier"]))
    state["flips"] = int(state.get("flips", 0))
    state["elapsed_seconds"] = float(state.get("elapsed_seconds", 0.0))

    upgrades = state.get("upgrades") or {}
    state["upgrades"] = {
        "coin_value": int(upgrades.get("coin_value", 0)),
        "head_prob": int(upgrades.get("head_prob", 0)),
        "flip_interval": int(upgrades.get("flip_interval", 0)),
        "combo_multiplier": int(upgrades.get("combo_multiplier", 0)),
    }
    return state


def load_progress():
    try:
        data = json.loads(SAVE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return _default_state()
    return _normalize_state(data)


def reset_progress():
    SAVE_PATH.write_text(json.dumps(DEFAULT_STATE))
    return _default_state()


def init_progress():
    user_choice = input("Type 'reset' to clear the save or press Enter to continue: ").strip().lower()
    if user_choice in {"reset", "r"}:
        return reset_progress()
    return load_progress()


def save_progress(state):
    normalized = _normalize_state(state)
    normalized["money"] = round(normalized["money"], 2)
    SAVE_PATH.write_text(json.dumps(normalized))
