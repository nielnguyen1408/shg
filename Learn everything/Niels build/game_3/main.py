import json
import os
import random
import sys
from typing import List, Optional, Tuple

from banker import banker_folds
from config import (
    ANTE_BIG,
    ANTE_INCREASE_INTERVAL,
    ANTE_SMALL,
    GAME_TITLE,
    MAX_POT_MULTIPLIER,
    RANKS,
    SAVE_FILE,
    START_BANKROLL,
    SUITS,
    TARGET_BANKROLL,
)
from poker_eval import compare_hands


class PlayerQuit(Exception):
    """Raised when the player chooses to quit mid-hand."""


class PlayerFold(Exception):
    """Raised when the player chooses to fold."""


def build_deck() -> List[str]:
    return [r + s for r in RANKS for s in SUITS]


def render_cards(label: str, cards: List[str]):
    print(f"{label}: {' '.join(cards)}")


def save_game(
    balance: int, hand_number: int, pending_hand: Optional[dict] = None, silent: bool = False
) -> None:
    data = {"balance": balance, "hand_number": hand_number}
    if pending_hand is not None:
        data["pending_hand"] = pending_hand
    elif "pending_hand" in data:
        data.pop("pending_hand", None)
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)
    if not silent:
        print(f"Game saved to {SAVE_FILE}.")


def load_game() -> Optional[Tuple[int, int, Optional[dict]]]:
    if not os.path.exists(SAVE_FILE):
        return None
    while True:
        choice = input(f"Found {SAVE_FILE}. Load it? [Enter=yes / n=no / r=reset]: ").strip().lower()
        if choice in {"", "y", "yes"}:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            balance = int(data.get("balance", START_BANKROLL))
            hand_number = int(data.get("hand_number", 1))
            pending_hand = data.get("pending_hand")
            print(f"Loaded game: balance ${balance:,}, starting at hand {hand_number}.")
            return balance, hand_number, pending_hand
        if choice in {"r", "reset"}:
            os.remove(SAVE_FILE)
            print("Save reset. Starting new game.")
            return None
        if choice in {"n", "no"}:
            return None
        print("Please enter y, n, or r.")


def prompt_street_bet(
    street: str,
    pot: int,
    balance: int,
    hand_number: int,
    preflop: bool = False,
    to_call: int = 0,
) -> int:
    call_amount = min(to_call, balance) if (preflop and to_call > 0) else 0
    if preflop:
        max_bet = balance  # you can add up to your remaining balance
        if call_amount > 0:
            if call_amount < max_bet:
                bet_range_text = f"{call_amount}=call/c, {call_amount + 1}-{max_bet}=raise"
            else:
                bet_range_text = f"{call_amount}=call/c (all-in)"
        else:
            bet_range_text = f"0=check/c, 1-{max_bet}=bet"
    else:
        max_bet = min(balance, max(MAX_POT_MULTIPLIER * pot, 1))
        bet_range_text = f"0=check, 1-{max_bet}"
    while True:
        extra_text = ""
        if call_amount > 0:
            extra_text = f" | To call: ${call_amount}"
        raw = input(
            f"{street} pot ${pot}{extra_text}: Enter bet ({bet_range_text}, f=fold, or q to save & quit): "
        ).strip().lower()
        if raw in {"q", "quit"}:
            raise PlayerQuit
        if raw in {"f", "fold"}:
            raise PlayerFold
        if raw in {"c", "call"}:
            if call_amount > 0:
                return call_amount
            return 0
        if raw == "" or raw == "0":
            if call_amount > 0:
                print(f"You must enter at least {call_amount} to call.")
                continue
            return 0
        if not raw.isdigit():
            print("Please enter a number.")
            continue
        amount = int(raw)
        min_allowed = call_amount if call_amount > 0 else 1
        if min_allowed <= amount <= max_bet:
            return amount
        if call_amount > 0 and amount < min_allowed:
            print(f"Minimum to call is {min_allowed}.")
            continue
        print(f"Bet must be between {min_allowed} and {max_bet}.")


