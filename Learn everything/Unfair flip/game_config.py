from pathlib import Path

# Save / persistence
SAVE_FILENAME = "save.json"

# Upgrade economy
BASE_COST = 0.1
COST_MULTIPLIER = 10
COIN_VALUE_MULTIPLIER = 2.0
HEAD_PROB_INCREMENT = 0.1
FLIP_INTERVAL_DECREMENT = 0.2
COMBO_MULTIPLIER_INCREMENT = 0.1

# Stat caps / floors
MAX_HEAD_PROB = 0.9
MIN_FLIP_INTERVAL = 0.1
MAX_COMBO_MULTIPLIER = 5.0
FINAL_STREAK_HEADCAP = 1.0

# Starting stats
DEFAULT_COIN_VALUE = 0.01
DEFAULT_HEAD_PROB = 0.2
DEFAULT_FLIP_INTERVAL = 1.0
DEFAULT_COMBO_MULTIPLIER = 1.5

# Gameplay settings
GOAL_COMBO = 20
UPGRADE_HOTKEY = "u"
BET_HOTKEY = "b"
BET_WIN_MULTIPLIER = 2.0
BET_SUCCESS_PROB = 0.5

# Default save-state payload
DEFAULT_STATE = {
    "money": 0.0,
    "streak": 0,
    "coin_value": DEFAULT_COIN_VALUE,
    "flip_interval": DEFAULT_FLIP_INTERVAL,
    "head_prob": DEFAULT_HEAD_PROB,
    "combo_multiplier": DEFAULT_COMBO_MULTIPLIER,
    "flips": 0,
    "elapsed_seconds": 0.0,
    "upgrades": {
        "coin_value": 0,
        "head_prob": 0,
        "flip_interval": 0,
        "combo_multiplier": 0,
    },
}


def save_path(base_dir: Path | None = None) -> Path:
    """Compute the save path, optionally relative to a provided directory."""
    if base_dir is None:
        return Path(SAVE_FILENAME)
    return base_dir / SAVE_FILENAME
