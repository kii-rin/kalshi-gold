# Gold backtest (KXGOLD15M)

_349 settled 15-minute gold markets, Sep 22, 2026 to Sep 26, 2026 (349 with price data). $1 per trade, Kalshi fee included, held to settlement. Generated Nov 25 2:06 PM ET._

> A backtest uses one price per minute and assumes you get that price. Real fills can be worse, especially in fast markets. Past results don't guarantee future ones.

**How to read it:** *Need* is the win rate required to break even at those prices. *Low* is the lowest win rate the results still allow (95% confidence). If Low is above Need, the edge is probably real. *Steady* = the same side was already the favorite at or above the band one minute earlier.

## All versions, best first

| Band | Start | Steady | Trades | Won | Win rate | Need | Low | Profit | Per trade | Worst dip | Verdict |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|
| 85-95c | 3 min | yes | 80 | 77 | 96.2% | 92.5% | 89.5% | **+$2.98** | 3.7c | $0.95 | can't tell yet |
| 85-95c | 2 min | yes | 53 | 50 | 94.3% | 92.5% | 84.6% | **+$0.99** | 1.9c | $0.95 | can't tell yet |
| 90-95c | 3 min | yes | 46 | 44 | 95.7% | 93.8% | 85.5% | **+$0.84** | 1.8c | $0.95 | too few trades |
| 85-97c | 3 min | yes | 121 | 114 | 94.2% | 94.2% | 88.5% | **+$0.05** | 0.0c | $2.92 | can't tell yet |
| 85-95c | 1 min | yes | 22 | 20 | 90.9% | 92.4% | 72.2% | **-$0.33** | -1.5c | $1.17 | too few trades |
| 90-95c | 2 min | yes | 26 | 24 | 92.3% | 93.9% | 75.9% | **-$0.42** | -1.6c | $0.95 | too few trades |
| 88-97c | 3 min | yes | 93 | 88 | 94.6% | 95.2% | 88.0% | **-$0.50** | -0.5c | $2.59 | loses money |
| 90-95c | 1 min | yes | 9 | 8 | 88.9% | 94.6% | 56.5% | **-$0.51** | -5.7c | $0.95 | too few trades |
| 88-97c | 1 min | yes | 24 | 22 | 91.7% | 95.5% | 74.2% | **-$0.92** | -3.8c | $1.68 | too few trades |
| 95-99c | 3 min | yes | 99 | 97 | 98.0% | 98.9% | 92.9% | **-$0.96** | -1.0c | $1.76 | loses money |
| 88-97c | 1 min | no | 56 | 52 | 92.9% | 94.6% | 83.0% | **-$0.97** | -1.7c | $1.23 | loses money |
| 90-95c | 1 min | no | 32 | 29 | 90.6% | 93.7% | 75.8% | **-$0.98** | -3.1c | $1.36 | too few trades |
| 85-97c | 1 min | yes | 33 | 30 | 90.9% | 93.9% | 76.4% | **-$0.98** | -3.0c | $1.99 | too few trades |
| 90-97c | 3 min | yes | 85 | 80 | 94.1% | 95.4% | 87.0% | **-$1.13** | -1.3c | $2.64 | loses money |
| 90-97c | 1 min | yes | 20 | 18 | 90.0% | 95.8% | 69.9% | **-$1.16** | -5.8c | $1.73 | too few trades |
| 85-97c | 2 min | yes | 78 | 72 | 92.3% | 94.0% | 84.2% | **-$1.32** | -1.7c | $2.74 | loses money |
| 95-99c | 2 min | yes | 64 | 62 | 96.9% | 99.0% | 89.3% | **-$1.34** | -2.1c | $1.86 | loses money |
| 88-97c | 2 min | yes | 55 | 51 | 92.7% | 95.2% | 82.7% | **-$1.34** | -2.4c | $2.16 | loses money |
| 85-95c | 2 min | no | 101 | 91 | 90.1% | 91.5% | 82.7% | **-$1.39** | -1.4c | $4.19 | loses money |
| 90-97c | 1 min | no | 52 | 48 | 92.3% | 95.0% | 81.8% | **-$1.39** | -2.7c | $1.65 | loses money |
| 85-95c | 1 min | no | 51 | 45 | 88.2% | 91.4% | 76.6% | **-$1.60** | -3.1c | $2.62 | loses money |
| 95-99c | 1 min | yes | 32 | 30 | 93.8% | 99.0% | 79.9% | **-$1.68** | -5.3c | $1.91 | too few trades |
| 90-97c | 2 min | yes | 47 | 43 | 91.5% | 95.4% | 80.1% | **-$1.83** | -3.9c | $2.21 | too few trades |
| 85-95c | 3 min | no | 146 | 131 | 89.7% | 91.1% | 83.7% | **-$1.97** | -1.3c | $4.30 | loses money |
| 95-99c | 1 min | no | 76 | 73 | 96.1% | 98.7% | 89.0% | **-$1.99** | -2.6c | $2.71 | loses money |
| 85-97c | 1 min | no | 71 | 64 | 90.1% | 93.0% | 81.0% | **-$2.01** | -2.8c | $3.20 | loses money |
| 80-97c | 3 min | yes | 153 | 139 | 90.8% | 92.2% | 85.2% | **-$2.12** | -1.4c | $5.02 | loses money |
| 90-95c | 2 min | no | 73 | 66 | 90.4% | 93.4% | 81.5% | **-$2.17** | -3.0c | $3.35 | loses money |
| 80-97c | 1 min | no | 82 | 73 | 89.0% | 91.7% | 80.4% | **-$2.21** | -2.7c | $3.04 | loses money |
| 85-97c | 3 min | no | 197 | 180 | 91.4% | 92.7% | 86.6% | **-$2.65** | -1.3c | $5.13 | loses money |
| 80-97c | 1 min | yes | 48 | 42 | 87.5% | 93.0% | 75.3% | **-$2.66** | -5.6c | $2.95 | too few trades |
| 95-99c | 3 min | no | 198 | 192 | 97.0% | 98.3% | 93.5% | **-$2.72** | -1.4c | $4.09 | loses money |
| 95-99c | 2 min | no | 145 | 140 | 96.6% | 98.4% | 92.2% | **-$2.72** | -1.9c | $3.75 | loses money |
| 80-99c | 3 min | yes | 228 | 213 | 93.4% | 94.6% | 89.4% | **-$2.79** | -1.2c | $5.27 | loses money |
| 90-95c | 3 min | no | 107 | 97 | 90.7% | 93.3% | 83.6% | **-$2.80** | -2.6c | $3.65 | loses money |
| 80-99c | 3 min | no | 286 | 262 | 91.6% | 92.7% | 87.8% | **-$3.09** | -1.1c | $8.16 | loses money |
| 85-97c | 2 min | no | 140 | 127 | 90.7% | 93.1% | 84.8% | **-$3.33** | -2.4c | $4.56 | loses money |
| 80-97c | 3 min | no | 222 | 198 | 89.2% | 90.7% | 84.4% | **-$3.40** | -1.5c | $8.33 | loses money |
| 88-97c | 3 min | no | 175 | 161 | 92.0% | 94.0% | 87.0% | **-$3.57** | -2.0c | $4.67 | loses money |
| 88-97c | 2 min | no | 123 | 112 | 91.1% | 94.1% | 84.7% | **-$3.76** | -3.1c | $4.34 | loses money |
| 80-99c | 1 min | no | 138 | 127 | 92.0% | 94.8% | 86.3% | **-$3.79** | -2.7c | $4.82 | loses money |
| 80-97c | 2 min | no | 159 | 141 | 88.7% | 91.2% | 82.8% | **-$4.04** | -2.5c | $6.81 | loses money |
| 80-97c | 2 min | yes | 105 | 93 | 88.6% | 92.5% | 81.1% | **-$4.08** | -3.9c | $5.01 | loses money |
| 90-97c | 2 min | no | 113 | 103 | 91.2% | 94.8% | 84.5% | **-$4.09** | -3.6c | $4.66 | loses money |
| 80-99c | 1 min | yes | 98 | 90 | 91.8% | 96.2% | 84.7% | **-$4.30** | -4.4c | $4.59 | loses money |
| 90-97c | 3 min | no | 164 | 151 | 92.1% | 94.7% | 86.9% | **-$4.33** | -2.6c | $5.37 | loses money |
| 80-99c | 2 min | yes | 176 | 163 | 92.6% | 95.2% | 87.8% | **-$4.63** | -2.6c | $5.52 | loses money |
| 80-99c | 2 min | no | 228 | 209 | 91.7% | 93.7% | 87.4% | **-$4.63** | -2.0c | $6.72 | loses money |