def handle_player_quit(balance: int, hand_number: int, hand_state: dict) -> None:
    """Save the current hand state so it can be resumed later."""
    print("\nSaving current hand and exiting. You'll resume from this spot next time.")
    save_game(balance, hand_number, pending_hand=hand_state)
    print("Saved. Exiting game.")
    sys.exit(0)


def handle_player_fold(player_contrib: int, banker_contrib: int, banker_cards: List[str]) -> None:
    """Resolve a player fold."""
    pot = player_contrib + banker_contrib
    print(f"\nYou fold. Banker wins pot ${pot}.")
    render_cards("Banker", banker_cards)


def main():
    print(GAME_TITLE)
    print(f"Start bankroll: ${START_BANKROLL:,} | Goal: ${TARGET_BANKROLL:,}")
    loaded = load_game()
    if loaded:
        balance, hand_number, pending_hand = loaded
    else:
        balance = START_BANKROLL
        hand_number = 1
        pending_hand = None

    while 0 < balance < TARGET_BANKROLL:
        hand_ended_early = False
        player_folded = False

        resuming = pending_hand is not None and pending_hand.get("hand_number") == hand_number
        if resuming:
            hand_state = pending_hand
            pending_hand = None
            player_cards = hand_state["player_cards"]
            banker_cards = hand_state["banker_cards"]
            board = hand_state["board"]
            player_contrib = hand_state["player_contrib"]
            banker_contrib = hand_state["banker_contrib"]
            player_role = hand_state["player_role"]
            current_small = hand_state["current_small"]
            current_big = hand_state["current_big"]
            stage = hand_state.get("stage", "preflop")
            pot = player_contrib + banker_contrib
            print(f"\n--- Hand {hand_number} (resumed) ---")
            # clear pending hand from save file now that it's loaded
            save_game(balance, hand_number, pending_hand=None, silent=True)
        else:
            print(f"\n--- Hand {hand_number} ---")
            deck = build_deck()
            random.shuffle(deck)
            player_cards = deck[:2]
            banker_cards = deck[2:4]
            board = deck[4:9]
            pot = 0
            player_contrib = 0
            banker_contrib = 0
            stage = "preflop"

            level = (hand_number - 1) // ANTE_INCREASE_INTERVAL
            ante_multiplier = 2 ** level
            current_small = ANTE_SMALL * ante_multiplier
            current_big = ANTE_BIG * ante_multiplier
            player_posts_small = hand_number % 2 == 1
            if player_posts_small:
                player_ante = current_small
                banker_ante = current_big
                player_role = "SB"
            else:
                player_ante = current_big
                banker_ante = current_small
                player_role = "BB"

            player_ante_paid = min(player_ante, balance)
            player_contrib += player_ante_paid
            banker_contrib += banker_ante
            balance -= player_ante_paid
            pot = player_contrib + banker_contrib
            if player_ante_paid < player_ante:
                print("Player is all-in from posting the blind.")

            hand_state = {
                "hand_number": hand_number,
                "player_cards": player_cards,
                "banker_cards": banker_cards,
                "board": board,
                "player_contrib": player_contrib,
                "banker_contrib": banker_contrib,
                "player_role": player_role,
                "current_small": current_small,
                "current_big": current_big,
                "stage": stage,
            }

        print(f"Balance ${balance:,} | Blinds ${current_small}/${current_big}")
        print(f"Hero: {player_role}")
        render_cards("Player", player_cards)

        # Pre-Flop betting (no community cards yet)
        if stage == "preflop":
            if player_role == "BB":
                banker_to_call = max(player_contrib - banker_contrib, 0)
                if banker_to_call > 0:
                    pot_before = pot
                    if banker_folds(banker_to_call, pot_before, banker_cards, []):
                        pot = player_contrib + banker_contrib
                        balance += pot
                        print(
                            f"Banker declines to complete the blind and folds. "
                            f"You win pot ${pot}. Balance: ${balance:,}"
                        )
                        render_cards("Banker", banker_cards)
                        pending_hand = None
                        hand_number += 1
                        continue
                    banker_contrib += banker_to_call
                    hand_state["banker_contrib"] = banker_contrib
                    pot = player_contrib + banker_contrib
                    print(f"Banker completes small blind (adds ${banker_to_call}). Pot ${pot}.")
            to_call = max(banker_contrib - player_contrib, 0)
            try:
                bet = prompt_street_bet("Pre-Flop", pot, balance, hand_number, preflop=True, to_call=to_call)
            except PlayerFold:
                handle_player_fold(player_contrib, banker_contrib, banker_cards)
                hand_number += 1
                pending_hand = None
                continue
            except PlayerQuit:
                handle_player_quit(balance, hand_number, hand_state)
            if bet > 0:
                pot_before = pot
                player_contrib += bet
                balance -= bet
                hand_state["player_contrib"] = player_contrib
                is_raise = bet > to_call
                if is_raise and banker_folds(bet, pot_before, banker_cards, []):
                    pot = player_contrib + banker_contrib
                    balance += pot
                    print(
                        f"Banker folds to your pre-flop bet of ${bet}. "
                        f"You win pot ${pot}. Balance: ${balance:,}"
                    )
                    render_cards("Banker", banker_cards)
                    hand_number += 1
                    pending_hand = None
                    continue
                banker_needed = max(player_contrib - banker_contrib, 0)
                if banker_needed > 0:
                    banker_contrib += banker_needed
                    action_text = f"Banker calls ${banker_needed}."
                else:
                    action_text = "Banker checks."
                hand_state["banker_contrib"] = banker_contrib
                pot = player_contrib + banker_contrib
                print(f"{action_text} Pot now ${pot}. Your balance: ${balance:,}")
            else:
                pot = player_contrib + banker_contrib
                print(f"Pre-Flop: check. Pot ${pot}.")
            stage = "flop"
            hand_state["stage"] = "flop"

        street_titles = ["Flop", "Turn", "River"]
        stage_labels = ["flop", "turn", "river"]
        start_idx = 0
        if hand_state["stage"] in stage_labels:
            start_idx = stage_labels.index(hand_state["stage"])
        for idx in range(start_idx, len(street_titles)):
            stage_label = stage_labels[idx]
            street_name = street_titles[idx]
            hand_state["stage"] = stage_label

            if street_name == "Flop":
                visible_board = board[:3]
            elif street_name == "Turn":
                visible_board = board[:4]
            else:  # River
                visible_board = board[:5]
            print(f"\n-- {street_name} --")
            print(f"Pot ${pot}")
            render_cards("Board", visible_board)
            render_cards("Player", player_cards)
            try:
                bet = prompt_street_bet(street_name, pot, balance, hand_number)
            except PlayerFold:
                handle_player_fold(player_contrib, banker_contrib, banker_cards)
                player_folded = True
                break
            except PlayerQuit:
                handle_player_quit(balance, hand_number, hand_state)
            if bet > 0:
                pot_before = pot
                player_contrib += bet
                balance -= bet
                hand_state["player_contrib"] = player_contrib
                if banker_folds(bet, pot_before, banker_cards, visible_board):
                    pot = player_contrib + banker_contrib
                    balance += pot
                    print(
                        f"Banker folds to your {street_name} bet of ${bet}. "
                        f"You win pot ${pot}. Balance: ${balance:,}"
                    )
                    render_cards("Banker", banker_cards)
                    hand_ended_early = True
                    break
                banker_needed = max(player_contrib - banker_contrib, 0)
                if banker_needed > 0:
                    banker_contrib += banker_needed
                    action_text = f"Banker calls ${banker_needed}."
                else:
                    action_text = "Banker already covered the bet."
                hand_state["banker_contrib"] = banker_contrib
                pot = player_contrib + banker_contrib
                print(f"{action_text} Pot now ${pot}. Your balance: ${balance:,}")
            else:
                pot = player_contrib + banker_contrib
                print(f"{street_name}: check. Pot ${pot}.")

        if hand_ended_early:
            pending_hand = None
            hand_number += 1
            continue
        if player_folded:
            pending_hand = None
            hand_number += 1
            continue

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
