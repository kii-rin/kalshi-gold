#!/usr/bin/env python3
"""Compare "buy the favorite near the close" across every downloaded 15-minute market.

Reads data/<series>-full.json.gz. Same rules as backtest.py: 1 contract at the ask, Kalshi taker fee, held to
settlement; "steady" = same favorite at >= the band's low end one minute earlier.
Each market's data is split in time: "first" (older 60%) and "last" (newer 40%), so a rule has to work in both.
Writes MARKETS.md.
"""
import glob
import gzip
import json
import math
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import backtest as bt  # noqa: E402

ET = ZoneInfo("America/New_York")
BANDS = [(70, 95), (80, 90), (85, 95), (90, 95), (90, 97), (95, 99)]
NAMES = {"KXGOLD15M": "Gold", "KXSILVER15M": "Silver", "KXPLATINUM15M": "Platinum", "KXPALLADIUM15M": "Palladium",
         "KXCOPPER15M": "Copper", "KXWTI15M": "WTI oil", "KXNATGAS15M": "Natural gas", "KXEURUSD15M": "EUR/USD",
         "KXGBPUSD15M": "GBP/USD", "KXUSDJPY15M": "USD/JPY"}


def one_contract(tr):
    out = []
    for t in tr:
        p = t["p"]
        pnl = (100 - p if t["won"] else -p) - bt.fee_c(1, p)
        out.append({**t, "n": 1, "cost": p + bt.fee_c(1, p), "pnl": pnl})
    return out


def s(tr):
    n = len(tr)
    if not n:
        return {"n": 0, "pnl": 0.0, "per": 0.0, "wr": 0.0, "need": 0.0, "t": 0.0}
    x = [t["pnl"] for t in tr]
    mu = sum(x) / n
    sd = math.sqrt(sum((v - mu) ** 2 for v in x) / n) or 1
    return {"n": n, "pnl": sum(x) / 100, "per": mu, "wr": sum(t["won"] for t in tr) / n,
            "need": sum(t["cost"] for t in tr) / (100 * n), "t": mu / sd * math.sqrt(n)}


def main():
    files = sorted(glob.glob(os.path.join(HERE, "data", "*-full.json.gz")))
    usd = lambda v: f"{'+' if v >= 0 else '-'}${abs(v):.2f}"
    summary, detail = [], []
    for f in files:
        series = os.path.basename(f).replace("-full.json.gz", "")
        ms = sorted((m for m in json.load(gzip.open(f, "rt")) if m.get("q") and any(m["q"])), key=lambda m: m["close"])
        if len(ms) < 200:
            continue
        cut = ms[int(len(ms) * 0.6)]["close"]
        first, last = [m for m in ms if m["close"] < cut], [m for m in ms if m["close"] >= cut]
        d0 = datetime.fromtimestamp(ms[0]["close"], ET).strftime("%b %d")
        dc = datetime.fromtimestamp(cut, ET).strftime("%b %d")
        d1 = datetime.fromtimestamp(ms[-1]["close"], ET).strftime("%b %d")
        rows = []
        for lo, hi in BANDS:
            for w in (3, 2, 1):
                for st in (False, True):
                    a = s(one_contract(bt.simulate(first, lo, hi, w, st)))
                    b = s(one_contract(bt.simulate(last, lo, hi, w, st)))
                    rows.append(((lo, hi), w, st, a, b))
        both = [r for r in rows if r[3]["n"] >= 40 and r[4]["n"] >= 25]
        best = max(both, key=lambda r: min(r[3]["t"], r[4]["t"]), default=None)   # best in the weaker period
        name = NAMES.get(series, series)
        if best:
            b, w, st, a, c = best
            summary.append((name, len(ms), d0, d1, f"{b[0]}-{b[1]}c, {w} min{', steady' if st else ''}", a, c))
        detail += ["", f"## {name} ({series}): {len(ms)} markets, {d0} - {d1} (first part to {dc})", "",
                   "| Band | Start | Steady | First: trades | won | need | per trade | profit | Last: trades | won | need | per trade | profit |",
                   "|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|"]
        for b, w, st, a, c in sorted(rows, key=lambda r: -(r[3]["pnl"] + r[4]["pnl"]))[:12]:
            detail.append(f"| {b[0]}-{b[1]}c | {w} min | {'yes' if st else 'no'} | {a['n']} | {a['wr'] * 100:.1f}% | "
                          f"{a['need'] * 100:.1f}% | {a['per']:+.2f}c | {usd(a['pnl'])} | {c['n']} | {c['wr'] * 100:.1f}% | "
                          f"{c['need'] * 100:.1f}% | {c['per']:+.2f}c | {usd(c['pnl'])} |")
    L = ["# Favorite-near-the-close across markets", "",
         "_Each market's own history, split in time: **first** (older 60%) and **last** (newer 40%). 1 contract per trade "
         "at the ask, Kalshi taker fee included. No outside price data: this is the plain price-band rule. A rule only "
         "counts if it works in both parts._", "",
         "## Best version per market (chosen by its weaker part)", "",
         "| Market | Markets | Dates | Best version | First: trades | per trade | profit | Last: trades | per trade | profit |",
         "|---|--:|---|---|--:|--:|--:|--:|--:|--:|"]
    for name, n, d0, d1, v, a, c in sorted(summary, key=lambda r: -min(r[5]["t"], r[6]["t"])):
        L.append(f"| {name} | {n} | {d0} - {d1} | {v} | {a['n']} | {a['per']:+.2f}c | {usd(a['pnl'])} | "
                 f"{c['n']} | {c['per']:+.2f}c | {usd(c['pnl'])} |")
    L += ["", "Top 12 versions per market by total profit:"] + detail
    open(os.path.join(HERE, "MARKETS.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L[:20]))


if __name__ == "__main__":
    main()
