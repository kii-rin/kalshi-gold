# Gold strategy research (Nov 27, 2026)

## Conclusion

**With an accurate gold price, none of the 90 strategies beat Kalshi's gold markets after fees.**

**Data:** 7,798 gold markets (Jul 31 – Nov 26), with Kalshi's price for each minute of the last 15. Every strategy was fitted on Aug–Sep, chosen on October, and tested once on November.

**Which gold price is accurate:** OKX XAUT matches Kalshi's settlement price (Pyth gold) much better than Coinbase PAXG, the price the live bot uses.

| Gold price | Correlation with Pyth's 15-minute moves | Typical gap |
|---|--:|--:|
| XAUT (OKX) | 0.982 | 2.7 bp |
| PAXG (Coinbase) | 0.936 | 5.0 bp |

- **With XAUT:** only 1 of 90 strategies was positive in both training and validation (+0.4¢ per trade), and it lost on November (−1.95¢ per trade). Every family's November pick lost money: the live rule, the fair-value option model with 5 ways to measure speed, the fair value plus momentum, mean-reversion or RSI, fading Kalshi jumps, Kalshi-only calibration tables, and logistic regression.
- **With PAXG:** some strategies made money, including the live rule at +1–4¢ per trade. But the more accurate gold price shows no edge, and the live rule was the best of about 120 versions tried earlier. So the PAXG profit is most likely luck from trying many versions, not a real edge.
- **Timestamps:** these were checked. PAXG and XAUT line up with no shift, so the results don't come from peeking ahead.

**Why it fails:** Kalshi's gold prices already include gold's distance from the target and its speed, priced against the real Pyth feed. Whenever a model disagreed with Kalshi, Kalshi was usually right, and the taker fee (about 1–2¢) removes what's left.

**What minute data can't test:** reacting within seconds to gold moves before Kalshi's price updates, and posting orders instead of taking them (maker). Both need second-by-second data and a fast setup, and other bots already compete there.

## Gold price from XAUT (OKX)

_7798 markets; gold price available for 100% of market-minutes. Train Aug 1-Sep 30 (fit), validation Oct (choose), **test Nov 1-26 (looked at once)**. 1 contract per trade, taker fee included; '+1c slip' assumes every fill is 1c worse._

### One pick per family (chosen on validation), then the test

| Family | Chosen settings | Train: trades, per trade | Valid: trades, per trade | **Test: trades** | **win / need** | **per trade (95% range)** | **profit** | test +1c slip | worst dip |
|---|---|---|---|--:|--:|--:|--:|--:|--:|
| A. Live rule (band + distance) | 70-95c, z>=1.5 | 890, +0.40c | 379, +0.35c | 246 | 89.8% / 91.8% | -1.95c (-6.0 to +1.5) | **-$4.79** | -$7.25 | $8.94 |
| B. Fair value (option model) | vol=ewma (scale 0.8), last 5 min, edge>=2c | 3534, -2.32c | 1621, -0.82c | 1301 | 26.8% / 28.9% | -2.03c (-4.0 to -0.1) | **-$26.41** | -$39.42 | $28.49 |
| C. Fair value + trend | momentum: + last 5 min trend, last 5 min, edge>=4c | 3355, -1.45c | 1527, -1.78c | 1202 | 40.3% / 44.0% | -3.71c (-5.9 to -1.5) | **-$44.64** | -$56.66 | $47.77 |
| D. Fade Kalshi overreaction | jump>=25c in 1 min, gold z<=0.7 | 609, -2.54c | 324, +0.36c | 281 | 32.4% / 37.0% | -4.62c (-9.5 to +0.7) | **-$12.98** | -$15.79 | $15.40 |
| E. Calibration table (Kalshi prices only) | edge>=4c, last 3 min | 308, +2.45c | 146, -1.01c | 115 | 56.5% / 59.4% | -2.85c (-10.0 to +4.8) | **-$3.28** | -$4.43 | $8.19 |
| F. Logistic regression (all features) | last 5 min, edge>=2c | 210, +3.24c | 84, -7.74c | 34 | 52.9% / 59.9% | -6.91c (-22.0 to +9.8) | **-$2.35** | -$2.69 | $4.49 |

### Every strategy on train and validation (test hidden)

