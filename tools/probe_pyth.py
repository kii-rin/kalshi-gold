"""One-off check: does Coinbase PAXG-USD (tokenized gold) move with Kalshi's gold markets?"""
import gzip, json, time, urllib.request
from datetime import datetime, timezone
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "probe"}), timeout=20) as r:
        return json.loads(r.read().decode())
ms = json.load(gzip.open("data/KXGOLD15M.json.gz", "rt"))
ms = [m for m in ms if m["close"] > 1795000000][-300:]          # last ~3 days of markets
iso = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
closes = {}
start, end = ms[0]["close"] - 1200, ms[-1]["close"]
t = start
while t < end:                                                  # 300 candles per request
    rows = get(f"https://api.exchange.coinbase.com/products/PAXG-USD/candles?granularity=60&start={iso(t)}&end={iso(min(end, t + 18000))}")
    for ts, lo, hi, op, cl, vol in rows:
        closes[int(ts)] = cl                                    # candle start time -> close
    t += 18000
    time.sleep(0.4)
print("PAXG candles:", len(closes))
agree = total = flat = 0
for m in ms:
    o, c = closes.get(m["close"] - 900 - 60), closes.get(m["close"] - 60)   # closes of the minutes ending at open and at close
    if o is None or c is None:
        continue
    if c == o:
        flat += 1; continue
    total += 1
    agree += (c > o) == (m["result"] == "yes")
print(f"markets compared: {total}, PAXG direction matched Kalshi result: {agree} ({agree / max(1, total) * 100:.1f}%), flat: {flat}")
print("sample:", [(m["ticker"][-15:], m["result"], closes.get(m["close"] - 960), closes.get(m["close"] - 60)) for m in ms[-5:]])
