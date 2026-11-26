#!/usr/bin/env python3
"""Backtest: buy the favorite only when gold is far from the target, judged by its recent speed.

Gold price stand-in: Coinbase PAXG-USD 1-minute candles (tokenized gold). Kalshi settles on Pyth gold,
which needs a paid key; we only use PAXG's *move since the market opened*, so its small premium cancels out.

distance score z = |PAXG move since open| / (typical 1-minute move * sqrt(minutes left))
  "typical 1-minute move" = standard deviation of PAXG 1-minute changes over the previous 30 minutes.
  z = 2 means gold would need an unusually big (2-sigma) move in the time left to cross the target.

Rule: at 3, 2, 1 minutes before close, buy the favorite (1 contract, at the ask, taker fee) the first time its
price is in the band AND PAXG agrees with the favorite's side AND z >= the cutoff.
Cutoffs are compared on Aug 1 - Oct 7 ("pick" period); the best is then checked on Oct 8 - Nov 26 ("check").
"""
import gzip
import json
import math
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAXG = os.path.join(HERE, "data", "PAXG-USD-1m.json.gz")
SPLIT = int(datetime(2026, 10, 8, tzinfo=ET).timestamp())


def get(url):
    for i in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "gold-backtest"}), timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            time.sleep(2 ** i)
            err = e
    raise RuntimeError(err)


def download_paxg(start, end):
    """{minute start ts: close} from Coinbase, cached; only fetches what's missing."""
    try:
        have = {int(k): v for k, v in json.load(gzip.open(PAXG, "rt")).items()}
    except (OSError, ValueError):
        have = {}
    iso = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    t = start - start % 60
    n = 0
    while t < end:
        t2 = min(end, t + 300 * 60)
        if not any(k in have for k in range(t, t2, 60 * 30)):       # skip blocks we already have
            for ts, lo, hi, op, cl, vol in get(f"https://api.exchange.coinbase.com/products/PAXG-USD/candles"
                                               f"?granularity=60&start={iso(t)}&end={iso(t2)}"):
                have[int(ts)] = cl
            n += 1
            time.sleep(0.35)
            if n % 50 == 0:
                print(f"  PAXG requests {n}, candles {len(have)}", flush=True)
        t = t2
    os.makedirs(os.path.dirname(PAXG), exist_ok=True)
    json.dump({str(k): v for k, v in sorted(have.items())}, gzip.open(PAXG, "wt"))
    return have


def price_at(px, t, max_age=600):
    """PAXG price at time t = close of the latest 1-minute candle that ended at or before t (candle start + 60)."""
    m = t - 60 - (t - 60) % 60
    for back in range(0, max_age, 60):
        v = px.get(m - back)
        if v is not None:
            return v
    return None


def speed(px, t, minutes=30):
    """Standard deviation of 1-minute relative changes over the previous `minutes` (forward-filled)."""
    vals = [price_at(px, t - 60 * i) for i in range(minutes + 1)]
    vals = [v for v in vals if v is not None]
    if len(vals) < 10:
        return None
    ch = [math.log(vals[i] / vals[i + 1]) for i in range(len(vals) - 1)]
    mu = sum(ch) / len(ch)
    sd = math.sqrt(sum((c - mu) ** 2 for c in ch) / len(ch))
    return max(sd, 2e-5)          # floor: PAXG sometimes doesn't trade for a few minutes


def fee_c(p):
    return math.ceil(round(0.07 * (p / 100) * (1 - p / 100) * 100, 6))


def simulate(ms, px, lo, hi, window, zcut, need_agree=True):
    out = []
    for m in ms:
        by = {k: (b, a) for k, b, a, v in m.get("c", [])}
        p_open = price_at(px, m["close"] - 900)
        if p_open is None:
            continue
        for k in range(window, 0, -1):
            if k not in by or by[k][0] is None or by[k][1] is None:
                continue
            b, a = by[k]
            opts = [(s, p) for s, p in (("yes", a), ("no", round(100 - b, 2))) if 0 < p < 100]
            if not opts:
                continue
            side, p = max(opts, key=lambda o: o[1])
            if not (lo <= p <= hi):
                continue
            t = m["close"] - 60 * k
            p_now, sd = price_at(px, t), speed(px, t)
            if p_now is None or sd is None:
                continue
            move = math.log(p_now / p_open)
            z = abs(move) / (sd * math.sqrt(k))
            if need_agree and ((move > 0) != (side == "yes") or move == 0):
                continue
            if z < zcut:
                continue
            won = side == m["result"]
            out.append({"close": m["close"], "p": p, "won": won, "pnl": (100 - p if won else -p) - fee_c(p), "z": z})
            break
    return out