| Family | Settings | Train trades | Train per trade | Train profit | Valid trades | Valid per trade | Valid profit |
|---|---|--:|--:|--:|--:|--:|--:|
| A. Live rule (band + distance) | 70-95c, z>=1 | 1480 | -1.41c | -$20.94 | 639 | +0.19c | +$1.19 |
| A. Live rule (band + distance) | 70-95c, z>=1.5 | 890 | +0.40c | +$3.56 | 379 | +0.35c | +$1.31 |
| A. Live rule (band + distance) | 80-90c, z>=1 | 667 | -0.72c | -$4.82 | 303 | +0.32c | +$0.97 |
| A. Live rule (band + distance) | 80-90c, z>=1.5 | 317 | +0.53c | +$1.68 | 145 | -0.12c | -$0.18 |
| B. Fair value (option model) | vol=rv30 (scale 0.75), last 3 min, edge>=2c | 2940 | -2.09c | -$61.39 | 1334 | -3.44c | -$45.88 |
| B. Fair value (option model) | vol=rv30 (scale 0.75), last 3 min, edge>=4c | 2616 | -2.26c | -$59.00 | 1184 | -3.33c | -$39.41 |
| B. Fair value (option model) | vol=rv30 (scale 0.75), last 3 min, edge>=6c | 2342 | -2.21c | -$51.84 | 1049 | -3.21c | -$33.71 |
| B. Fair value (option model) | vol=rv30 (scale 0.75), last 3 min, edge>=8c | 2092 | -2.31c | -$48.23 | 938 | -3.04c | -$28.47 |
| B. Fair value (option model) | vol=rv30 (scale 0.75), last 5 min, edge>=2c | 3571 | -2.26c | -$80.85 | 1653 | -1.68c | -$27.72 |
| B. Fair value (option model) | vol=rv30 (scale 0.75), last 5 min, edge>=4c | 3235 | -2.37c | -$76.58 | 1495 | -1.88c | -$28.17 |
| B. Fair value (option model) | vol=rv30 (scale 0.75), last 5 min, edge>=6c | 2927 | -2.23c | -$65.17 | 1341 | -2.15c | -$28.85 |
| B. Fair value (option model) | vol=rv30 (scale 0.75), last 5 min, edge>=8c | 2621 | -2.10c | -$55.16 | 1207 | -1.98c | -$23.87 |
| B. Fair value (option model) | vol=rv30 (scale 0.75), last 10 min, edge>=2c | 4098 | -2.71c | -$110.90 | 1900 | -2.70c | -$51.30 |
| B. Fair value (option model) | vol=rv30 (scale 0.75), last 10 min, edge>=4c | 3917 | -2.20c | -$86.13 | 1825 | -2.07c | -$37.79 |
| B. Fair value (option model) | vol=rv30 (scale 0.75), last 10 min, edge>=6c | 3646 | -2.15c | -$78.26 | 1713 | -1.38c | -$23.62 |
| B. Fair value (option model) | vol=rv30 (scale 0.75), last 10 min, edge>=8c | 3327 | -2.17c | -$72.25 | 1572 | -2.37c | -$37.21 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 3 min, edge>=2c | 3013 | -2.53c | -$76.26 | 1356 | -2.95c | -$39.96 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 3 min, edge>=4c | 2710 | -2.10c | -$56.83 | 1205 | -4.00c | -$48.25 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 3 min, edge>=6c | 2437 | -2.24c | -$54.69 | 1083 | -2.77c | -$30.05 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 3 min, edge>=8c | 2188 | -1.77c | -$38.80 | 974 | -2.53c | -$24.64 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 5 min, edge>=2c | 3588 | -2.50c | -$89.63 | 1663 | -1.29c | -$21.46 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 5 min, edge>=4c | 3267 | -2.86c | -$93.32 | 1525 | -2.03c | -$30.90 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 5 min, edge>=6c | 3001 | -2.72c | -$81.54 | 1380 | -2.14c | -$29.59 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 5 min, edge>=8c | 2712 | -2.40c | -$64.98 | 1228 | -1.84c | -$22.58 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 10 min, edge>=2c | 4098 | -2.37c | -$97.06 | 1901 | -2.60c | -$49.34 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 10 min, edge>=4c | 3922 | -2.51c | -$98.57 | 1821 | -2.61c | -$47.59 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 10 min, edge>=6c | 3693 | -2.26c | -$83.63 | 1720 | -2.22c | -$38.23 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 10 min, edge>=8c | 3378 | -1.88c | -$63.42 | 1597 | -2.26c | -$36.06 |
| B. Fair value (option model) | vol=ewma (scale 0.8), last 3 min, edge>=2c | 2885 | -2.19c | -$63.17 | 1306 | -3.56c | -$46.52 |
| B. Fair value (option model) | vol=ewma (scale 0.8), last 3 min, edge>=4c | 2540 | -2.03c | -$51.67 | 1150 | -2.93c | -$33.70 |
| B. Fair value (option model) | vol=ewma (scale 0.8), last 3 min, edge>=6c | 2266 | -2.22c | -$50.28 | 1007 | -3.47c | -$34.97 |
| B. Fair value (option model) | vol=ewma (scale 0.8), last 3 min, edge>=8c | 1995 | -1.96c | -$39.11 | 899 | -2.69c | -$24.15 |
| B. Fair value (option model) | vol=ewma (scale 0.8), last 5 min, edge>=2c | 3534 | -2.32c | -$82.06 | 1621 | -0.82c | -$13.27 |
| B. Fair value (option model) | vol=ewma (scale 0.8), last 5 min, edge>=4c | 3166 | -2.46c | -$77.75 | 1464 | -1.92c | -$28.14 |
| B. Fair value (option model) | vol=ewma (scale 0.8), last 5 min, edge>=6c | 2843 | -2.42c | -$68.85 | 1300 | -2.37c | -$30.87 |
| B. Fair value (option model) | vol=ewma (scale 0.8), last 5 min, edge>=8c | 2515 | -2.43c | -$61.12 | 1164 | -2.27c | -$26.41 |
| B. Fair value (option model) | vol=ewma (scale 0.8), last 10 min, edge>=2c | 4104 | -2.41c | -$98.87 | 1900 | -2.92c | -$55.41 |
| B. Fair value (option model) | vol=ewma (scale 0.8), last 10 min, edge>=4c | 3906 | -2.00c | -$78.01 | 1812 | -2.42c | -$43.78 |
| B. Fair value (option model) | vol=ewma (scale 0.8), last 10 min, edge>=6c | 3612 | -2.11c | -$76.15 | 1695 | -1.69c | -$28.60 |
| B. Fair value (option model) | vol=ewma (scale 0.8), last 10 min, edge>=8c | 3211 | -2.27c | -$73.00 | 1558 | -2.81c | -$43.71 |
| B. Fair value (option model) | vol=pyth (scale 0.75), last 3 min, edge>=2c | 3146 | -2.25c | -$70.81 | 1423 | -2.92c | -$41.52 |
| B. Fair value (option model) | vol=pyth (scale 0.75), last 3 min, edge>=4c | 2858 | -2.07c | -$59.22 | 1308 | -2.94c | -$38.48 |
| B. Fair value (option model) | vol=pyth (scale 0.75), last 3 min, edge>=6c | 2611 | -2.66c | -$69.46 | 1204 | -2.45c | -$29.53 |
| B. Fair value (option model) | vol=pyth (scale 0.75), last 3 min, edge>=8c | 2389 | -2.22c | -$52.99 | 1083 | -2.04c | -$22.09 |
| B. Fair value (option model) | vol=pyth (scale 0.75), last 5 min, edge>=2c | 3692 | -2.39c | -$88.37 | 1719 | -2.31c | -$39.79 |
| B. Fair value (option model) | vol=pyth (scale 0.75), last 5 min, edge>=4c | 3415 | -2.65c | -$90.33 | 1611 | -2.16c | -$34.84 |
| B. Fair value (option model) | vol=pyth (scale 0.75), last 5 min, edge>=6c | 3160 | -2.89c | -$91.26 | 1494 | -2.10c | -$31.41 |
| B. Fair value (option model) | vol=pyth (scale 0.75), last 5 min, edge>=8c | 2905 | -2.86c | -$83.14 | 1363 | -2.17c | -$29.57 |
| B. Fair value (option model) | vol=pyth (scale 0.75), last 10 min, edge>=2c | 4104 | -3.02c | -$123.98 | 1914 | -2.10c | -$40.16 |
| B. Fair value (option model) | vol=pyth (scale 0.75), last 10 min, edge>=4c | 3928 | -3.15c | -$123.54 | 1848 | -1.64c | -$30.39 |
| B. Fair value (option model) | vol=pyth (scale 0.75), last 10 min, edge>=6c | 3737 | -3.37c | -$125.99 | 1777 | -1.23c | -$21.93 |
| B. Fair value (option model) | vol=pyth (scale 0.75), last 10 min, edge>=8c | 3466 | -3.65c | -$126.34 | 1658 | -2.36c | -$39.12 |
| B. Fair value (option model) | vol=blend (scale 0.85), last 3 min, edge>=2c | 2941 | -2.18c | -$64.11 | 1317 | -2.75c | -$36.19 |
| B. Fair value (option model) | vol=blend (scale 0.85), last 3 min, edge>=4c | 2598 | -2.08c | -$54.15 | 1192 | -3.10c | -$36.99 |
| B. Fair value (option model) | vol=blend (scale 0.85), last 3 min, edge>=6c | 2321 | -2.55c | -$59.29 | 1068 | -2.59c | -$27.66 |
| B. Fair value (option model) | vol=blend (scale 0.85), last 3 min, edge>=8c | 2061 | -2.49c | -$51.40 | 962 | -2.63c | -$25.33 |
| B. Fair value (option model) | vol=blend (scale 0.85), last 5 min, edge>=2c | 3514 | -2.47c | -$86.67 | 1636 | -1.27c | -$20.83 |
| B. Fair value (option model) | vol=blend (scale 0.85), last 5 min, edge>=4c | 3193 | -2.56c | -$81.88 | 1501 | -1.48c | -$22.24 |
| B. Fair value (option model) | vol=blend (scale 0.85), last 5 min, edge>=6c | 2858 | -2.96c | -$84.73 | 1353 | -1.84c | -$24.89 |
| B. Fair value (option model) | vol=blend (scale 0.85), last 5 min, edge>=8c | 2555 | -2.51c | -$64.14 | 1209 | -2.15c | -$25.96 |
| B. Fair value (option model) | vol=blend (scale 0.85), last 10 min, edge>=2c | 4050 | -2.10c | -$85.02 | 1883 | -2.15c | -$40.48 |
| B. Fair value (option model) | vol=blend (scale 0.85), last 10 min, edge>=4c | 3841 | -2.28c | -$87.56 | 1804 | -2.11c | -$38.00 |
| B. Fair value (option model) | vol=blend (scale 0.85), last 10 min, edge>=6c | 3533 | -2.45c | -$86.59 | 1697 | -1.38c | -$23.47 |
| B. Fair value (option model) | vol=blend (scale 0.85), last 10 min, edge>=8c | 3197 | -1.77c | -$56.58 | 1574 | -1.63c | -$25.62 |
| C. Fair value + trend | momentum: + last 5 min trend, last 5 min, edge>=4c | 3355 | -1.45c | -$48.50 | 1527 | -1.78c | -$27.24 |
| C. Fair value + trend | momentum: + last 5 min trend, last 5 min, edge>=6c | 3112 | -1.49c | -$46.28 | 1416 | -2.28c | -$32.33 |
| C. Fair value + trend | mean reversion: - last 5 min trend, last 5 min, edge>=4c | 3877 | -3.19c | -$123.75 | 1775 | -2.24c | -$39.71 |
| C. Fair value + trend | mean reversion: - last 5 min trend, last 5 min, edge>=6c | 3723 | -3.17c | -$118.00 | 1716 | -3.03c | -$52.06 |
| C. Fair value + trend | RSI filter, last 5 min, edge>=4c | 3058 | -2.31c | -$70.59 | 1417 | -1.86c | -$26.30 |
| C. Fair value + trend | RSI filter, last 5 min, edge>=6c | 2772 | -2.03c | -$56.38 | 1284 | -2.08c | -$26.75 |
| D. Fade Kalshi overreaction | jump>=10c in 1 min, gold z<=0.3 | 851 | -3.84c | -$32.68 | 427 | -3.67c | -$15.68 |
| D. Fade Kalshi overreaction | jump>=10c in 1 min, gold z<=0.7 | 1464 | -3.48c | -$50.98 | 706 | -1.96c | -$13.81 |
| D. Fade Kalshi overreaction | jump>=15c in 1 min, gold z<=0.3 | 627 | -3.00c | -$18.81 | 326 | -3.97c | -$12.94 |
| D. Fade Kalshi overreaction | jump>=15c in 1 min, gold z<=0.7 | 1147 | -3.86c | -$44.24 | 580 | -1.44c | -$8.37 |
| D. Fade Kalshi overreaction | jump>=25c in 1 min, gold z<=0.3 | 308 | -4.61c | -$14.20 | 172 | -0.99c | -$1.70 |
| D. Fade Kalshi overreaction | jump>=25c in 1 min, gold z<=0.7 | 609 | -2.54c | -$15.49 | 324 | +0.36c | +$1.15 |
| E. Calibration table (Kalshi prices only) | edge>=2c, last 3 min | 960 | +0.82c | +$7.88 | 480 | -1.00c | -$4.81 |
| E. Calibration table (Kalshi prices only) | edge>=2c, last 14 min | 3863 | +2.61c | +$100.96 | 1816 | -2.33c | -$42.38 |
| E. Calibration table (Kalshi prices only) | edge>=4c, last 3 min | 308 | +2.45c | +$7.55 | 146 | -1.01c | -$1.47 |
| E. Calibration table (Kalshi prices only) | edge>=4c, last 14 min | 2642 | +4.66c | +$123.11 | 1299 | -2.80c | -$36.42 |
| E. Calibration table (Kalshi prices only) | edge>=6c, last 3 min | 77 | +7.16c | +$5.51 | 31 | +5.27c | +$1.63 |
| E. Calibration table (Kalshi prices only) | edge>=6c, last 14 min | 1283 | +6.30c | +$80.84 | 649 | -2.28c | -$14.82 |
| F. Logistic regression (all features) | last 3 min, edge>=2c | 158 | +4.00c | +$6.33 | 63 | -9.75c | -$6.14 |
| F. Logistic regression (all features) | last 5 min, edge>=2c | 210 | +3.24c | +$6.80 | 84 | -7.74c | -$6.50 |
| F. Logistic regression (all features) | last 3 min, edge>=4c | 56 | +1.35c | +$0.76 | 13 | -9.85c | -$1.28 |
| F. Logistic regression (all features) | last 5 min, edge>=4c | 61 | +4.98c | +$3.04 | 14 | -14.79c | -$2.07 |
| F. Logistic regression (all features) | last 3 min, edge>=6c | 26 | +8.35c | +$2.17 | 2 | +0.50c | +$0.01 |
| F. Logistic regression (all features) | last 5 min, edge>=6c | 31 | +10.38c | +$3.22 | 3 | -21.33c | -$0.64 |
| F. Logistic regression (all features) | last 3 min, edge>=8c | 15 | -1.20c | -$0.18 | 0 | +0.00c | +$0.00 |
| F. Logistic regression (all features) | last 5 min, edge>=8c | 18 | +2.63c | +$0.47 | 0 | +0.00c | +$0.00 |

