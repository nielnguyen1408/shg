import math
from dataclasses import dataclass

from game_config import (
    BASE_COST,
    COMBO_MULTIPLIER_INCREMENT,
    COST_MULTIPLIER,
    COIN_VALUE_MULTIPLIER,
    DEFAULT_COMBO_MULTIPLIER,
    DEFAULT_FLIP_INTERVAL,
    DEFAULT_HEAD_PROB,
    FLIP_INTERVAL_DECREMENT,
    HEAD_PROB_INCREMENT,
    MAX_COMBO_MULTIPLIER,
    MAX_HEAD_PROB,
    MIN_FLIP_INTERVAL,
)

def _compute_levels(max_value, default_value, step, *, ceil=False):
    if step <= 0:
        return 0
    levels = (max_value - default_value) / step
    if ceil:
        return max(0, math.ceil(levels))
    return max(0, int(round(levels)))


HEAD_PROB_MAX_LEVEL = _compute_levels(MAX_HEAD_PROB, DEFAULT_HEAD_PROB, HEAD_PROB_INCREMENT)
FLIP_INTERVAL_MAX_LEVEL = _compute_levels(
    DEFAULT_FLIP_INTERVAL, MIN_FLIP_INTERVAL, FLIP_INTERVAL_DECREMENT, ceil=True
)
COMBO_MULTIPLIER_MAX_LEVEL = _compute_levels(
    MAX_COMBO_MULTIPLIER, DEFAULT_COMBO_MULTIPLIER, COMBO_MULTIPLIER_INCREMENT
)


@dataclass(frozen=True)
class Upgrade:
    key: str
    label: str
    description: str
    max_level: int | None = None


UPGRADES = {
    "coin_value": Upgrade(
        key="coin_value",
        label="Coin Value",
        description="Doubles the reward per Head flip.",
        max_level=None,
    ),
    "head_prob": Upgrade(
        key="head_prob",
        label="Flip Chance",
        description=f"Increase head probability by {HEAD_PROB_INCREMENT * 100:.0f}% (capped at {MAX_HEAD_PROB * 100:.0f}%).",
        max_level=HEAD_PROB_MAX_LEVEL,
    ),
    "flip_interval": Upgrade(
        key="flip_interval",
        label="Flip Time",
        description="Reduce time between flips by 0.2s (capped at 0.1s).",
        max_level=FLIP_INTERVAL_MAX_LEVEL,
    ),
    "combo_multiplier": Upgrade(
        key="combo_multiplier",
        label="Combo Value",
        description="Increase combo multiplier by 0.1 (caps at 5x).",
        max_level=COMBO_MULTIPLIER_MAX_LEVEL,
    ),
}


def get_upgrade_cost(state, upgrade_name):
    _ensure_upgrade_state(state)
    upgrade = _get_upgrade(upgrade_name)
    if _is_maxed(state, upgrade):
        return None
    level = state["upgrades"][upgrade.key]
    return BASE_COST * (COST_MULTIPLIER ** level)


def can_purchase(state, upgrade_name):
    cost = get_upgrade_cost(state, upgrade_name)
    if cost is None:
        return False
    return state["money"] >= cost


def list_upgrades(state):
    _ensure_upgrade_state(state)
    upgrades = []
    for upgrade in UPGRADES.values():
        level = state["upgrades"][upgrade.key]
        maxed = _is_maxed(state, upgrade)
        cost = None if maxed else get_upgrade_cost(state, upgrade.key)
        affordable = False if maxed else state["money"] >= cost
        upgrades.append(
            {
                "name": upgrade.key,
                "label": upgrade.label,
                "level": level,
                "cost": cost,
                "description": upgrade.description,
                "affordable": affordable,
                "maxed": maxed,
                "max_level": upgrade.max_level,
            }
        )
    return upgrades


def purchase_upgrade(state, upgrade_name):
    _ensure_upgrade_state(state)
    upgrade = _get_upgrade(upgrade_name)
    if _is_maxed(state, upgrade):
        raise ValueError(f"{upgrade.label} is already at the maximum level.")
    cost = get_upgrade_cost(state, upgrade.key)
    if cost is None or state["money"] < cost:
        raise ValueError(f"Not enough money to buy {upgrade.label}. Required {cost:.2f}.")

    if upgrade.key == "coin_value":
        state["coin_value"] *= COIN_VALUE_MULTIPLIER
    elif upgrade.key == "head_prob":
        state["head_prob"] = min(MAX_HEAD_PROB, state["head_prob"] + HEAD_PROB_INCREMENT)
    elif upgrade.key == "flip_interval":
        state["flip_interval"] = max(MIN_FLIP_INTERVAL, state["flip_interval"] - FLIP_INTERVAL_DECREMENT)
    elif upgrade.key == "combo_multiplier":
        state["combo_multiplier"] = min(
            MAX_COMBO_MULTIPLIER, state["combo_multiplier"] + COMBO_MULTIPLIER_INCREMENT
        )

    state["upgrades"][upgrade.key] += 1
    state["money"] -= cost
    return upgrade


def _ensure_upgrade_state(state):
    state.setdefault(
        "upgrades",
        {
            "coin_value": 0,
            "head_prob": 0,
            "flip_interval": 0,
            "combo_multiplier": 0,
        },
    )


def _get_upgrade(upgrade_name):
    key = upgrade_name.strip().lower()
    if key not in UPGRADES:
        raise ValueError(f"Unknown upgrade '{upgrade_name}'. Options: {', '.join(UPGRADES)}")
    return UPGRADES[key]


def _is_maxed(state, upgrade):
    if upgrade.max_level is None:
        return False
    return state["upgrades"][upgrade.key] >= upgrade.max_level
