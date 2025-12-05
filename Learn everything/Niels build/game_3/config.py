from typing import List

# Card configuration
RANKS: List[str] = "2 3 4 5 6 7 8 9 T J Q K A".split()
SUITS: List[str] = ["s", "h", "d", "c"]  # spades, hearts, diamonds, clubs

# Bankroll and game targets
START_BANKROLL: int = 1_000
TARGET_BANKROLL: int = 100_000_000

# Save/load configuration
SAVE_FILE: str = "save.json"

# Betting configuration
# Maximum bet on post-flop streets is min(balance, MAX_POT_MULTIPLIER * pot)
MAX_POT_MULTIPLIER: int = 2

# Banker fold-equity configuration
# Base formula: FE = bet / (bet + pot_effective)
# You can scale it down or up with FOLD_EQUITY_SCALE, e.g. 0.8 for tighter banker.
FOLD_EQUITY_SCALE: float = 1.0
DRAW_FOLD_MULTIPLIER: float = 0.5  # banker hangs on more with strong draws
FLOP_TOP_PAIR_MULTIPLIER: float = 0.6
FLOP_MID_PAIR_MULTIPLIER: float = 0.8
FLOP_BOTTOM_PAIR_MULTIPLIER: float = 0.95
RIVER_WEAK_HAND_MULTIPLIER: float = 1.3

# Pre-flop fold-equity tuning
# Banker folds more with trash hands (no high cards, offsuit, unconnected)
# and folds less as the hand has high cards / is suited / is connected.
PREFLOP_BASE_MULTIPLIER: float = 1.0
PREFLOP_FEATURE_STEP: float = 0.3
PREFLOP_MIN_MULTIPLIER: float = 0.3
PREFLOP_MAX_MULTIPLIER: float = 1.5

# Game text
GAME_TITLE: str = "Poker one-player (you vs. banker with fold equity)"

# Ante / blinds configuration
ANTE_SMALL: int = 5
ANTE_BIG: int = 10
ANTE_INCREASE_INTERVAL: int = 100  # hands before doubling antes