## Gold price from PAXG (Coinbase)

_7798 markets; gold price available for 56% of market-minutes. Train Aug 1-Sep 30 (fit), validation Oct (choose), **test Nov 1-26 (looked at once)**. 1 contract per trade, taker fee included; '+1c slip' assumes every fill is 1c worse._

### One pick per family (chosen on validation), then the test

| Family | Chosen settings | Train: trades, per trade | Valid: trades, per trade | **Test: trades** | **win / need** | **per trade (95% range)** | **profit** | test +1c slip | worst dip |
|---|---|---|---|--:|--:|--:|--:|--:|--:|
| A. Live rule (band + distance) | 70-95c, z>=1.5 | 556, +2.34c | 222, +5.31c | 169 | 90.5% / 88.9% | +1.67c (-2.8 to +5.9) | **+$2.83** | +$1.14 | $2.56 |
| B. Fair value (option model) | vol=ewma (scale 0.75), last 5 min, edge>=8c | 1769, +2.60c | 822, +1.29c | 658 | 29.5% / 28.3% | +1.15c (-1.6 to +4.0) | **+$7.59** | +$1.01 | $9.02 |
| C. Fair value + trend | momentum: + last 5 min trend, last 5 min, edge>=6c | 1882, +2.19c | 882, +1.59c | 702 | 37.7% / 38.3% | -0.52c (-3.3 to +2.6) | **-$3.66** | -$10.68 | $9.74 |
| D. Fade Kalshi overreaction | jump>=25c in 1 min, gold z<=0.3 | 141, -1.45c | 65, +8.88c | 61 | 27.9% / 32.3% | -4.38c (-15.2 to +6.6) | **-$2.67** | -$3.28 | $3.60 |
| E. Calibration table (Kalshi prices only) | edge>=4c, last 3 min | 308, +2.45c | 146, -1.01c | 115 | 56.5% / 59.4% | -2.85c (-10.0 to +4.8) | **-$3.28** | -$4.43 | $8.19 |
| F. Logistic regression (all features) | last 5 min, edge>=6c | 504, +12.12c | 256, +12.32c | 168 | 55.4% / 48.1% | +7.27c (-0.2 to +14.5) | **+$12.21** | +$10.54 | $4.96 |

