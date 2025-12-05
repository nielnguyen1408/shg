import random
from typing import List, Optional

from config import (
    DRAW_FOLD_MULTIPLIER,
    FLOP_BOTTOM_PAIR_MULTIPLIER,
    FLOP_MID_PAIR_MULTIPLIER,
    FLOP_TOP_PAIR_MULTIPLIER,
    FOLD_EQUITY_SCALE,
    PREFLOP_BASE_MULTIPLIER,
    PREFLOP_FEATURE_STEP,
    PREFLOP_MAX_MULTIPLIER,
    PREFLOP_MIN_MULTIPLIER,
    RIVER_WEAK_HAND_MULTIPLIER,
)
from poker_eval import best_hand, card_rank_value


def banker_strength_multiplier(level: int) -> float:
    """
    Convert banker hand strength level (0-8) to a fold-equity multiplier.
    Lower levels -> more likely to fold, higher levels -> less likely.
    """
    if level <= 1:  # High Card, One Pair
        return 1.5
    if level <= 3:  # Two Pair, Trips
        return 1.0
    if level <= 5:  # Straight, Flush
        return 0.7
    # Full House or better
    return 0.4


def preflop_banker_multiplier(banker_cards: List[str]) -> float:
    """
    Pre-flop adjustment: banker folds less with
    - high cards (A, K, Q),
    - suited hands,
    - connected / small-gap hands (rank difference <= 2).
    More of these features -> lower multiplier -> less folding.
    """
    if len(banker_cards) != 2:
        return PREFLOP_BASE_MULTIPLIER

    ranks = [c[0] for c in banker_cards]
    suits = [c[1] for c in banker_cards]

    high_ranks = {"A", "K", "Q", "J", "T"}
    high_count = sum(1 for r in ranks if r in high_ranks)

    suited = 1 if len(set(suits)) == 1 else 0

    idx = [card_rank_value(r) for r in ranks]
    connected = 1 if abs(idx[0] - idx[1]) <= 2 else 0

    feature_points = high_count + suited + connected

    mult = PREFLOP_BASE_MULTIPLIER - PREFLOP_FEATURE_STEP * feature_points
    mult = max(PREFLOP_MIN_MULTIPLIER, min(PREFLOP_MAX_MULTIPLIER, mult))
    return mult


def has_flush_draw(banker_cards: List[str], board_cards: List[str]) -> bool:
    if len(board_cards) not in {3, 4}:
        return False
    combined = banker_cards + board_cards
    suit_counts = {}
    for card in combined:
        suit_counts[card[1]] = suit_counts.get(card[1], 0) + 1
    banker_suits = {card[1] for card in banker_cards}
    for suit, count in suit_counts.items():
        if count >= 4 and count < 5 and suit in banker_suits:
            return True
    return False


def has_straight_draw(banker_cards: List[str], board_cards: List[str]) -> bool:
    if len(board_cards) not in {3, 4}:
        return False
    combined = banker_cards + board_cards
    values = {card_rank_value(card[0]) for card in combined}
    banker_values = {card_rank_value(card[0]) for card in banker_cards}

    # account for wheel draws (A2345)
    if 12 in values:  # Ace
        values.add(-1)
    if 12 in banker_values:
        banker_values.add(-1)

    for start in range(-1, 9):  # straight starting points
        window = {start + i for i in range(5)}
        present = values & window
        if len(present) == 4:
            if (banker_values & present):
                return True
    return False


def pair_category(banker_cards: List[str], board_cards: List[str]) -> Optional[str]:
    if not board_cards:
        return None
    board_values = [card_rank_value(card[0]) for card in board_cards]
    # unique ranks high->low
    unique_board: List[int] = []
    seen = set()
    for value in sorted(board_values, reverse=True):
        if value not in seen:
            unique_board.append(value)
            seen.add(value)
    hole_values = [card_rank_value(card[0]) for card in banker_cards]
    board_len = len(board_cards)

    def classify_index(idx: int) -> str:
        if board_len == 3:
            if idx == 0:
                return "top"
            if idx == 1:
                return "mid"
            return "bottom"
        if board_len == 4:
            if idx == 0:
                return "top"
            if idx in {1, 2}:
                return "mid"
            return "bottom"
        # river or greater
        if idx == 0:
            return "top"
        if idx in {1, 2}:
            return "mid"
        return "bottom"

    categories = []
    for value in hole_values:
        if value in unique_board:
            idx = unique_board.index(value)
            categories.append(classify_index(idx))

    if categories:
        if "top" in categories:
            return "top"
        if "mid" in categories:
            return "mid"
        return "bottom"

    # handle pocket pairs / overpairs / underpairs
    board_high = unique_board[0]
    board_low = unique_board[-1]
    if hole_values[0] == hole_values[1]:
        pair_value = hole_values[0]
        if pair_value > board_high:
            return "top"
        if pair_value < board_low:
            return "bottom"
        # treat as mid unless board only has two ranks
        if len(unique_board) <= 2:
            return "bottom"
        return "mid"

    # non-pocket pair beating top two ranks
    if len(unique_board) >= 2 and max(hole_values) > unique_board[1]:
        return "top"
    return None


def banker_folds(bet: int, pot: int, banker_cards: List[str], board_cards: List[str]) -> bool:
    """
    Decide whether the banker folds based on bet size, pot,
    and banker hand strength vs. the current board.
    Base formula: FE = bet / (bet + pot_effective).
    For pot <= 0, use pot_effective = bet so FE = 0.5.
    Then adjust FE by a multiplier derived from banker hand strength.
    """
    if bet <= 0:
        return False
    pot_effective = pot if pot > 0 else bet
    fold_equity = bet / (bet + pot_effective)

    total_cards = len(banker_cards) + len(board_cards)
    stage = None
    if len(board_cards) >= 3:
        if len(board_cards) == 3:
            stage = "flop"
        elif len(board_cards) == 4:
            stage = "turn"
        else:
            stage = "river"
    if total_cards <= 2:
        # Pure pre-flop: use hand-shape based heuristic.
        strength_multiplier = preflop_banker_multiplier(banker_cards)
    elif total_cards >= 5:
        # Post-flop: use full 7-card evaluation.
        level, _, _ = best_hand(banker_cards + board_cards)
        strength_multiplier = banker_strength_multiplier(level)
        if stage == "flop":
            category = pair_category(banker_cards, board_cards)
            if category == "top":
                strength_multiplier *= FLOP_TOP_PAIR_MULTIPLIER
            elif category == "mid":
                strength_multiplier *= FLOP_MID_PAIR_MULTIPLIER
            elif category == "bottom":
                strength_multiplier *= FLOP_BOTTOM_PAIR_MULTIPLIER
        if stage == "river" and level <= 1:
            strength_multiplier *= RIVER_WEAK_HAND_MULTIPLIER
    else:
        # Fallback (should not really happen in current flow).
        strength_multiplier = banker_strength_multiplier(0)

    draw_multiplier = 1.0
    if has_flush_draw(banker_cards, board_cards) or has_straight_draw(banker_cards, board_cards):
        draw_multiplier = DRAW_FOLD_MULTIPLIER

    fold_equity *= strength_multiplier * draw_multiplier * FOLD_EQUITY_SCALE
    fold_equity = max(0.0, min(1.0, fold_equity))
    return random.random() < fold_equity
