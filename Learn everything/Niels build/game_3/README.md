# Poker one-player

Simple command-line poker where you bet on either the Player or the Banker.

## Objective
- Start with $1,000 and try to reach $100,000,000.
- Lose when your bankroll hits $0.

## Rules (Version 2)
- Standard Texas Hold'em ranking is used.
- You see only your own 2 hole cards. Banker's hole cards stay hidden until showdown.
- Betting starts pre-flop (hole cards only), then repeats on flop, turn, and river. Banker auto-calls every bet.
- Street bet cap is 2× the current pot. Checks are allowed. Pre-flop has no minimum bet; with an empty pot you can check or bet any amount up to your balance.
- If you win the showdown, you take the pot (your bets + banker calls). If you lose, you lose your bets. Ties return your bets.
- Card notation uses lowercase suits for readability (e.g., `Jc`, `Ah`).

## Save / Load
- A save file `save.json` is kept in this folder with your bankroll and next hand number.
- If `save.json` exists, pressing Enter will load it by default. Type `n` to skip loading, or `r`/`reset` to clear the save.
- At any betting prompt you can type `q`/`quit` to save and exit; otherwise play continues automatically into the next hand.

## How to run
```bash
python main.py
```

Follow the prompts to place bets and choose a side for each hand.