### Every strategy on train and validation (test hidden)

| Family | Settings | Train trades | Train per trade | Train profit | Valid trades | Valid per trade | Valid profit |
|---|---|--:|--:|--:|--:|--:|--:|
| A. Live rule (band + distance) | 70-95c, z>=1 | 823 | +1.69c | +$13.89 | 325 | +4.19c | +$13.61 |
| A. Live rule (band + distance) | 70-95c, z>=1.5 | 556 | +2.34c | +$13.00 | 222 | +5.31c | +$11.80 |
| A. Live rule (band + distance) | 80-90c, z>=1 | 368 | +1.96c | +$7.23 | 144 | +6.17c | +$8.89 |
| A. Live rule (band + distance) | 80-90c, z>=1.5 | 236 | +2.27c | +$5.36 | 90 | +5.63c | +$5.07 |
| B. Fair value (option model) | vol=rv30 (scale 0.7), last 3 min, edge>=2c | 1829 | +1.03c | +$18.91 | 837 | +0.40c | +$3.36 |
| B. Fair value (option model) | vol=rv30 (scale 0.7), last 3 min, edge>=4c | 1693 | +1.37c | +$23.18 | 770 | +0.86c | +$6.60 |
| B. Fair value (option model) | vol=rv30 (scale 0.7), last 3 min, edge>=6c | 1576 | +1.84c | +$28.93 | 705 | +0.05c | +$0.36 |
| B. Fair value (option model) | vol=rv30 (scale 0.7), last 3 min, edge>=8c | 1472 | +2.60c | +$38.31 | 652 | +0.51c | +$3.31 |
| B. Fair value (option model) | vol=rv30 (scale 0.7), last 5 min, edge>=2c | 2180 | +0.93c | +$20.32 | 1000 | -0.56c | -$5.62 |
| B. Fair value (option model) | vol=rv30 (scale 0.7), last 5 min, edge>=4c | 2042 | +1.55c | +$31.58 | 953 | -0.72c | -$6.85 |
| B. Fair value (option model) | vol=rv30 (scale 0.7), last 5 min, edge>=6c | 1930 | +1.76c | +$33.88 | 893 | -0.74c | -$6.60 |
| B. Fair value (option model) | vol=rv30 (scale 0.7), last 5 min, edge>=8c | 1824 | +2.68c | +$48.81 | 834 | -0.10c | -$0.87 |
| B. Fair value (option model) | vol=rv30 (scale 0.7), last 10 min, edge>=2c | 2450 | -0.15c | -$3.57 | 1152 | -3.77c | -$43.48 |
| B. Fair value (option model) | vol=rv30 (scale 0.7), last 10 min, edge>=4c | 2417 | -0.11c | -$2.65 | 1127 | -3.09c | -$34.88 |
| B. Fair value (option model) | vol=rv30 (scale 0.7), last 10 min, edge>=6c | 2358 | +0.68c | +$16.13 | 1102 | -3.28c | -$36.18 |
| B. Fair value (option model) | vol=rv30 (scale 0.7), last 10 min, edge>=8c | 2280 | +1.04c | +$23.77 | 1062 | -2.13c | -$22.59 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 3 min, edge>=2c | 1835 | +0.87c | +$15.91 | 835 | -0.51c | -$4.29 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 3 min, edge>=4c | 1684 | +1.54c | +$25.89 | 771 | +0.08c | +$0.60 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 3 min, edge>=6c | 1561 | +1.71c | +$26.71 | 722 | +0.32c | +$2.32 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 3 min, edge>=8c | 1461 | +2.01c | +$29.38 | 662 | +0.56c | +$3.69 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 5 min, edge>=2c | 2154 | +1.13c | +$24.28 | 989 | -0.90c | -$8.88 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 5 min, edge>=4c | 2027 | +1.65c | +$33.44 | 935 | -0.61c | -$5.68 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 5 min, edge>=6c | 1924 | +2.19c | +$42.17 | 895 | -0.06c | -$0.49 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 5 min, edge>=8c | 1790 | +2.18c | +$39.05 | 829 | +0.69c | +$5.73 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 10 min, edge>=2c | 2447 | -0.47c | -$11.39 | 1143 | -3.12c | -$35.69 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 10 min, edge>=4c | 2407 | -0.48c | -$11.53 | 1123 | -3.63c | -$40.73 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 10 min, edge>=6c | 2333 | +0.55c | +$12.83 | 1100 | -3.16c | -$34.79 |
| B. Fair value (option model) | vol=rv60 (scale 0.75), last 10 min, edge>=8c | 2257 | +0.70c | +$15.77 | 1062 | -2.58c | -$27.36 |
| B. Fair value (option model) | vol=ewma (scale 0.75), last 3 min, edge>=2c | 1805 | +0.72c | +$13.05 | 825 | +0.50c | +$4.14 |
| B. Fair value (option model) | vol=ewma (scale 0.75), last 3 min, edge>=4c | 1655 | +1.49c | +$24.74 | 760 | +1.21c | +$9.20 |
| B. Fair value (option model) | vol=ewma (scale 0.75), last 3 min, edge>=6c | 1521 | +2.10c | +$32.01 | 697 | +0.71c | +$4.92 |
| B. Fair value (option model) | vol=ewma (scale 0.75), last 3 min, edge>=8c | 1421 | +2.45c | +$34.78 | 640 | +0.74c | +$4.71 |
| B. Fair value (option model) | vol=ewma (scale 0.75), last 5 min, edge>=2c | 2158 | +0.60c | +$12.87 | 990 | -0.12c | -$1.23 |
| B. Fair value (option model) | vol=ewma (scale 0.75), last 5 min, edge>=4c | 2021 | +1.01c | +$20.39 | 936 | -0.21c | -$1.96 |
| B. Fair value (option model) | vol=ewma (scale 0.75), last 5 min, edge>=6c | 1905 | +2.04c | +$38.93 | 880 | +0.44c | +$3.85 |
| B. Fair value (option model) | vol=ewma (scale 0.75), last 5 min, edge>=8c | 1769 | +2.60c | +$46.07 | 822 | +1.29c | +$10.58 |
| B. Fair value (option model) | vol=ewma (scale 0.75), last 10 min, edge>=2c | 2451 | -0.57c | -$14.03 | 1145 | -3.30c | -$37.80 |
| B. Fair value (option model) | vol=ewma (scale 0.75), last 10 min, edge>=4c | 2408 | +0.56c | +$13.44 | 1127 | -3.12c | -$35.11 |
| B. Fair value (option model) | vol=ewma (scale 0.75), last 10 min, edge>=6c | 2344 | +0.96c | +$22.52 | 1098 | -3.11c | -$34.15 |
| B. Fair value (option model) | vol=ewma (scale 0.75), last 10 min, edge>=8c | 2261 | +0.80c | +$18.05 | 1056 | -1.84c | -$19.40 |
| B. Fair value (option model) | vol=pyth (scale 0.65), last 3 min, edge>=2c | 1896 | +1.17c | +$22.26 | 880 | -0.96c | -$8.46 |
| B. Fair value (option model) | vol=pyth (scale 0.65), last 3 min, edge>=4c | 1764 | +0.97c | +$17.11 | 834 | -0.58c | -$4.87 |
| B. Fair value (option model) | vol=pyth (scale 0.65), last 3 min, edge>=6c | 1658 | +1.71c | +$28.37 | 775 | -0.75c | -$5.83 |
| B. Fair value (option model) | vol=pyth (scale 0.65), last 3 min, edge>=8c | 1570 | +1.89c | +$29.69 | 728 | -0.65c | -$4.76 |
| B. Fair value (option model) | vol=pyth (scale 0.65), last 5 min, edge>=2c | 2193 | +0.70c | +$15.27 | 1019 | -0.39c | -$3.96 |
| B. Fair value (option model) | vol=pyth (scale 0.65), last 5 min, edge>=4c | 2076 | +1.09c | +$22.64 | 980 | -0.54c | -$5.26 |
| B. Fair value (option model) | vol=pyth (scale 0.65), last 5 min, edge>=6c | 1982 | +1.27c | +$25.17 | 935 | -0.52c | -$4.89 |
| B. Fair value (option model) | vol=pyth (scale 0.65), last 5 min, edge>=8c | 1890 | +1.39c | +$26.22 | 896 | +0.24c | +$2.17 |
| B. Fair value (option model) | vol=pyth (scale 0.65), last 10 min, edge>=2c | 2453 | -0.10c | -$2.49 | 1144 | -2.43c | -$27.77 |
| B. Fair value (option model) | vol=pyth (scale 0.65), last 10 min, edge>=4c | 2419 | +0.13c | +$3.24 | 1131 | -2.73c | -$30.84 |
| B. Fair value (option model) | vol=pyth (scale 0.65), last 10 min, edge>=6c | 2365 | +0.63c | +$15.01 | 1110 | -2.37c | -$26.33 |
| B. Fair value (option model) | vol=pyth (scale 0.65), last 10 min, edge>=8c | 2299 | +0.72c | +$16.57 | 1083 | -1.24c | -$13.46 |
| B. Fair value (option model) | vol=blend (scale 0.75), last 3 min, edge>=2c | 1838 | +1.38c | +$25.40 | 845 | -0.52c | -$4.40 |
| B. Fair value (option model) | vol=blend (scale 0.75), last 3 min, edge>=4c | 1708 | +1.42c | +$24.29 | 780 | -0.28c | -$2.15 |
| B. Fair value (option model) | vol=blend (scale 0.75), last 3 min, edge>=6c | 1570 | +2.16c | +$33.96 | 708 | +0.13c | +$0.90 |
| B. Fair value (option model) | vol=blend (scale 0.75), last 3 min, edge>=8c | 1461 | +2.72c | +$39.79 | 656 | +0.40c | +$2.61 |
| B. Fair value (option model) | vol=blend (scale 0.75), last 5 min, edge>=2c | 2139 | +1.77c | +$37.92 | 990 | -0.58c | -$5.72 |
| B. Fair value (option model) | vol=blend (scale 0.75), last 5 min, edge>=4c | 2035 | +2.11c | +$42.95 | 950 | -0.31c | -$2.92 |
| B. Fair value (option model) | vol=blend (scale 0.75), last 5 min, edge>=6c | 1913 | +2.20c | +$42.14 | 891 | +0.31c | +$2.73 |
| B. Fair value (option model) | vol=blend (scale 0.75), last 5 min, edge>=8c | 1784 | +2.64c | +$47.05 | 836 | +1.03c | +$8.62 |
| B. Fair value (option model) | vol=blend (scale 0.75), last 10 min, edge>=2c | 2450 | -0.11c | -$2.78 | 1141 | -2.45c | -$27.92 |
| B. Fair value (option model) | vol=blend (scale 0.75), last 10 min, edge>=4c | 2413 | +0.44c | +$10.67 | 1120 | -2.11c | -$23.62 |
| B. Fair value (option model) | vol=blend (scale 0.75), last 10 min, edge>=6c | 2334 | +0.51c | +$11.84 | 1093 | -2.09c | -$22.80 |
| B. Fair value (option model) | vol=blend (scale 0.75), last 10 min, edge>=8c | 2242 | +1.62c | +$36.26 | 1067 | -1.86c | -$19.90 |
| C. Fair value + trend | momentum: + last 5 min trend, last 5 min, edge>=4c | 1998 | +1.82c | +$36.30 | 926 | +1.37c | +$12.65 |
| C. Fair value + trend | momentum: + last 5 min trend, last 5 min, edge>=6c | 1882 | +2.19c | +$41.25 | 882 | +1.59c | +$14.06 |
| C. Fair value + trend | mean reversion: - last 5 min trend, last 5 min, edge>=4c | 2236 | -2.86c | -$63.88 | 1032 | -2.50c | -$25.83 |
| C. Fair value + trend | mean reversion: - last 5 min trend, last 5 min, edge>=6c | 2187 | -2.17c | -$47.42 | 1005 | -2.33c | -$23.43 |
| C. Fair value + trend | RSI filter, last 5 min, edge>=4c | 1799 | +2.32c | +$41.80 | 808 | +0.40c | +$3.20 |
| C. Fair value + trend | RSI filter, last 5 min, edge>=6c | 1713 | +2.39c | +$40.90 | 770 | +0.83c | +$6.37 |
| D. Fade Kalshi overreaction | jump>=10c in 1 min, gold z<=0.3 | 387 | -2.70c | -$10.46 | 212 | -2.67c | -$5.65 |
| D. Fade Kalshi overreaction | jump>=10c in 1 min, gold z<=0.7 | 710 | -2.81c | -$19.96 | 371 | -0.76c | -$2.81 |
| D. Fade Kalshi overreaction | jump>=15c in 1 min, gold z<=0.3 | 285 | -1.77c | -$5.03 | 159 | -1.30c | -$2.07 |
| D. Fade Kalshi overreaction | jump>=15c in 1 min, gold z<=0.7 | 531 | -1.83c | -$9.71 | 295 | -1.23c | -$3.64 |
| D. Fade Kalshi overreaction | jump>=25c in 1 min, gold z<=0.3 | 141 | -1.45c | -$2.05 | 65 | +8.88c | +$5.77 |
| D. Fade Kalshi overreaction | jump>=25c in 1 min, gold z<=0.7 | 274 | -4.06c | -$11.13 | 148 | +1.65c | +$2.45 |
| E. Calibration table (Kalshi prices only) | edge>=2c, last 3 min | 960 | +0.82c | +$7.88 | 480 | -1.00c | -$4.81 |
| E. Calibration table (Kalshi prices only) | edge>=2c, last 14 min | 3863 | +2.61c | +$100.96 | 1816 | -2.33c | -$42.38 |
| E. Calibration table (Kalshi prices only) | edge>=4c, last 3 min | 308 | +2.45c | +$7.55 | 146 | -1.01c | -$1.47 |
| E. Calibration table (Kalshi prices only) | edge>=4c, last 14 min | 2642 | +4.66c | +$123.11 | 1299 | -2.80c | -$36.42 |
| E. Calibration table (Kalshi prices only) | edge>=6c, last 3 min | 77 | +7.16c | +$5.51 | 31 | +5.27c | +$1.63 |
| E. Calibration table (Kalshi prices only) | edge>=6c, last 14 min | 1283 | +6.30c | +$80.84 | 649 | -2.28c | -$14.82 |
| F. Logistic regression (all features) | last 3 min, edge>=2c | 829 | +5.29c | +$43.85 | 375 | +5.64c | +$21.15 |
| F. Logistic regression (all features) | last 5 min, edge>=2c | 1145 | +5.95c | +$68.11 | 540 | +6.00c | +$32.38 |
| F. Logistic regression (all features) | last 3 min, edge>=4c | 564 | +8.87c | +$50.04 | 259 | +8.04c | +$20.82 |
| F. Logistic regression (all features) | last 5 min, edge>=4c | 770 | +9.55c | +$73.55 | 374 | +9.90c | +$37.01 |
| F. Logistic regression (all features) | last 3 min, edge>=6c | 400 | +11.88c | +$47.51 | 179 | +10.37c | +$18.57 |
| F. Logistic regression (all features) | last 5 min, edge>=6c | 504 | +12.12c | +$61.07 | 256 | +12.32c | +$31.53 |
| F. Logistic regression (all features) | last 3 min, edge>=8c | 277 | +14.67c | +$40.65 | 137 | +9.73c | +$13.33 |
| F. Logistic regression (all features) | last 5 min, edge>=8c | 348 | +16.28c | +$56.67 | 184 | +12.12c | +$22.30 |

