import io
import os
import sys
import urllib.error
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import backtest as bt  # noqa: E402

C = 1795600000 - 1795600000 % 900


def cand(ts, bid, ask):
    return {"end_period_ts": ts, "yes_bid": {"close_dollars": f"{bid / 100:.4f}"},
            "yes_ask": {"close_dollars": f"{ask / 100:.4f}"}}


def mk(i, result, quotes, live):
    close = C - 900 * i
    return {"ticker": f"KXGOLD15M-{i}", "close": close, "result": result, "live": live,
            "raw": [cand(close - 60 * k, b, a) for k, (b, a) in quotes.items()]}


class Fake:
    def __init__(self, ms, cutoff):
        self.ms, self.cutoff, self.urls = ms, cutoff, []

    def __call__(self, url):
        self.urls.append(url)
        u = urllib.parse.urlparse(url)
        q = dict(urllib.parse.parse_qsl(u.query))
        path = u.path.replace("/trade-api/v2", "")
        iso = lambda t: bt.datetime.fromtimestamp(t, bt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if path == "/historical/cutoff":
            return {"market_settled_ts": iso(self.cutoff)}
        if path == "/markets":
            return {"markets": [{"ticker": m["ticker"], "close_time": iso(m["close"]), "result": m["result"]}
                                for m in self.ms if m["live"]], "cursor": ""}
        if path == "/historical/markets":
            return {"markets": [{"ticker": m["ticker"], "close_time": iso(m["close"]), "result": m["result"]}
                                for m in self.ms if not m["live"]], "cursor": ""}
        if path == "/markets/candlesticks":
            want = q["market_tickers"].split(",")
            return {"markets": [{"market_ticker": m["ticker"], "candlesticks": m["raw"]} for m in self.ms
                                if m["ticker"] in want]}
        if path.startswith("/historical/markets/") and path.endswith("/candlesticks"):
            t = path.split("/")[3]
            return {"candlesticks": next(m["raw"] for m in self.ms if m["ticker"] == t)}
        raise urllib.error.HTTPError(url, 404, "nf", {}, io.BytesIO())


def test_download_live_and_archived_then_simulate():
    ms = [mk(1, "yes", {4: (90, 91), 3: (92, 93), 2: (95, 96), 1: (98, 99)}, True),
          mk(2, "no", {4: (5, 6), 3: (8, 9), 2: (3, 4)}, True),
          mk(300, "yes", {4: (50, 51), 3: (91, 92), 2: (97, 98)}, False),      # spike: not steady at 3 min
          mk(301, "yes", {4: (2, 3), 3: (3, 4), 2: (1, 2)}, False)]           # NO fav 97, lost
    api = bt.Api(pause=0, opener=Fake(ms, cutoff=C - 900 * 100), sleep=lambda s: None)
    got = bt.list_markets(api, "KXGOLD15M", C - 900 * 400, C)
    assert [m["ticker"] for m in got] == ["KXGOLD15M-301", "KXGOLD15M-300", "KXGOLD15M-2", "KXGOLD15M-1"]
    bt.fetch_quotes(api, "KXGOLD15M", got, C - 900 * 100)
    by = {m["ticker"]: m for m in got}
    assert by["KXGOLD15M-1"]["q"] == [[90, 91], [92, 93], [95, 96], [98, 99]]
    assert by["KXGOLD15M-300"]["q"][0] == [50, 51]
    tr = bt.simulate(got, 88, 97, 3)
    assert {(t["side"], t["p"], t["won"]) for t in tr} == {("yes", 93, True), ("no", 92, True), ("yes", 92, True),
                                                          ("no", 97, False)}
    st = bt.simulate(got, 88, 97, 3, steady=True)
    assert ("yes", 92, True) not in {(t["side"], t["p"], t["won"]) for t in st}       # spike skipped
    md = bt.report(got, "KXGOLD15M", C - 900 * 400, C, api.calls)
    assert "| 88-97c | 3 min | no | 4 | 3 |" in md


def test_one_dollar_buys_one_contract_and_fee():
    m = {"ticker": "T", "close": C, "result": "yes", "q": [None, [92, 93], None, None]}
    t = bt.simulate([m], 88, 97, 3)[0]
    assert t["n"] == 1 and t["cost"] == 94 and t["pnl"] == 6
