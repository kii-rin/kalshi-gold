#!/usr/bin/env python3
"""Long gold backtest: download months of Kalshi 15-minute gold markets, test price bands, write BACKTEST.md.

Runs on GitHub Actions (which can reach Kalshi). Downloaded prices are saved in data/<series>.json.gz,
so re-runs only fetch new markets.

Rule tested: at N, N-1, ... 1 minute(s) before close, look at the favorite's ask (the price you'd pay).
The first time it is inside the band, buy $1 worth (whole contracts) and hold to settlement. Kalshi fee included.
"steady" variants also require the same side to have been the favorite at >= the band's low end one
minute earlier (a 1-minute-data stand-in for the live bot's 30-second steady rule).
"""
import argparse
import gzip
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API = "https://api.elections.kalshi.com/trade-api/v2"
ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = (4, 3, 2, 1)          # minutes before close we keep a quote for
BANDS = [(88, 97), (90, 97), (85, 95), (80, 97), (85, 97), (90, 95), (80, 99), (95, 99)]


# ------------------------------------------------------------------ download
class Api:
    def __init__(self, pause=0.15, opener=None, sleep=time.sleep):
        self.pause, self.calls, self._last, self.sleep = pause, 0, 0.0, sleep
        self.opener = opener or self._open

    @staticmethod
    def _open(url):
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "gold-backtest/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    def get(self, path, params=None):
        url = API + path + ("?" + urllib.parse.urlencode(params, safe=",") if params else "")
        for attempt in range(7):
            wait = self.pause - (time.time() - self._last)
            if wait > 0:
                self.sleep(wait)
            self._last = time.time()
            self.calls += 1
            try:
                return self.opener(url)
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    self.sleep(min(60, 2 ** (attempt + 1)))
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                self.sleep(min(60, 2 ** (attempt + 1)))
        raise RuntimeError(f"gave up on {path}")


def parse_ts(s):
    if isinstance(s, (int, float)):
        return int(s)
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def cents(o):
    """Close price of an OHLC dict in cents. Handles close_dollars, dollar strings, or whole cents."""
    if not isinstance(o, dict):
        return None
    for k in ("close_dollars", "close"):
        v = o.get(k)
        if v in (None, ""):
            continue
        if k == "close_dollars" or (isinstance(v, str) and "." in v):
            return round(float(v) * 100, 2)
        return float(v)
    return None


def list_markets(api, series, start, end):
    """Settled markets closing in [start, end], from the live and the historical (archived) lists."""
    found = {}

    def take(ms):
        for m in ms:
            r = (m.get("result") or "").lower()
            c = m.get("close_time")
            if r in ("yes", "no") and c:
                c = parse_ts(c)
                if start <= c <= end:
                    found[m["ticker"]] = {"ticker": m["ticker"], "close": c, "result": r}

    for path, extra in (("/markets", {"min_close_ts": start, "max_close_ts": end}), ("/historical/markets", {})):
        cursor, pages, oldest_seen = None, 0, None
        while pages < 400:
            p = {"series_ticker": series, "limit": 1000, **extra}
            if cursor:
                p["cursor"] = cursor
            try:
                d = api.get(path, p)
            except urllib.error.HTTPError as e:
                print(f"  {path}: HTTP {e.code}, skipping")
                break
            ms = d.get("markets", [])
            take(ms)
            pages += 1
            closes = [parse_ts(m["close_time"]) for m in ms if m.get("close_time")]
            if closes:
                oldest_seen = min(closes + ([oldest_seen] if oldest_seen else []))
            cursor = d.get("cursor")
            if not cursor or not ms:
                break
        print(f"  {path}: {pages} page(s), {len(found)} markets in range so far")
    return sorted(found.values(), key=lambda m: m["close"])


def quotes_from(candles, close):
    cs = sorted((int(c["end_period_ts"]), cents(c.get("yes_bid")), cents(c.get("yes_ask"))) for c in candles or [])
    out = []
    for k in CHECKS:
        t = close - 60 * k
        best = None
        for c in cs:
            if c[0] <= t:
                best = c
            else:
                break
        out.append([best[1], best[2]] if best and t - best[0] <= 300 else None)
    return out


