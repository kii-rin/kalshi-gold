# ES-HyperNEAT gold brains: results (Nov 25, 2026)

Trained with [kii-rin/eshyperneat-trainer](https://github.com/kii-rin/eshyperneat-trainer) using `train_neat.py`, on every 15-minute gold market from Jul 31 to Nov 25 (7,569 with full minute data).

- **When the brain decides:** once per market, 2 minutes before close: buy YES, buy NO, or skip. 1 contract per trade, Kalshi taker fee included.
- **What it sees:** the price, how the price moved over the last 1/3/8/12 minutes, the recent price range, the spread, recent volume, and the time of day.
- **Training goal:** steady profit per trade (t-stat), not total profit.
- **Data split by time:** train Jul 31–Oct 8, validation Oct 8–Nov 2 (picks the generation to keep), test Nov 2–25 (never used for any choice).

| Seed | Kept gen | Train | Validation | **Test (honest)** | Test trades | Test win rate |
|--:|--:|--:|--:|--:|--:|--:|
| 1 | 0 | -$17.52 | -$8.30 | **-$7.01** | 750 | 45% |
| 2 | 64 | +$4.13 | +$0.27 | **-$2.88** | 430 | 41% |
| 3 | 32 | +$1.01 | +$0.28 | **+$3.79** | 188 | 66% |
| 4 | 0 | -$15.80 | +$5.01 | **-$18.72** | 833 | 48% |
| 5 | 87 | +$3.36 | +$0.83 | **-$1.09** | 15 | 73% |
| **Rule: favorite 90-95c at 2 min** | | -$4.10 | +$2.58 | **+$1.47** | 191 | 94% |

**Verdict: no edge found, so no brain is used for trading.**

- **Test results:** 4 of 5 brains lost money on the test months (-$25.91 combined over 2,216 trades).
- **Seed 3:** its +$3.79 is not trustworthy. It was the best of 5 tries, it was flat on train and validation, and its test result (t = 1.0) is well within luck.
- **What the brains did:** they mostly learned to trade mid-priced markets, around 40-60% chances. Those are coin flips where the fee is the only certain thing.
- **Why it found nothing:** the brain only saw Kalshi's own prices and volume, which the market has already priced in.

An edge would need information Kalshi's price doesn't have yet. The most likely candidate is the live gold price compared with the market's target, from a feed faster than the market updates.

Re-run: `python train_neat.py --data data/KXGOLD15M-full.json.gz --neat ../eshyperneat-trainer --gens 120 --seed 1`
