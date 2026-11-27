"""One-off: which free gold-token minute feeds exist, and how complete are they (one recent weekday)?"""
import json, time, urllib.request
S, E = 1795617600, 1795617600 + 86400          # Nov 25 2026 00:00-24:00 UTC (a weekday)
def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "probe"}), timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return f"ERR {getattr(e, 'code', '')} {e}"
def report(name, minutes):
    if isinstance(minutes, str):
        print(f"{name:34} {minutes[:120]}"); return
    print(f"{name:34} {len(set(minutes))} of 1440 minutes have trades")
# Bitfinex
for sym in ("tPAXG:USD", "tXAUT:USD", "tXAUTF0:USTF0"):
    d = get(f"https://api-pub.bitfinex.com/v2/candles/trade:1m:{sym}/hist?start={S*1000}&end={E*1000}&limit=10000&sort=1")
    report(f"Bitfinex {sym}", d if isinstance(d, str) else [r[0] // 60000 for r in d])
    time.sleep(1)
# OKX (history candles, 100 per page)
for inst in ("PAXG-USDT", "XAUT-USDT"):
    mins, after = [], E * 1000
    for _ in range(16):
        d = get(f"https://www.okx.com/api/v5/market/history-candles?instId={inst}&bar=1m&after={after}&limit=100")
        if isinstance(d, str) or not d.get("data"):
            mins = d if isinstance(d, str) else mins; break
        rows = d["data"]; mins += [int(r[0]) // 60000 for r in rows if int(r[0]) >= S * 1000 and float(r[5]) > 0]
        after = int(rows[-1][0])
        if after < S * 1000: break
        time.sleep(0.3)
    report(f"OKX {inst}", mins)
# Coinbase PAXG (reference)
mins = []
for t in range(S, E, 18000):
    from datetime import datetime, timezone
    iso = lambda x: datetime.fromtimestamp(x, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    d = get(f"https://api.exchange.coinbase.com/products/PAXG-USD/candles?granularity=60&start={iso(t)}&end={iso(min(E, t + 18000))}")
    mins += [] if isinstance(d, str) else [r[0] // 60 for r in d]
    time.sleep(0.4)
report("Coinbase PAXG-USD", mins)
# Kalshi: does each gold market record the Pyth price at open (strike) and close?
d = get("https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXGOLD15M&status=settled&limit=3")
for m in ([] if isinstance(d, str) else d.get("markets", [])):
    print("Kalshi", m["ticker"], {k: m.get(k) for k in ("floor_strike", "expiration_value", "result", "open_time", "close_time")})
