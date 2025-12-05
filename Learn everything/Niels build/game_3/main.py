import itertools
import json
import os
import random
import sys
from typing import List, Optional, Tuple


RANKS = "2 3 4 5 6 7 8 9 T J Q K A".split()
SUITS = ["s", "h", "d", "c"]  # spades, hearts, diamonds, clubs
START_BANKROLL = 1_000
TARGET_BANKROLL = 100_000_000
SAVE_FILE = "save.json"


def build_deck() -> List[str]:
    return [r + s for r in RANKS for s in SUITS]


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


def render_cards(label: str, cards: List[str]):
    print(f"{label}: {' '.join(cards)}")


def save_game(balance: int, hand_number: int) -> None:
    data = {"balance": balance, "hand_number": hand_number}
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"Game saved to {SAVE_FILE}.")


def load_game() -> Optional[Tuple[int, int]]:
    if not os.path.exists(SAVE_FILE):
        return None
    while True:
        choice = input(f"Found {SAVE_FILE}. Load it? [Enter=yes / n=no / r=reset]: ").strip().lower()
        if choice in {"", "y", "yes"}:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            balance = int(data.get("balance", START_BANKROLL))
            hand_number = int(data.get("hand_number", 1))
            print(f"Loaded game: balance ${balance:,}, starting at hand {hand_number}.")
            return balance, hand_number
        if choice in {"r", "reset"}:
            os.remove(SAVE_FILE)
            print("Save reset. Starting new game.")
            return None
        if choice in {"n", "no"}:
            return None
        print("Please enter y, n, or r.")


def prompt_street_bet(street: str, pot: int, balance: int, hand_number: int, preflop: bool = False) -> int:
    if preflop and pot == 0:
        max_bet = balance  # no minimum; you can check or bet any amount up to balance
        bet_range_text = f"0=check, 1-{max_bet}"
    else:
        max_bet = min(balance, max(2 * pot, 1))
        bet_range_text = f"0=check, 1-{max_bet}"
    while True:
        raw = input(f"{street} pot ${pot}: Enter bet ({bet_range_text}, or q to save & quit): ").strip().lower()
        if raw in {"q", "quit"}:
            save_game(balance, hand_number)
            print("Saved. Exiting game.")
            sys.exit(0)
        if raw == "" or raw == "0":
            return 0
        if not raw.isdigit():
            print("Please enter a number.")
            continue
        amount = int(raw)
        if 1 <= amount <= max_bet:
            return amount
        print(f"Bet must be between 0 and {max_bet}.")


def main():
    print("Poker one-player (you vs. banker auto-calls)")
    print(f"Start bankroll: ${START_BANKROLL:,} | Goal: ${TARGET_BANKROLL:,}")
    loaded = load_game()
    if loaded:
        balance, hand_number = loaded
    else:
        balance = START_BANKROLL
        hand_number = 1

    while 0 < balance < TARGET_BANKROLL:
        print(f"\n--- Hand {hand_number} ---")
        print(f"Balance: ${balance:,}")

        deck = build_deck()
        random.shuffle(deck)
        player_cards = deck[:2]
        banker_cards = deck[2:4]
        board = deck[4:9]

        print("Hole cards dealt. You only see your own; banker is hidden.")
        render_cards("Player", player_cards)
        print("Banker: ?? ??")

        pot = 0
        player_contrib = 0
        banker_contrib = 0

        # Pre-Flop betting (no community cards yet)
        print("Pre-Flop: bet based on your hole cards.")
        bet = prompt_street_bet("Pre-Flop", pot, balance, hand_number, preflop=True)
        if bet > 0:
            player_contrib += bet
            banker_contrib += bet  # banker always calls
            balance -= bet
            pot = player_contrib + banker_contrib
            print(f"Banker calls {bet}. Pot now ${pot}. Your balance: ${balance:,}")
        else:
            pot = player_contrib + banker_contrib
            print(f"Pre-Flop: check. Pot ${pot}.")

        streets = [("Flop", board[:3]), ("Turn", board[3:4]), ("River", board[4:5])]
        for street_name, new_cards in streets:
            render_cards(street_name, new_cards)
            bet = prompt_street_bet(street_name, pot, balance, hand_number)
            if bet > 0:
                player_contrib += bet
                banker_contrib += bet  # banker always calls
                balance -= bet
                pot = player_contrib + banker_contrib
                print(f"Banker calls {bet}. Pot now ${pot}. Your balance: ${balance:,}")
            else:
                pot = player_contrib + banker_contrib
                print(f"{street_name}: check. Pot ${pot}.")

        winner, winning_hand = compare_hands(player_cards, banker_cards, board)

        print("\nShowdown:")
        render_cards("Board", board)
        render_cards("Player", player_cards)
        render_cards("Banker", banker_cards)
        print(f"Winner: {winner.capitalize()} with {winning_hand}")

        if winner == "tie":
            balance += player_contrib
            print(f"Tie. Your bets are returned. Balance: ${balance:,}")
        elif winner == "player":
            balance += player_contrib + banker_contrib
            print(f"You win pot ${player_contrib + banker_contrib}! Balance: ${balance:,}")
        else:
            print(f"You lose your bets (${player_contrib}). Balance: ${balance:,}")

        hand_number += 1

    if balance >= TARGET_BANKROLL:
        print(f"Congratulations! You reached ${balance:,} and beat the target.")
    else:
        print("Bankroll depleted. Better luck next time.")


if __name__ == "__main__":
    main()
