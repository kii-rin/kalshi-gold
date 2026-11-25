# Gold backtest (KXGOLD15M)

_7836 settled 15-minute gold markets, Jan 01, 2026 to Nov 25, 2026 (7777 with price data). $1 per trade, Kalshi fee included, held to settlement. Generated Nov 25 2:55 PM ET._

> A backtest uses one price per minute and assumes you get that price. Real fills can be worse, especially in fast markets. Past results don't guarantee future ones.

**How to read it:** *Need* is the win rate required to break even at those prices. *Low* is the lowest win rate the results still allow (95% confidence). If Low is above Need, the edge is probably real. *Steady* = the same side was already the favorite at or above the band one minute earlier.

## All versions, best first

| Band | Start | Steady | Trades | Won | Win rate | Need | Low | Profit | Per trade | Worst dip | Verdict |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|
| 90-95c | 2 min | yes | 627 | 592 | 94.4% | 93.9% | 92.3% | **+$3.01** | 0.5c | $6.37 | can't tell yet |
| 90-95c | 3 min | yes | 1063 | 1001 | 94.2% | 94.0% | 92.6% | **+$1.69** | 0.2c | $8.12 | can't tell yet |
| 90-95c | 1 min | yes | 252 | 233 | 92.5% | 93.9% | 88.5% | **-$3.72** | -1.5c | $5.03 | below break-even, not certain |
| 90-97c | 1 min | yes | 509 | 480 | 94.3% | 95.6% | 91.9% | **-$6.71** | -1.3c | $9.18 | below break-even, not certain |
| 85-95c | 1 min | yes | 466 | 425 | 91.2% | 92.8% | 88.3% | **-$7.28** | -1.6c | $8.66 | below break-even, not certain |
| 88-97c | 1 min | yes | 638 | 598 | 93.7% | 95.2% | 91.6% | **-$9.50** | -1.5c | $11.68 | below break-even, not certain |
| 85-95c | 2 min | yes | 1169 | 1071 | 91.6% | 92.6% | 89.9% | **-$11.42** | -1.0c | $14.34 | below break-even, not certain |
| 90-97c | 2 min | yes | 1198 | 1134 | 94.7% | 95.7% | 93.2% | **-$11.97** | -1.0c | $13.98 | below break-even, not certain |
| 85-97c | 1 min | yes | 808 | 753 | 93.2% | 94.7% | 91.2% | **-$11.97** | -1.5c | $13.87 | below break-even, not certain |
| 90-97c | 3 min | yes | 1932 | 1834 | 94.9% | 95.6% | 93.9% | **-$13.34** | -0.7c | $17.11 | below break-even, not certain |
| 85-95c | 3 min | yes | 1855 | 1705 | 91.9% | 92.6% | 90.6% | **-$13.54** | -0.7c | $19.25 | below break-even, not certain |
| 90-95c | 2 min | no | 1642 | 1521 | 92.6% | 93.6% | 91.3% | **-$15.28** | -0.9c | $22.23 | below break-even, not certain |
| 90-95c | 1 min | no | 743 | 679 | 91.4% | 93.6% | 89.1% | **-$16.65** | -2.2c | $19.71 | loses money |
| 88-97c | 3 min | yes | 2293 | 2162 | 94.3% | 95.1% | 93.3% | **-$18.48** | -0.8c | $21.07 | below break-even, not certain |
| 90-97c | 1 min | no | 1233 | 1152 | 93.4% | 95.1% | 91.9% | **-$20.25** | -1.6c | $24.33 | loses money |
| 88-97c | 2 min | yes | 1458 | 1367 | 93.8% | 95.2% | 92.4% | **-$20.52** | -1.4c | $21.39 | loses money |
| 95-99c | 1 min | yes | 838 | 810 | 96.7% | 99.1% | 95.2% | **-$20.82** | -2.5c | $21.13 | loses money |
| 80-97c | 1 min | yes | 1061 | 972 | 91.6% | 93.6% | 89.8% | **-$21.17** | -2.0c | $22.58 | loses money |
| 88-97c | 1 min | no | 1376 | 1276 | 92.7% | 94.5% | 91.2% | **-$24.22** | -1.8c | $28.07 | loses money |
| 90-95c | 3 min | no | 2506 | 2319 | 92.5% | 93.5% | 91.4% | **-$24.58** | -1.0c | $31.34 | loses money |
| 85-97c | 3 min | yes | 2773 | 2590 | 93.4% | 94.3% | 92.4% | **-$25.64** | -0.9c | $30.32 | loses money |
| 85-95c | 1 min | no | 1050 | 939 | 89.4% | 92.0% | 87.4% | **-$27.40** | -2.6c | $29.51 | loses money |
| 85-97c | 2 min | yes | 1817 | 1685 | 92.7% | 94.4% | 91.4% | **-$29.71** | -1.6c | $31.28 | loses money |
| 95-99c | 2 min | yes | 1748 | 1701 | 97.3% | 99.1% | 96.4% | **-$30.54** | -1.7c | $31.11 | loses money |
| 85-97c | 1 min | no | 1540 | 1412 | 91.7% | 93.7% | 90.2% | **-$31.00** | -2.0c | $33.66 | loses money |
| 90-97c | 2 min | no | 2516 | 2357 | 93.7% | 94.9% | 92.7% | **-$31.01** | -1.2c | $36.66 | loses money |
| 95-99c | 3 min | yes | 2400 | 2344 | 97.7% | 99.0% | 97.0% | **-$31.06** | -1.3c | $31.36 | loses money |
| 90-97c | 3 min | no | 3618 | 3394 | 93.8% | 94.8% | 93.0% | **-$34.16** | -0.9c | $41.61 | loses money |
| 80-97c | 1 min | no | 1786 | 1614 | 90.4% | 92.3% | 88.9% | **-$34.55** | -1.9c | $36.26 | loses money |
| 80-97c | 3 min | yes | 3381 | 3104 | 91.8% | 92.9% | 90.8% | **-$37.10** | -1.1c | $41.17 | loses money |
| 95-99c | 1 min | no | 1913 | 1848 | 96.6% | 98.7% | 95.7% | **-$40.34** | -2.1c | $41.20 | loses money |
| 88-97c | 2 min | no | 2754 | 2553 | 92.7% | 94.2% | 91.7% | **-$42.54** | -1.5c | $48.27 | loses money |
| 88-97c | 3 min | no | 3916 | 3634 | 92.8% | 94.0% | 91.9% | **-$46.22** | -1.2c | $54.90 | loses money |
| 80-97c | 2 min | yes | 2303 | 2095 | 91.0% | 93.1% | 89.7% | **-$48.96** | -2.1c | $51.18 | loses money |
| 85-95c | 2 min | no | 2274 | 2037 | 89.6% | 91.7% | 88.3% | **-$49.10** | -2.2c | $54.42 | loses money |
| 85-95c | 3 min | no | 3329 | 2995 | 90.0% | 91.6% | 88.9% | **-$52.86** | -1.6c | $57.66 | loses money |
| 80-99c | 3 min | yes | 5106 | 4806 | 94.1% | 95.2% | 93.4% | **-$54.72** | -1.1c | $57.10 | loses money |
| 95-99c | 3 min | no | 4388 | 4262 | 97.1% | 98.4% | 96.6% | **-$55.54** | -1.3c | $56.43 | loses money |
| 80-99c | 1 min | yes | 2296 | 2165 | 94.3% | 96.7% | 93.3% | **-$55.69** | -2.4c | $56.12 | loses money |
| 95-99c | 2 min | no | 3450 | 3344 | 96.9% | 98.6% | 96.3% | **-$56.66** | -1.6c | $58.32 | loses money |
| 85-97c | 3 min | no | 4250 | 3890 | 91.5% | 92.9% | 90.7% | **-$58.61** | -1.4c | $64.11 | loses money |
| 85-97c | 2 min | no | 3054 | 2783 | 91.1% | 93.2% | 90.1% | **-$63.99** | -2.1c | $68.42 | loses money |
| 80-97c | 3 min | no | 4660 | 4185 | 89.8% | 91.2% | 88.9% | **-$64.70** | -1.4c | $68.43 | loses money |
| 80-97c | 2 min | no | 3426 | 3074 | 89.7% | 91.7% | 88.7% | **-$67.39** | -2.0c | $73.44 | loses money |
| 80-99c | 2 min | yes | 4029 | 3793 | 94.1% | 95.9% | 93.4% | **-$69.22** | -1.7c | $72.13 | loses money |
| 80-99c | 1 min | no | 3138 | 2922 | 93.1% | 95.4% | 92.2% | **-$70.12** | -2.2c | $71.34 | loses money |
| 80-99c | 3 min | no | 6174 | 5685 | 92.1% | 93.3% | 91.4% | **-$75.01** | -1.2c | $77.66 | loses money |
| 80-99c | 2 min | no | 5098 | 4721 | 92.6% | 94.3% | 91.9% | **-$85.35** | -1.7c | $91.88 | loses money |