def fetch_quotes(api, series, ms, cutoff):
    """Fill m['q'] = [[yes_bid, yes_ask] at 4,3,2,1 min before close]. Live markets in batches of 100."""
    live = [m for m in ms if m["close"] >= cutoff]
    old = [m for m in ms if m["close"] < cutoff]
    for i in range(0, len(live), 100):
        g = live[i:i + 100]
        try:
            d = api.get("/markets/candlesticks", {"market_tickers": ",".join(m["ticker"] for m in g),
                                                  "start_ts": g[0]["close"] - 360, "end_ts": g[-1]["close"],
                                                  "period_interval": 1})
            by = {e.get("market_ticker") or e.get("ticker"): e.get("candlesticks") for e in d.get("markets", [])}
        except urllib.error.HTTPError as e:
            print(f"  batch HTTP {e.code}; falling back to one at a time")
            by = {}
        for m in g:
            if m["ticker"] in by:
                m["q"] = quotes_from(by[m["ticker"]], m["close"])
            else:
                old.append(m)
        print(f"  live prices: {min(i + 100, len(live))}/{len(live)}")
    for j, m in enumerate(old, 1):
        p = {"start_ts": m["close"] - 360, "end_ts": m["close"], "period_interval": 1}
        d = None
        for path in (f"/historical/markets/{m['ticker']}/candlesticks",
                     f"/series/{series}/markets/{m['ticker']}/candlesticks"):
            try:
                d = api.get(path, p)
                break
            except urllib.error.HTTPError:
                continue
        m["q"] = quotes_from((d or {}).get("candlesticks"), m["close"])
        if j % 200 == 0 or j == len(old):
            print(f"  archived prices: {j}/{len(old)} ({api.calls} requests)")


def load_data(path):
    try:
        with gzip.open(path, "rt") as f:
            return {m["ticker"]: m for m in json.load(f)}
    except (OSError, ValueError):
        return {}