## By month (88-97c, 3 min, steady)

| | Trades | Won | Win rate | Profit |
|---|--:|--:|--:|--:|
| September 2026 | 93 | 88 | 94.6% | -$0.50 |

## By hour (Eastern) (88-97c, 3 min, steady)

| | Trades | Won | Win rate | Profit |
|---|--:|--:|--:|--:|
| 12 AM | 6 | 6 | 100.0% | +$0.29 |
| 1 AM | 4 | 4 | 100.0% | +$0.16 |
| 2 AM | 4 | 4 | 100.0% | +$0.21 |
| 3 AM | 2 | 2 | 100.0% | +$0.12 |
| 4 AM | 2 | 2 | 100.0% | +$0.04 |
| 5 AM | 5 | 5 | 100.0% | +$0.30 |
| 6 AM | 6 | 6 | 100.0% | +$0.33 |
| 7 AM | 5 | 5 | 100.0% | +$0.15 |
| 8 AM | 3 | 2 | 66.7% | -$0.88 |
| 9 AM | 3 | 3 | 100.0% | +$0.11 |
| 10 AM | 4 | 4 | 100.0% | +$0.18 |
| 11 AM | 8 | 6 | 75.0% | -$1.60 |
| 12 PM | 4 | 4 | 100.0% | +$0.24 |
| 1 PM | 4 | 4 | 100.0% | +$0.24 |
| 2 PM | 3 | 3 | 100.0% | +$0.18 |
| 3 PM | 3 | 3 | 100.0% | +$0.14 |
| 4 PM | 4 | 3 | 75.0% | -$0.88 |
| 5 PM | 3 | 2 | 66.7% | -$0.82 |
| 6 PM | 2 | 2 | 100.0% | +$0.09 |
| 7 PM | 4 | 4 | 100.0% | +$0.24 |
| 8 PM | 4 | 4 | 100.0% | +$0.21 |
| 9 PM | 4 | 4 | 100.0% | +$0.16 |
| 10 PM | 4 | 4 | 100.0% | +$0.20 |
| 11 PM | 2 | 2 | 100.0% | +$0.09 |

## By price paid (88-97c, 3 min, steady)

| | Trades | Won | Win rate | Profit |
|---|--:|--:|--:|--:|
| 87-89c | 3 | 3 | 100.0% | +$0.33 |
| 90-92c | 23 | 22 | 95.7% | +$0.80 |
| 93-95c | 39 | 36 | 92.3% | -$1.31 |
| 96-98c | 28 | 27 | 96.4% | -$0.32 |

_371 requests to Kalshi this run._
