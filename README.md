# Kalshi gold cloud bot

Runs all day on a cloud server, so no PC needed.

**Rule:** in the last 2 minutes before each 15-minute gold market closes, if the favorite costs **90–95¢** and has stayed the favorite at 90¢+ for the minute before, buy it once and hold until it settles. This was the best version in a backtest of 7,800+ markets (see BACKTEST.md). Even so, it only roughly broke even, so treat this as a learning test.

It starts in **paper mode**: it only logs what it *would* buy. Nothing real happens until you set `LIVE=true`.

## Quick test on GitHub ($1 per trade)

For a short test (a day or so), it can run on GitHub Actions. The defaults there are **$1 per trade with no daily limit**, for real.

1. In this repo, go to **Settings → Secrets and variables → Actions**.
2. Under **Secrets**, add `KALSHI_API_KEY_ID` and `KALSHI_PRIVATE_KEY` (the whole key text).
3. Go to **Actions → Gold bot (test run) → Run workflow**. It runs for about 6 hours. Tap the run to watch its log.
4. It keeps itself going: GitHub tries to start it every hour, and a new run waits in line until the current one ends. To stop it, add the repo **variable** `BOT_ENABLED` = `false` and cancel the running run.

Optional **variables**:
- `LIVE` = `false` for paper mode
- `DOLLARS_PER_TRADE` to bet more, or `DAILY_LIMIT` to cap daily spending (`0` = no limit)
- `BAND_LOW` / `BAND_HIGH` to change the price band
- `NTFY_TOPIC` for phone alerts

**Trade log:** open [TRADES.md](TRADES.md) any time. It shows today's and all-time results (trades, wins, losses, profit), a row for each trade once its market settles, and any failed orders. It's updated by the bot, with no notifications.

Restarts don't reset the daily limit: the bot reads today's buys from Kalshi when it starts. A private repo gets 2,000 free Actions minutes a month, and a full day uses about 1,440. GitHub Actions is meant for testing, so for running long-term, use Railway (below).

## Set up from your phone (Railway, for running long-term)

### 1. Kalshi API key
On kalshi.com, go to **Account & security → API keys → Create key**. Keep two things:
- the **Key ID**
- the **private key** (a text file that starts with `-----BEGIN`). Open it and copy all of its text.

### 2. Railway (runs the bot, Hobby plan $5/month)
1. Go to railway.com, sign in with GitHub, and choose the Hobby plan.
2. Tap **New Project → Deploy from GitHub repo** and pick this repo.
3. Open the service and go to **Variables**. Add:

| Variable | Value |
|---|---|
| `KALSHI_API_KEY_ID` | your Key ID |
| `KALSHI_PRIVATE_KEY` | the whole private key text, including the BEGIN/END lines |
| `LIVE` | `false` (paper mode to start) |

4. It redeploys by itself. Open **Deployments → View logs**. You should see:
   `Kalshi key works. Balance: $...`
   then lines like `PAPER KXGOLD15M-...: would buy YES x2 at 93c` when gold is in the band.

### 3. Go live
Once the paper trades look right (give it a day or so), change `LIVE` to `true`. To stop the bot at any time, set `LIVE` back to `false`, or remove the deployment.

## Optional settings (Variables)

| Variable | Default | Meaning |
|---|---|---|
| `BAND_LOW` / `BAND_HIGH` | `90` / `95` (GitHub) | Price band in cents |
| `START_SECONDS` | `120` (GitHub) | Only buy in the last this-many seconds |
| `STABLE_SECONDS` | `60` (GitHub) | Favorite must have stayed at or above `BAND_LOW` this long before buying |
| `DOLLARS_PER_TRADE` | `2` | Buys whole contracts ($2 at 93¢ = 2 contracts) |
| `DAILY_LIMIT` | `20` | Max dollars spent per day (Eastern time). `0` = no limit |
| `SLIPPAGE_CENTS` | `1` | May pay up to this much above the price it saw, but never above `BAND_HIGH` |
| `SERIES` | `KXGOLD15M` | Market to trade, e.g. `KXSILVER15M` |
| `NTFY_TOPIC` | (off) | Phone alerts: install the free **ntfy** app, subscribe to a long random topic name, and put the same name here |

## Notes
- Gold markets only trade on weekdays. At other times the bot just waits.
- It only buys when the same side has been the favorite at or above `BAND_LOW` for the last 30 seconds (`STABLE_SECONDS`), and the live order book still shows it in the band right before ordering. That skips markets that spike into the band.
- Orders are immediate-or-cancel: if nothing fills, it tries up to 3 times while still in the window and in the band.
- The daily spend total resets if Railway restarts the bot.
- The backtest covered about 37 trades, which isn't proof. Keep bets small at first.

## Run tests
```
pip install cryptography pytest
python -m pytest -q
```
