#!/usr/bin/env python3
"""Download research data for gold:
  data/XAUT-USDT-1m.json.gz   OKX XAUT (Tether Gold) 1-minute closes  {minute start ts: close}
  data/KXGOLD15M-pyth.json.gz Kalshi gold markets with Pyth target (floor_strike) and settlement value
"""
import gzip, json, os, sys, time, urllib.request
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START, END = 1785456000, int(time.time())          # Jul 31 2026 -> now

def get(url):
    for i in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "gold-research"}), timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            err = e; time.sleep(2 ** i)
    raise RuntimeError(err)

def xaut():
    path = os.path.join(HERE, "data", "XAUT-USDT-1m.json.gz")
    out, after, n = {}, END * 1000, 0
    while True:
        d = get(f"https://www.okx.com/api/v5/market/history-candles?instId=XAUT-USDT&bar=1m&after={after}&limit=100")
        rows = d.get("data") or []
        if not rows:
            break
        for r in rows:
            if float(r[5]) > 0:                     # minute with trades
                out[int(r[0]) // 1000] = float(r[4])
        after = int(rows[-1][0]); n += 1
        if after < START * 1000:
            break
        if n % 200 == 0:
            print(f"  XAUT pages {n}, minutes {len(out)}", flush=True)
        time.sleep(0.12)
    json.dump({str(k): v for k, v in sorted(out.items())}, gzip.open(path, "wt"))
    print(f"XAUT: {len(out)} minutes with trades")

def pyth():
    path = os.path.join(HERE, "data", "KXGOLD15M-pyth.json.gz")
    found = {}
    for base in ("/markets", "/historical/markets"):
        cursor = None
        for _ in range(200):
            q = f"?series_ticker=KXGOLD15M&limit=1000" + (f"&cursor={cursor}" if cursor else "")
            d = get("https://api.elections.kalshi.com/trade-api/v2" + base + q)
            for m in d.get("markets", []):
                if m.get("floor_strike") is not None:
                    found[m["ticker"]] = {"ticker": m["ticker"], "strike": m.get("floor_strike"),
                                          "settle": m.get("expiration_value"), "result": m.get("result"),
                                          "open": m.get("open_time"), "close": m.get("close_time")}
            cursor = d.get("cursor")
            if not cursor or not d.get("markets"):
                break
            time.sleep(0.2)
    json.dump(sorted(found.values(), key=lambda m: m["close"]), gzip.open(path, "wt"))
    print(f"Kalshi gold markets with Pyth target: {len(found)}")

if __name__ == "__main__":
    pyth(); xaut()
