#!/usr/bin/env python3
"""Distance-and-speed backtest for any 15-minute market that has a free Coinbase price.

  python tools/distance_backtest.py --series KXBTC15M --product BTC-USD

Rule: at N..1 minutes before close, buy the favorite (1 contract at the ask, taker fee) the first time its
price is in the band AND the Coinbase price has moved toward the favorite's side since the market opened
AND z = |move| / (typical 1-minute move * sqrt(minutes left)) >= the cutoff. "no check" = band only.
The market's history is split in time: first 60% / last 40%; a version should work in both.
Writes results/DISTANCE-<series>.md and caches prices in data/<product>-1m.json.gz.
"""
import argparse
import gzip
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import paxg_backtest as pb  # noqa: E402  (price_at, speed, simulate, stats, fee_c, get)

ET = ZoneInfo("America/New_York")
BANDS = [(60, 90), (70, 95), (75, 90), (80, 90), (85, 95), (90, 95)]
CUTS = [None, 0, 1, 1.5, 2]          # None = no check at all, 0 = direction only


def download(product, start, end):
    path = os.path.join(HERE, "data", f"{product}-1m.json.gz")
    try:
        have = {int(k): v for k, v in json.load(gzip.open(path, "rt")).items()}
    except (OSError, ValueError):
        have = {}
    iso = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    t, n = start - start % 60, 0
    while t < end:
        t2 = min(end, t + 300 * 60)
        if not any(k in have for k in range(t, t2, 60 * 30)):
            for ts, lo, hi, op, cl, vol in pb.get(f"https://api.exchange.coinbase.com/products/{product}/candles"
                                                  f"?granularity=60&start={iso(t)}&end={iso(t2)}"):
                have[int(ts)] = cl
            n += 1
            time.sleep(0.25)
            if n % 100 == 0:
                print(f"  {product}: {n} requests, {len(have)} candles", flush=True)
        t = t2
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump({str(k): v for k, v in sorted(have.items())}, gzip.open(path, "wt"))
    return have


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", required=True)
    ap.add_argument("--product", required=True, help="Coinbase product, e.g. BTC-USD")
    a = ap.parse_args()
    ms = sorted(json.load(gzip.open(os.path.join(HERE, "data", f"{a.series}-full.json.gz"), "rt")), key=lambda m: m["close"])
    ms = [m for m in ms if m.get("c")]
    print(f"{a.series}: {len(ms)} markets; downloading {a.product} ...", flush=True)
    px = download(a.product, ms[0]["close"] - 3600, ms[-1]["close"])
    print(f"{a.product}: {len(px)} candles")
    cut = ms[int(len(ms) * 0.6)]["close"]
    first, last = [m for m in ms if m["close"] < cut], [m for m in ms if m["close"] >= cut]
    d = lambda t: datetime.fromtimestamp(t, ET).strftime("%b %d")
    rows = []
    for b in BANDS:
        for w in (3, 2):
            for z in CUTS:
                agree = z is not None
                sa = pb.stats(pb.simulate(first, px, *b, w, z or 0, need_agree=agree))
                sb = pb.stats(pb.simulate(last, px, *b, w, z or 0, need_agree=agree))
                rows.append((b, w, z, sa, sb))
    usd = lambda v: f"{'+' if v >= 0 else '-'}${abs(v):.2f}"
    cell = lambda s: f"{s['n']} | {s['wr'] * 100:.1f}% | {s['need'] * 100:.1f}% | {s['per']:+.2f}c | {usd(s['pnl'])}"
    zl = lambda z: "no check" if z is None else ("direction only" if z == 0 else f"z >= {z:g}")
    L = [f"# Distance filter: {a.series} with Coinbase {a.product}", "",
         f"_{len(ms)} markets, {d(ms[0]['close'])} - {d(ms[-1]['close'])}; first part to {d(cut)}. 1 contract per trade "
         "at the ask, Kalshi taker fee included._", "",
         "| Band | Start | Check | First: trades | won | need | per trade | profit | Last: trades | won | need | per trade | profit |",
         "|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|"]
    for b, w, z, sa, sb in sorted(rows, key=lambda r: -min(r[3]["t"], r[4]["t"])):
        L.append(f"| {b[0]}-{b[1]}c | {w} min | {zl(z)} | {cell(sa)} | {cell(sb)} |")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump([{"band": b, "window": w, "z": z, "first": sa, "last": sb} for b, w, z, sa, sb in rows],
              open(os.path.join(HERE, "results", f"DISTANCE-{a.series}.json"), "w"))
    open(os.path.join(HERE, "results", f"DISTANCE-{a.series}.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L[:16]))


if __name__ == "__main__":
    main()