def save_data(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt") as f:
        json.dump(sorted(data.values(), key=lambda m: m["close"]), f, separators=(",", ":"))


# ------------------------------------------------------------------ simulate
def fee_c(n, p):
    return math.ceil(round(0.07 * n * (p / 100) * (1 - p / 100) * 100, 6))


def favorite(q):
    if not q:
        return None
    bid, ask = q
    opts = []
    if ask is not None and 0 < ask < 100:
        opts.append(("yes", ask))
    if bid is not None and 0 < bid < 100:
        opts.append(("no", round(100 - bid, 2)))
    return max(opts, key=lambda o: o[1]) if opts else None


def simulate(ms, lo, hi, window, steady=False, dollars=1.0):
    trades = []
    for m in ms:
        q = m.get("q") or [None] * len(CHECKS)
        for k in range(window, 0, -1):
            f = favorite(q[CHECKS.index(k)])
            if not f or not (lo <= f[1] <= hi):
                continue
            if steady:
                prev = favorite(q[CHECKS.index(k + 1)])
                if not prev or prev[0] != f[0] or prev[1] < lo:
                    continue
            side, p = f
            n = int(dollars * 100 // p)
            if n < 1:
                break
            cost = n * p + fee_c(n, p)
            won = side == m["result"]
            trades.append({"close": m["close"], "side": side, "p": p, "n": n, "cost": cost, "won": won,
                           "pnl": (n * 100 if won else 0) - cost})
            break
    return trades


def wilson(w, n, z=1.96):
    if not n:
        return 0.0, 1.0
    p = w / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def wilson_low(w, n):
    return wilson(w, n)[0]


def stats(tr):
    n = len(tr)
    w = sum(t["won"] for t in tr)
    cost = sum(t["cost"] for t in tr)
    pay = sum(t["n"] * 100 for t in tr)
    pnl = sum(t["pnl"] for t in tr)
    eq = peak = dd = 0
    for t in sorted(tr, key=lambda t: t["close"]):
        eq += t["pnl"]
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    be = cost / pay if pay else 0
    lo, hi = wilson(w, n)
    verdict = ("too few trades" if n < 50 else "edge looks real" if lo > be else
               "loses money" if hi < be else "below break-even, not certain" if w / n < be else "can't tell yet")
    return {"n": n, "w": w, "wr": w / n if n else 0, "be": be, "low": lo, "pnl": pnl / 100,
            "per": pnl / n if n else 0, "dd": dd / 100, "verdict": verdict}


# ------------------------------------------------------------------ report
def pct(x):
    return f"{x * 100:.1f}%"


def usd(x):
    return f"{'+' if x >= 0 else '-'}${abs(x):.2f}"


def report(ms, series, start, end, calls):
    rows = []
    for lo, hi in BANDS:
        for w in (3, 2, 1):
            for st in (False, True):
                rows.append(((lo, hi), w, st, stats(simulate(ms, lo, hi, w, st))))
    rows.sort(key=lambda r: r[3]["pnl"], reverse=True)
    d0 = datetime.fromtimestamp(start, ET).strftime("%b %d, %Y")
    d1 = datetime.fromtimestamp(end, ET).strftime("%b %d, %Y")
    priced = sum(1 for m in ms if m.get("q") and any(m["q"]))
    L = [f"# Gold backtest ({series})", "",
         f"_{len(ms)} settled 15-minute gold markets, {d0} to {d1} ({priced} with price data). "
         f"$1 per trade, Kalshi fee included, held to settlement. Generated "
         f"{datetime.now(ET).strftime('%b %d %I:%M %p').replace(' 0', ' ')} ET._", "",
         "> A backtest uses one price per minute and assumes you get that price. Real fills can be worse, "
         "especially in fast markets. Past results don't guarantee future ones.", "",
         "**How to read it:** *Need* is the win rate required to break even at those prices. *Low* is the "
         "lowest win rate the results still allow (95% confidence). If Low is above Need, the edge is "
         "probably real. *Steady* = the same side was already the favorite at or above the band one minute earlier.",
         "", "## All versions, best first", "",
         "| Band | Start | Steady | Trades | Won | Win rate | Need | Low | Profit | Per trade | Worst dip | Verdict |",
         "|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|"]
    for b, w, st, s in rows:
        L.append(f"| {b[0]}-{b[1]}c | {w} min | {'yes' if st else 'no'} | {s['n']} | {s['w']} | {pct(s['wr'])} | "
                 f"{pct(s['be'])} | {pct(s['low'])} | **{usd(s['pnl'])}** | {s['per']:.1f}c | ${s['dd']:.2f} | "
                 f"{s['verdict']} |")

    def breakdown(title, keyf, b=(88, 97), w=3, st=True):
        tr = simulate(ms, b[0], b[1], w, st)
        groups = {}
        for t in tr:
            groups.setdefault(keyf(t), []).append(t)
        out = ["", f"## {title} ({b[0]}-{b[1]}c, {w} min, steady)", "",
               "| | Trades | Won | Win rate | Profit |", "|---|--:|--:|--:|--:|"]
        for k in sorted(groups):
            s = stats(groups[k])
            out.append(f"| {k[1] if isinstance(k, tuple) else k} | {s['n']} | {s['w']} | {pct(s['wr'])} | {usd(s['pnl'])} |")
        return out

    L += breakdown("By month", lambda t: (datetime.fromtimestamp(t["close"], ET).strftime("%Y-%m"),
                                          datetime.fromtimestamp(t["close"], ET).strftime("%B %Y")))
    L += breakdown("By hour (Eastern)", lambda t: (datetime.fromtimestamp(t["close"], ET).hour,
                                                   datetime.fromtimestamp(t["close"], ET).strftime("%I %p").lstrip("0")))
    L += breakdown("By price paid", lambda t: (int(t["p"] // 3), f"{int(t['p'] // 3) * 3}-{int(t['p'] // 3) * 3 + 2}c"))
    L += ["", f"_{calls} requests to Kalshi this run._", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="KXGOLD15M")
    ap.add_argument("--start", default="2026-08-01", help="YYYY-MM-DD (Eastern)")
    ap.add_argument("--end", default="", help="YYYY-MM-DD (Eastern), default now")
    ap.add_argument("--offline", action="store_true", help="use saved data only")
    a = ap.parse_args(argv)
    start = int(datetime.strptime(a.start, "%Y-%m-%d").replace(tzinfo=ET).timestamp())
    end = (int((datetime.strptime(a.end, "%Y-%m-%d").replace(tzinfo=ET) + timedelta(days=1)).timestamp())
           if a.end else int(time.time()))
    path = os.path.join(HERE, "data", f"{a.series}.json.gz")
    data = load_data(path)
    api = Api()
    if not a.offline:
        print(f"Listing {a.series} markets ...")
        ms = list_markets(api, a.series, start, end)
        try:
            cutoff = parse_ts(api.get("/historical/cutoff").get("market_settled_ts"))
        except Exception:
            cutoff = end - 60 * 86400
        need = [m for m in ms if m["ticker"] not in data or not data[m["ticker"]].get("q")]
        print(f"{len(ms)} markets in range, {len(need)} to download (archive cutoff "
              f"{datetime.fromtimestamp(cutoff, ET):%b %d})")
        done = 0
        for i in range(0, len(need), 500):           # save as we go
            chunk = need[i:i + 500]
            fetch_quotes(api, a.series, chunk, cutoff)
            for m in chunk:
                data[m["ticker"]] = m
            save_data(path, data)
            done += len(chunk)
            print(f"saved {done}/{len(need)}")
    ms = [m for m in data.values() if start <= m["close"] <= end]
    if not ms:
        print("No markets found.")
        return 1
    md = report(sorted(ms, key=lambda m: m["close"]), a.series, start, end, api.calls)
    with open(os.path.join(HERE, "BACKTEST.md"), "w") as f:
        f.write(md)
    print(md[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
