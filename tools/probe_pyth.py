"""One-off check of Pyth endpoints for the gold price (live, at a past time, minute history)."""
import json, time, urllib.parse, urllib.request
ID = "7fd2c87083dd8fd5af2486a43f40b8e444acd77fda4e96263a53421cd079c387"   # Metal.Index.1OZGOLD/USD
T = 1795453140   # Nov 23 2026 11:59 AM ET
def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "probe"}), timeout=20) as r:
            return r.status, r.read().decode()[:700]
    except Exception as e:
        body = getattr(e, "read", lambda: b"")().decode()[:300] if hasattr(e, "read") else ""
        return getattr(e, "code", "ERR"), f"{e} {body}"
q = urllib.parse.quote
urls = [
    f"https://hermes.pyth.network/v2/updates/price/latest?ids%5B%5D={ID}&parsed=true&encoding=hex",
    f"https://hermes.pyth.network/v2/updates/price/{T}?ids%5B%5D={ID}&parsed=true&encoding=hex",
    f"https://benchmarks.pyth.network/v1/shims/tradingview/symbols?symbol={q('Metal.Index.1OZGOLD/USD')}",
    f"https://benchmarks.pyth.network/v1/shims/tradingview/symbols?symbol={q('Metal.1OZGOLD/USD')}",
    f"https://benchmarks.pyth.network/v1/shims/tradingview/history?symbol={q('Metal.Index.1OZGOLD/USD')}&resolution=1&from={T-600}&to={T}",
    f"https://benchmarks.pyth.network/v1/shims/tradingview/history?symbol={q('Metal.1OZGOLD/USD')}&resolution=1&from={T-600}&to={T}",
    f"https://benchmarks.pyth.network/v1/shims/tradingview/history?symbol={q('Metal.XAU/USD')}&resolution=1&from={T-600}&to={T}",
    f"https://benchmarks.pyth.network/v1/updates/price/{T}?ids={ID}&parsed=true",
]
for u in urls:
    s, b = get(u)
    print(f"\n### {s} {u}\n{b}")
    time.sleep(1)
