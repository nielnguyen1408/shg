## Project Overview

- One-player heads-up no-limit Texas Hold'em simulation (`main.py`) with a deterministic banker AI (`banker.py`) and hand evaluator (`poker_eval.py`).
- Game state saved to `save.json`; quitting mid-hand stores full hand snapshot (`pending_hand`) so play can resume seamlessly.
- Configurable constants live in `config.py` (stack goals, blind structure, fold-equity multipliers, etc.).

## Key Logic

### Banker AI (`banker.py`)
- Uses fold equity `FE = bet / (bet + pot)` scaled by:
  - Preflop heuristics: counts broadway cards (A–T), suitedness, and connectivity. Parameters: `PREFLOP_*` multipliers. SB completion (when player is BB) also respects FE to allow folding trash hands.
  - Postflop hand strength via `best_hand` coupled with pair classification (`pair_category`). Distinguishes top/mid/bottom pairs per street (flop 3 ranks, turn 4, river 5). Pocket pairs treated as over/mid/under accordingly.
  - Draw detection: `has_flush_draw`, `has_straight_draw` (currently 4-card draws). Multipliers set by `DRAW_FOLD_MULTIPLIER` and flop pair multipliers.
  - River weak-hand multiplier (`RIVER_WEAK_HAND_MULTIPLIER`) increases fold frequency for high-card / one-pair holdings at showdown.

### Game Flow (`main.py`)
- `prompt_street_bet` handles CLI input; supports shortcuts: `c` for call/check, `f` for fold, `q` to save & quit (creates pending hand).
- Preflop blinds auto-post; roles alternate each hand. When player is BB, banker must complete SB but can fold using FE if cards are trash.
- Each street prints minimal info: balance/blinds, hero cards preflop, board+pot with `-- Street --` separators, and reprints hero hand for reference.
- Folding or banker folding reveals banker cards immediately for transparency.
- Uses `hand_state` dict to support resuming after quit; includes deck slice, board, contributions, stage, and blind info.

### Evaluator (`poker_eval.py`)
- Standard 7-card evaluator returning rank tier (0–8) plus kickers.
- `compare_hands` used at showdown; also leveraged by banker AI for strength assessment.

## Considerations & Open Items
- Banker still relies on heuristic multipliers; noteworthy tweaks discussed:
  - Strong draws (beyond 4-card flush/straight) or combo draws not yet covered.
  - Potential to further differentiate gutshots/open-enders and adjust FE accordingly.
  - Pot-odds already baked into FE formula; additional logic is purely situational strength adjustments.
  - Future GUI can reuse current modules; only CLI I/O needs abstraction.
- Testing often done manually; no automated tests yet.
