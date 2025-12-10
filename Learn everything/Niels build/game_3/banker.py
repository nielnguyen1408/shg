import random
import itertools
from typing import Dict, List, Optional, Tuple

from config import (
    BOARD_ONLY_PENALTY,
    BOARD_WEAK_BOARD_CALL_MULTIPLIER,
    DRAW_FOLD_MULTIPLIER,
    FLOP_BOTTOM_PAIR_MULTIPLIER,
    FLOP_MID_PAIR_MULTIPLIER,
    FLOP_TOP_PAIR_MULTIPLIER,
    FOLD_EQUITY_SCALE,
    PREFLOP_BASE_MULTIPLIER,
    PREFLOP_FEATURE_STEP,
    PREFLOP_MAX_MULTIPLIER,
    PREFLOP_MIN_MULTIPLIER,
    RANKS,
    RIVER_WEAK_HAND_MULTIPLIER,
    RIVER_BOARD_PAIR_PENALTY,
    RIVER_BOARD_AIR_PENALTY,
    SUITS,
)
from poker_eval import best_hand, card_rank_value


def banker_strength_multiplier(
    level: int, tiebreak: List[int], best_combo: List[str], banker_cards: List[str], board_cards: List[str]
) -> float:
    """
    Convert hand strength to a fold-equity multiplier using the full ranking.
    Lower multiplier -> folds less. Incorporates sub-tiers for high card,
    flush, and straight, plus detection for “one-card” straights.
    """
    banker_cards_in_best = sum(1 for card in best_combo if card in banker_cards)

    if level == 8:  # Straight Flush
        return 0.2
    if level == 7:  # Quads
        return 0.25
    if level == 6:  # Full House
        return 0.35
    if level == 5:  # Flush
        top_rank = tiebreak[0]
        if top_rank >= 11:  # A/K high flush
            return 0.4
        if top_rank >= 8:  # Q/J/T high flush
            return 0.55
        return 0.75  # low flush
    if level == 4:  # Straight
        straight_high = tiebreak[0]
        if banker_cards_in_best <= 1:  # one-card or board straight
            if straight_high >= 10:  # Q-high or better
                return 0.75
            return 0.9
        if straight_high >= 10:
            return 0.6  # high straight
        if straight_high >= 7:  # 9-high / 8-high
            return 0.75
        return 0.9  # low straight
    if level == 3:  # Trips
        return 0.8
    if level == 2:  # Two Pair
        return 0.95
    if level == 1:  # One Pair (further tuned by pair_category elsewhere)
        return 1.05
    if level == 0:  # High Card
        high_card = tiebreak[0]
        if high_card >= 11:  # A/K high
            return 1.2
        return 1.45  # weaker highs
    return 1.0


def board_texture_level(board_cards: List[str]) -> Optional[int]:
    """
    Rough strength of the board alone (0-8 scale) to detect weak boards.
    Uses full evaluation once 5 cards are out; otherwise approximates
    with pairs/trips/2p vs. high card.
    """
    if len(board_cards) < 3:
        return None
    if len(board_cards) >= 5:
        level, _, _ = best_hand(board_cards)
        return level

    rank_counts = {}
    for card in board_cards:
        val = card_rank_value(card[0])
        rank_counts[val] = rank_counts.get(val, 0) + 1

    counts = sorted(rank_counts.values(), reverse=True)
    if counts[0] >= 3:
        return 3  # trips on board
    if len(counts) >= 2 and counts[0] == 2 and counts[1] == 2:
        return 2  # two pair on board
    if counts[0] == 2:
        return 1  # one pair on board
    return 0  # high card board


def banker_plays_board_only(banker_cards: List[str], board_cards: List[str]) -> bool:
    """
    True if the banker best hand uses only board cards (common chop),
    meaning banker has not improved beyond the board.
    """
    total_cards = banker_cards + board_cards
    if len(total_cards) < 5:
        return False
    _, _, banker_best_combo = best_hand(total_cards)
    return not any(card in banker_cards for card in banker_best_combo)