def stats(tr):
    n = len(tr)
    if not n:
        return {"n": 0, "w": 0, "wr": 0, "need": 0, "pnl": 0, "per": 0, "t": 0}
    pnl = [t["pnl"] for t in tr]
    mu = sum(pnl) / n
    sd = math.sqrt(sum((x - mu) ** 2 for x in pnl) / n) or 1
    w = sum(t["won"] for t in tr)
    need = sum(t["p"] + fee_c(t["p"]) for t in tr) / (100 * n)
    return {"n": n, "w": w, "wr": w / n, "need": need, "pnl": sum(pnl) / 100, "per": mu, "t": mu / sd * math.sqrt(n)}


def main():
    ms = sorted(json.load(gzip.open(os.path.join(HERE, "data", "KXGOLD15M-full.json.gz"), "rt")), key=lambda m: m["close"])
    ms = [m for m in ms if m.get("c") and m["close"] >= int(datetime(2026, 8, 1, tzinfo=ET).timestamp())]
    print(f"{len(ms)} gold markets; downloading PAXG ...", flush=True)
    px = download_paxg(ms[0]["close"] - 3600, ms[-1]["close"])
    print(f"PAXG candles: {len(px)}")
    pick = [m for m in ms if m["close"] < SPLIT]
    check = [m for m in ms if m["close"] >= SPLIT]
    bands = [(80, 90), (85, 95), (90, 95), (80, 95)]
    cuts = [0, 1, 1.5, 2, 2.5, 3, 4]
    rows = []
    for b in bands:
        for w in (3, 2, 1):
            for z in cuts:
                rows.append((b, w, z, stats(simulate(pick, px, *b, w, z)), stats(simulate(check, px, *b, w, z))))
    base = {b: (stats(simulate(pick, px, *b, 3, 0, need_agree=False)), stats(simulate(check, px, *b, 3, 0, need_agree=False)))
            for b in bands}
    usd = lambda x: f"{'+' if x >= 0 else '-'}${abs(x):.2f}"
    cell = lambda s: f"{s['n']} | {s['wr'] * 100:.1f}% | {s['need'] * 100:.1f}% | {s['per']:+.2f}c | {usd(s['pnl'])}"
    L = ["# Distance-and-speed filter backtest (gold, PAXG as the gold price)", "",
         f"_{len(ms)} markets, Aug 1 - Nov 26, 2026. 1 contract per trade at the ask, Kalshi taker fee included. "
         "**Pick** = Aug 1 - Oct 7 (used to choose); **check** = Oct 8 - Nov 26 (not used to choose)._", "",
         "**z** = how far PAXG has moved from the market's start, measured in typical moves for the time left. "
         "z >= 2 means gold needs an unusually large move to cross back. z = 0 means no distance filter "
         "(but PAXG must still point the same way as the favorite).", "",
         "## Your rule: favorite 80-90c, last 3 minutes", "",
         "| z at least | Pick: trades | won | need | per trade | profit | Check: trades | won | need | per trade | profit |",
         "|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|"]
    s0 = base[(80, 90)]
    L.append(f"| no PAXG check | {cell(s0[0])} | {cell(s0[1])} |")
    for b, w, z, sp, sc in rows:
        if b == (80, 90) and w == 3:
            L.append(f"| {z:g} | {cell(sp)} | {cell(sc)} |")
    L += ["", "## Best 10 versions by the pick period (then: how they did on check)", "",
          "| Band | Start | z at least | Pick: trades | won | need | per trade | profit | Check: trades | won | need | per trade | profit |",
          "|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|"]
    good = [r for r in rows if r[3]["n"] >= 60]
    for b, w, z, sp, sc in sorted(good, key=lambda r: -r[3]["t"])[:10]:
        L.append(f"| {b[0]}-{b[1]}c | {w} min | {z:g} | {cell(sp)} | {cell(sc)} |")
    L += ["", "## Every version", "", "| Band | Start | z | Pick trades | Pick profit | Pick t | Check trades | Check profit | Check t |",
          "|---|---|--:|--:|--:|--:|--:|--:|--:|"]
    for b, w, z, sp, sc in rows:
        L.append(f"| {b[0]}-{b[1]}c | {w} | {z:g} | {sp['n']} | {usd(sp['pnl'])} | {sp['t']:+.2f} | {sc['n']} | {usd(sc['pnl'])} | {sc['t']:+.2f} |")
    open(os.path.join(HERE, "PAXG_FILTER.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L[:24 + 10]))


if __name__ == "__main__":
    sys.exit(main())
