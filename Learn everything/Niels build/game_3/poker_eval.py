import itertools
from typing import List, Tuple

from config import RANKS


def card_rank_value(rank: str) -> int:
    return RANKS.index(rank)


def evaluate_five(cards: List[str]) -> Tuple[int, List[int]]:
    ranks = sorted((card_rank_value(c[0]) for c in cards), reverse=True)
    suits = [c[1] for c in cards]
    rank_counts = {}
    for r in ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1
    counts = sorted(rank_counts.items(), key=lambda x: (-x[1], -x[0]))
    is_flush = len(set(suits)) == 1

    unique_ranks = sorted(set(ranks), reverse=True)
    is_wheel = unique_ranks == [12, 3, 2, 1, 0]  # A,5,4,3,2
    straight_high = None
    if is_wheel:
        straight_high = 3  # represents 5-high straight
    elif len(unique_ranks) >= 5:
        for i in range(len(unique_ranks) - 4):
            window = unique_ranks[i : i + 5]
            if window[0] - window[-1] == 4:
                straight_high = window[0]
                break
    is_straight = straight_high is not None

    if is_straight and is_flush:
        return (8, [straight_high])
    if counts[0][1] == 4:
        four = counts[0][0]
        kicker = [r for r in ranks if r != four][0]
        return (7, [four, kicker])
    if counts[0][1] == 3 and counts[1][1] >= 2:
        trip = counts[0][0]
        pair = counts[1][0]
        return (6, [trip, pair])
    if is_flush:
        return (5, ranks)
    if is_straight:
        return (4, [straight_high])
    if counts[0][1] == 3:
        trip = counts[0][0]
        kickers = [r for r in ranks if r != trip][:2]
        return (3, [trip] + kickers)
    if counts[0][1] == 2 and counts[1][1] == 2:
        high_pair, low_pair = sorted([counts[0][0], counts[1][0]], reverse=True)
        kicker = [r for r in ranks if r not in (high_pair, low_pair)][0]
        return (2, [high_pair, low_pair, kicker])
    if counts[0][1] == 2:
        pair = counts[0][0]
        kickers = [r for r in ranks if r != pair][:3]
        return (1, [pair] + kickers)
    return (0, ranks)


HAND_NAMES = {
    8: "Straight Flush",
    7: "Four of a Kind",
    6: "Full House",
    5: "Flush",
    4: "Straight",
    3: "Three of a Kind",
    2: "Two Pair",
    1: "One Pair",
    0: "High Card",
}


def best_hand(seven_cards: List[str]) -> Tuple[int, List[int], List[str]]:
    best_rank = (-1, [])
    best_combo: List[str] = []
    for combo in itertools.combinations(seven_cards, 5):
        rank = evaluate_five(list(combo))
        if rank > best_rank:
            best_rank = rank
            best_combo = list(combo)
    level, tiebreak = best_rank
    return level, tiebreak, best_combo


def compare_hands(player_cards: List[str], banker_cards: List[str], board: List[str]) -> Tuple[str, str]:
    player_rank = best_hand(player_cards + board)
    banker_rank = best_hand(banker_cards + board)
    if player_rank > banker_rank:
        winner = "player"
        description = HAND_NAMES[player_rank[0]]
    elif banker_rank > player_rank:
        winner = "banker"
        description = HAND_NAMES[banker_rank[0]]
    else:
        winner = "tie"
        description = HAND_NAMES[player_rank[0]]
    return winner, description