def range_strength_stats(
    banker_cards: List[str], board_cards: List[str]
) -> Tuple[int, int, int, int, Dict[int, int]]:
    """
    Evaluate banker hand vs. all remaining 2-card combos.
    Returns (better, tie, worse, total, counts_by_level).
    Counts help gauge how banker ranks within the possible hand space.
    """
    total_cards = banker_cards + board_cards
    if len(total_cards) < 5:
        return 0, 0, 0, 0, {}

    banker_rank = best_hand(total_cards)
    banker_level = banker_rank[0]

    deck = [r + s for r in RANKS for s in SUITS]
    remaining = [c for c in deck if c not in total_cards]

    better = tie = worse = 0
    counts_by_level: Dict[int, int] = {}

    for opp in itertools.combinations(remaining, 2):
        opp_level, _, _ = best_hand(list(opp) + board_cards)
        counts_by_level[opp_level] = counts_by_level.get(opp_level, 0) + 1
        if opp_level > banker_level:
            better += 1
        elif opp_level < banker_level:
            worse += 1
        else:
            tie += 1

    total = better + tie + worse
    return better, tie, worse, total, counts_by_level


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


def banker_folds(bet: int, pot: int, banker_cards: List[str], board_cards: List[str]) -> Tuple[bool, float]:
    """
    Decide whether the banker folds based on bet size, pot,
    and banker hand strength vs. the current board.
    Base formula: FE = bet / (bet + pot_effective).
    For pot <= 0, use pot_effective = bet so FE = 0.5.
    Then adjust FE by a multiplier derived from banker hand strength.
    """
    if bet <= 0:
        return False, 0.0
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
        # Post-flop: use full 7-card evaluation with richer sub-tiering.
        level, tiebreak, best_combo = best_hand(banker_cards + board_cards)
        strength_multiplier = banker_strength_multiplier(level, tiebreak, best_combo, banker_cards, board_cards)
        board_level = board_texture_level(board_cards)
        banker_cards_in_best = sum(1 for card in best_combo if card in banker_cards)
        board_only = banker_plays_board_only(banker_cards, board_cards)
        if board_only:
            strength_multiplier *= BOARD_ONLY_PENALTY
        if board_level is not None and board_level <= 1:
            # On weak boards (high card / single pair) where banker only plays board,
            # reduce fold-equity so banker calls more and avoids over-folding chops.
            if level == board_level and board_only:
                strength_multiplier *= BOARD_WEAK_BOARD_CALL_MULTIPLIER
        better, tie, worse, total, _ = range_strength_stats(banker_cards, board_cards)
        percentile = None
        boardish_air = False
        if board_level is not None and board_level >= 1 and banker_cards_in_best <= 1:
            # Board-pair or paired board, banker adds at most one card (weak kicker) -> treat as near air.
            boardish_air = True
        if total > 0:
            percentile = better / total  # 0 = nuts, 1 = worst
            if not boardish_air:
                if percentile <= 0.1:
                    strength_multiplier *= 0.5
                elif percentile <= 0.25:
                    strength_multiplier *= 0.65
                elif percentile <= 0.5:
                    strength_multiplier *= 0.85
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
            # One-pair that only exists on the board faces extra fold pressure on river.
            if level == 1 and board_level is not None and board_level >= 1 and banker_cards_in_best <= 1:
                strength_multiplier *= RIVER_BOARD_PAIR_PENALTY
                strength_multiplier *= RIVER_BOARD_AIR_PENALTY
    else:
        # Fallback (should not really happen in current flow).
        strength_multiplier = banker_strength_multiplier(0)

    draw_multiplier = 1.0
    has_draw = has_flush_draw(banker_cards, board_cards) or has_straight_draw(banker_cards, board_cards)
    if has_draw:
        # Only protect draws when hand isn't already very weak in range-percentile terms.
        # For weak/high-card trash near the bottom of range, keep FE higher (no reduction).
        if percentile is None or percentile <= 0.35 or level >= 2:
            draw_multiplier = DRAW_FOLD_MULTIPLIER

    fold_equity *= strength_multiplier * draw_multiplier * FOLD_EQUITY_SCALE
    fold_equity = max(0.0, min(1.0, fold_equity))
    return random.random() < fold_equity, fold_equity
