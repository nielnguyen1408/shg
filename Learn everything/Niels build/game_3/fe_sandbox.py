"""
Quick sandbox to probe banker fold-equity logic without full play sessions.

Examples:
  python fe_sandbox.py --banker "7s 9s" --board "Ad 6c 4d 4h Kh" --bet 40 --pot 60
  python fe_sandbox.py --banker "Ah Kd" --bet 15 --pot 15  # pre-flop sized
  python fe_sandbox.py --preset --fe-only  # use the preset scenario below and just print FE
"""

import argparse
import random
from typing import List

from banker import banker_folds


PRESET_SCENARIO = {
    "banker": ["2s", "9s"],
    "board": ["Ad", "2c", "4d", "4h", "Kh"],
    "bet": 40,
    "pot": 60,
}


def parse_cards(raw: str, expected_min: int, expected_max: int) -> List[str]:
    cards = [c.strip() for c in raw.replace(",", " ").split() if c.strip()]
    if not (expected_min <= len(cards) <= expected_max):
        raise argparse.ArgumentTypeError(f"Expected between {expected_min} and {expected_max} cards, got {len(cards)}.")
    for card in cards:
        if len(card) != 2:
            raise argparse.ArgumentTypeError(f"Card '{card}' must be rank+suit (e.g., As, Td).")
    return cards


def main() -> None:
    parser = argparse.ArgumentParser(description="Fold-equity sandbox for banker_folds().")
    parser.add_argument("--preset", action="store_true", help="Use the preset scenario defined in this file.")
    parser.add_argument("--banker", type=lambda s: parse_cards(s, 2, 2), help="Banker hand, 2 cards.")
    parser.add_argument(
        "--board", default="", type=lambda s: parse_cards(s, 0, 5), help="Board cards (0-5 allowed)."
    )
    parser.add_argument("--bet", type=int, default=50, help="Bet size hero makes into banker.")
    parser.add_argument("--pot", type=int, default=100, help="Current pot before bet.")
    parser.add_argument(
        "--runs", type=int, default=1, help="Number of random trials to estimate fold frequency (uses FE internally)."
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Optional RNG seed for reproducible fold/call sampling over runs."
    )
    parser.add_argument(
        "--reuse-fe",
        action="store_true",
        help="Compute FE once then sample folds, for speed when runs is large (default is per-run FE).",
    )
    parser.add_argument("--fe-only", action="store_true", help="Just compute FE once and print it.")
    args = parser.parse_args()

    if args.preset:
        banker_cards = PRESET_SCENARIO["banker"]
        board_cards = PRESET_SCENARIO["board"]
        bet = PRESET_SCENARIO["bet"]
        pot = PRESET_SCENARIO["pot"]
    else:
        if args.banker is None:
            parser.error("Either provide --banker or use --preset.")
        banker_cards = args.banker
        board_cards = args.board
        bet = args.bet
        pot = args.pot

    if args.seed is not None:
        random.seed(args.seed)

    if args.fe_only:
        _, fe = banker_folds(bet, pot, banker_cards, board_cards)
        print(f"Banker hand: {' '.join(banker_cards)}")
        print(f"Board: {' '.join(board_cards) if board_cards else '(none)'}")
        print(f"Bet: {bet} | Pot: {pot}")
        print(f"Fold Equity: {fe:.2f}")
        return

    runs = max(1, args.runs)
    fold_decisions = []
    fe_values = []

    if args.reuse_fe and runs > 1:
        # Compute FE once, then sample folds using the same FE (faster for large runs).
        folded, fe = banker_folds(bet, pot, banker_cards, board_cards)
        fe_values = [fe] * runs
        fold_decisions = [random.random() < fe for _ in range(runs)]
        # Use the first sampled fold as "last run" for reporting consistency.
        folded = fold_decisions[-1]
    else:
        for _ in range(runs):
            folded, fe = banker_folds(bet, pot, banker_cards, board_cards)
            fold_decisions.append(folded)
            fe_values.append(fe)

    avg_fe = sum(fe_values) / len(fe_values)
    fold_rate = sum(1 for f in fold_decisions if f) / len(fold_decisions)

    print(f"Banker hand: {' '.join(banker_cards)}")
    print(f"Board: {' '.join(board_cards) if board_cards else '(none)'}")
    print(f"Bet: {bet} | Pot: {pot}")
    print(f"Fold Equity (last run): {fe_values[-1]:.2f} | Folded: {fold_decisions[-1]}")
    if args.runs > 1:
        print(f"Avg FE over {args.runs} runs: {avg_fe:.2f} | Empirical fold rate: {fold_rate:.2f}")


if __name__ == "__main__":
    main()


# Chạy 1 lần:
# python fe_sandbox.py --preset --fe-only

# Overide: Bỏ --preset và truyền --banker ... --board ... --bet ... --pot ...