## By month (88-97c, 3 min, steady)

| | Trades | Won | Win rate | Profit |
|---|--:|--:|--:|--:|
| July 2026 | 9 | 2 | 22.2% | -$6.81 |
| August 2026 | 661 | 624 | 94.4% | -$6.40 |
| September 2026 | 674 | 636 | 94.4% | -$4.36 |
| October 2026 | 523 | 500 | 95.6% | +$3.60 |
| November 2026 | 426 | 400 | 93.9% | -$4.50 |

## By hour (Eastern) (88-97c, 3 min, steady)

| | Trades | Won | Win rate | Profit |
|---|--:|--:|--:|--:|
| 12 AM | 106 | 99 | 93.4% | -$1.48 |
| 1 AM | 108 | 100 | 92.6% | -$2.41 |
| 2 AM | 100 | 94 | 94.0% | -$1.02 |
| 3 AM | 81 | 77 | 95.1% | +$0.30 |
| 4 AM | 76 | 75 | 98.7% | +$2.45 |
| 5 AM | 99 | 94 | 94.9% | +$0.00 |
| 6 AM | 91 | 88 | 96.7% | +$0.96 |
| 7 AM | 119 | 112 | 94.1% | -$1.34 |
| 8 AM | 85 | 77 | 90.6% | -$4.01 |
| 9 AM | 90 | 83 | 92.2% | -$2.66 |
| 10 AM | 113 | 105 | 92.9% | -$2.01 |
| 11 AM | 84 | 81 | 96.4% | +$1.34 |
| 12 PM | 95 | 91 | 95.8% | +$0.58 |
| 1 PM | 96 | 91 | 94.8% | -$0.29 |
| 2 PM | 96 | 89 | 92.7% | -$1.98 |
| 3 PM | 82 | 79 | 96.3% | +$0.81 |
| 4 PM | 94 | 92 | 97.9% | +$2.07 |
| 5 PM | 74 | 69 | 93.2% | -$1.49 |
| 6 PM | 95 | 88 | 92.6% | -$2.48 |
| 7 PM | 102 | 99 | 97.1% | +$1.88 |
| 8 PM | 102 | 95 | 93.1% | -$1.76 |
| 9 PM | 111 | 104 | 93.7% | -$1.44 |
| 10 PM | 95 | 87 | 91.6% | -$3.48 |
| 11 PM | 99 | 93 | 93.9% | -$1.03 |

## By price paid (88-97c, 3 min, steady)

| | Trades | Won | Win rate | Profit |
|---|--:|--:|--:|--:|
| 87-89c | 150 | 130 | 86.7% | -$4.22 |
| 90-92c | 491 | 458 | 93.3% | +$4.70 |
| 93-95c | 930 | 890 | 95.7% | +$1.10 |
| 96-98c | 722 | 684 | 94.7% | -$20.06 |

_11940 requests to Kalshi this run._
