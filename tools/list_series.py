"""List every Kalshi 15-minute series, with how many settled markets each has and when they started."""
import json, time, urllib.request
API = "https://api.elections.kalshi.com/trade-api/v2"
def get(path):
    with urllib.request.urlopen(urllib.request.Request(API + path, headers={"User-Agent": "list"}), timeout=30) as r:
        return json.loads(r.read().decode())
series = get("/series").get("series", [])
fifteen = sorted({s["ticker"]: s for s in series if s["ticker"].upper().endswith("15M")}.values(), key=lambda s: s["ticker"])
print(f"{len(series)} series, {len(fifteen)} are 15-minute:")
for s in fifteen:
    try:
        old = get(f"/historical/markets?series_ticker={s['ticker']}&limit=1000")
        n_old = len(old.get("markets", []))
        live = get(f"/markets?series_ticker={s['ticker']}&status=settled&limit=1000")
        n_live = len(live.get("markets", []))
        closes = [m["close_time"] for m in old.get("markets", []) + live.get("markets", []) if m.get("close_time")]
        print(f"{s['ticker']:<18} {s.get('category',''):<12} {s.get('title','')[:40]:<40} archive>={n_old}{'+' if old.get('cursor') else ''} "
              f"live>={n_live}{'+' if live.get('cursor') else ''} oldest seen {min(closes) if closes else '-'}")
    except Exception as e:
        print(f"{s['ticker']:<18} error {e}")
    time.sleep(0.5)
