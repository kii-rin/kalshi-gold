import base64
import json
import os
import sys
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import bot  # noqa: E402

NOW = 1795453000.0


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def settings(**kw):
    vals = {"LIVE": "false", "DAILY_LIMIT": "20", "CONFIRM_CHECKS": "1"}
    vals.update({k: str(v) for k, v in kw.items()})
    return bot.Settings(lambda n, d=None: vals.get(n, d))


def mkt(ticker, secs_left, yes_ask=None, no_ask=None, yes_bid=None):
    m = {"ticker": ticker, "close_time": iso(NOW + secs_left)}
    if yes_ask is not None:
        m["yes_ask_dollars"] = f"{yes_ask / 100:.4f}"
    if no_ask is not None:
        m["no_ask_dollars"] = f"{no_ask / 100:.4f}"
    if yes_bid is not None:
        m["yes_bid_dollars"] = f"{yes_bid / 100:.4f}"
    return m


class FakeKalshi:
    def __init__(self, markets, fill=True):
        self.markets, self.fill, self.orders = markets, fill, []

    def open_markets(self, series):
        return self.markets

    def market(self, ticker):
        return next((m for m in self.markets if m["ticker"] == ticker), {"ticker": ticker})

    fills = []

    def balance(self):
        return {"balance": 5000}

    def fills_since(self, ts):
        return self.fills

    def buy(self, ticker, side, count, limit):
        self.orders.append((ticker, side, count, limit))
        if not self.fill:
            return {"status": "canceled", "fill_count_fp": "0.00"}
        return {"status": "executed", "fill_count_fp": f"{count}.00",
                "taker_fill_cost_dollars": f"{count * limit / 100:.4f}", "taker_fees_dollars": "0.0200"}


def test_decide_band_side_and_window():
    s = settings()
    assert bot.decide(mkt("A", 120, yes_ask=93, no_ask=8), s, NOW)[0] == "buy"
    a, d = bot.decide(mkt("B", 120, yes_ask=6, no_ask=95), s, NOW)
    assert a == "buy" and d["side"] == "no" and d["price"] == 95 and d["count"] == 2 and d["limit"] == 96
    assert bot.decide(mkt("C", 120, yes_ask=98.5, no_ask=2), s, NOW)[0] == "skip"     # above 97
    assert bot.decide(mkt("D", 120, yes_ask=85, no_ask=16), s, NOW)[0] == "skip"      # below 88
    assert bot.decide(mkt("E", 200, yes_ask=93, no_ask=8), s, NOW)[0] == "wait"       # more than 3 min left
    assert bot.decide(mkt("F", -5, yes_ask=93, no_ask=8), s, NOW)[0] == "wait"        # already closed
    # NO ask worked out from YES bid when missing
    a, d = bot.decide(mkt("G", 60, yes_ask=8, yes_bid=7), s, NOW)
    assert a == "buy" and d["side"] == "no" and d["price"] == 93


def test_limit_never_above_band_top():
    a, d = bot.decide(mkt("A", 60, yes_ask=96.8, no_ask=4), settings(SLIPPAGE_CENTS=2), NOW)
    assert d["limit"] == 97


def test_paper_mode_never_orders():
    k = FakeKalshi([mkt("A", 100, yes_ask=93, no_ask=8)])
    b = bot.Bot(settings(), k, clock=lambda: NOW)
    b.step()
    b.step()
    assert k.orders == [] and "A" in b.done


def test_live_buys_once_and_tracks_spend():
    k = FakeKalshi([mkt("A", 100, yes_ask=93, no_ask=8), mkt("B", 100, yes_ask=50, no_ask=51)])
    b = bot.Bot(settings(LIVE="true", KALSHI_API_KEY_ID="x", KALSHI_PRIVATE_KEY="y"), k, clock=lambda: NOW)
    b.step()
    b.step()
    assert k.orders == [("A", "yes", 2, 94)]
    assert b.spent == pytest.approx(1.88 + 0.02)


def test_unfilled_retries_then_gives_up():
    k = FakeKalshi([mkt("A", 100, yes_ask=93, no_ask=8)], fill=False)
    b = bot.Bot(settings(LIVE="true", KALSHI_API_KEY_ID="x", KALSHI_PRIVATE_KEY="y"), k, clock=lambda: NOW)
    for _ in range(5):
        b.step()
    assert len(k.orders) == 3 and "A" in b.done


def test_daily_limit():
    ms = [mkt(f"M{i}", 100, yes_ask=93, no_ask=8) for i in range(5)]
    k = FakeKalshi(ms)
    b = bot.Bot(settings(LIVE="true", KALSHI_API_KEY_ID="x", KALSHI_PRIVATE_KEY="y", DAILY_LIMIT=5), k,
                clock=lambda: NOW)
    b.step()
    assert len(k.orders) == 2        # 2 x ~$1.90 fits, a third would pass $5
    k2 = FakeKalshi(ms)
    b2 = bot.Bot(settings(LIVE="true", KALSHI_API_KEY_ID="x", KALSHI_PRIVATE_KEY="y", DAILY_LIMIT=0), k2,
                 clock=lambda: NOW)
    b2.step()
    assert len(k2.orders) == 5       # 0 = no limit


def test_sleeps_until_window_opens():
    k = FakeKalshi([mkt("A", 600, yes_ask=93, no_ask=8)])
    b = bot.Bot(settings(), k, clock=lambda: NOW)
    assert b.step() == pytest.approx(60)            # capped at 60s
    k.markets = [mkt("A", 230, yes_ask=93, no_ask=8)]
    assert b.step() == pytest.approx(50)            # wakes exactly when 180s are left
    k.markets = [mkt("A", 150, yes_ask=80, no_ask=21)]
    assert b.step() == pytest.approx(3)             # inside the window: poll every 3s


def test_signature_is_valid_rsa_pss_and_v2_order_body():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption()).decode()
    seen = {}

    def opener(method, url, headers, body):
        seen.update(method=method, url=url, headers=headers, body=json.loads(body) if body else None)
        return {"order_id": "o1", "fill_count": "2.00", "remaining_count": "0.00",
                "average_fill_price": "0.0600", "average_fee_paid": "0.0100", "ts_ms": 1}

    k = bot.Kalshi("key-123", pem, opener=opener)
    r = k.buy("KXGOLD15M-X", "no", 2, 95)
    h = seen["headers"]
    assert seen["url"].endswith("/trade-api/v2/portfolio/events/orders")
    msg = f"{h['KALSHI-ACCESS-TIMESTAMP']}POST/trade-api/v2/portfolio/events/orders".encode()
    key.public_key().verify(base64.b64decode(h["KALSHI-ACCESS-SIGNATURE"]), msg,
                            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
                            hashes.SHA256())
    b = seen["body"]
    # buying NO at <=95c == selling YES at >=5c
    assert b == {**b, "side": "ask", "price": "0.0500", "count": "2.00", "time_in_force": "immediate_or_cancel",
                 "self_trade_prevention_type": "taker_at_cross"}
    assert "action" not in b and "type" not in b
    # filled at YES 6c -> paid 94c per NO contract
    assert r["fill_count_fp"] == "2.00" and r["taker_fill_cost_dollars"] == "1.8800" and r["taker_fees_dollars"] == "0.0200"
    filled, spent = bot.fill_info(r, 95)
    assert filled == 2 and spent == pytest.approx(1.90)


def test_v2_yes_buy_and_no_fill():
    seen = {}

    def opener(method, url, headers, body):
        seen["body"] = json.loads(body)
        return {"order_id": "o2", "fill_count": "0.00", "remaining_count": "0.00", "ts_ms": 1}

    k = bot.Kalshi("k", None, opener=opener)
    k.sign = lambda *a: "sig"
    r = k.buy("T", "yes", 1, 94)
    assert seen["body"]["side"] == "bid" and seen["body"]["price"] == "0.9400" and seen["body"]["count"] == "1.00"
    assert bot.fill_info(r, 94)[0] == 0


def test_private_key_with_escaped_newlines():
    s = settings(KALSHI_PRIVATE_KEY="-----BEGIN-----\\nabc\\n-----END-----")
    assert "\n" in s.private_key and "\\n" not in s.private_key


def test_bad_settings():
    with pytest.raises(ValueError):
        settings(BAND_LOW=97, BAND_HIGH=88)
    with pytest.raises(ValueError):
        bot.Settings(lambda n, d=None: {"LIVE": "true"}.get(n, d))   # live without a key


def test_restart_counts_todays_fills_and_skips_bought_markets():
    k = FakeKalshi([mkt("KXGOLD15M-A", 100, yes_ask=93, no_ask=8), mkt("KXGOLD15M-B", 100, yes_ask=93, no_ask=8)])
    k.fills = [{"ticker": "KXGOLD15M-A", "side": "yes", "action": "buy", "count_fp": "1.00", "yes_price_dollars": "0.9300"},
               {"ticker": "KXBTC15M-Z", "side": "no", "action": "buy", "count_fp": "5.00", "no_price_dollars": "0.9000"}]
    b = bot.Bot(settings(LIVE="true", KALSHI_API_KEY_ID="x", KALSHI_PRIVATE_KEY="y", DAILY_LIMIT=1, DOLLARS_PER_TRADE=1),
                k, clock=lambda: NOW)
    b.load_today()
    assert b.spent == pytest.approx(0.93) and "KXGOLD15M-A" in b.done
    b.step()
    assert k.orders == []            # A already bought, B would pass the $1 limit


def test_run_minutes_stops():
    t = [NOW]
    k = FakeKalshi([])
    b = bot.Bot(settings(RUN_MINUTES=5), k, clock=lambda: t[0], sleep=lambda s: t.__setitem__(0, t[0] + s))
    b.run()
    assert t[0] - NOW == pytest.approx(300)


def test_one_dollar_a_day_allows_one_trade():
    ms = [mkt(f"M{i}", 100, yes_ask=93, no_ask=8) for i in range(3)]
    k = FakeKalshi(ms)
    b = bot.Bot(settings(LIVE="true", KALSHI_API_KEY_ID="x", KALSHI_PRIVATE_KEY="y", DAILY_LIMIT=1, DOLLARS_PER_TRADE=1),
                k, clock=lambda: NOW)
    b.step()
    assert len(k.orders) == 1 and k.orders[0][2] == 1


def test_ed25519_key_signature():
    from cryptography.hazmat.primitives.asymmetric import ed25519
    key = ed25519.Ed25519PrivateKey.generate()
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption()).decode()
    seen = {}

    def opener(method, url, headers, body):
        seen.update(headers=headers, url=url)
        return {"balance": 100}

    k = bot.Kalshi("key-1", pem, opener=opener)
    k.balance()
    h = seen["headers"]
    key.public_key().verify(base64.b64decode(h["KALSHI-ACCESS-SIGNATURE"]),
                            f"{h['KALSHI-ACCESS-TIMESTAMP']}GET/trade-api/v2/portfolio/balance".encode())


def test_trade_logged_when_it_settles_not_when_bought():
    rows = []
    t = [NOW]
    k = FakeKalshi([mkt("A", 100, yes_ask=93, no_ask=8)])
    k.results = {}
    k.market = lambda tk: {"ticker": tk, "result": k.results.get(tk, "")}
    b = bot.Bot(settings(LIVE="true", KALSHI_API_KEY_ID="x", KALSHI_PRIVATE_KEY="y"), k, clock=lambda: t[0])
    b.record = rows.append
    b.step()
    assert rows == [] and "A" in b.pending
    t[0] = NOW + 130
    assert b.step() <= 30 and rows == []
    k.results["A"] = "yes"
    k.markets = []
    b.step()
    r = rows[0]
    assert (r["side"], r["result"], r["paid"], r["profit"], r["price_c"]) == ("yes", "won", "1.90", "0.10", 95.0)
    assert not b.pending


def test_loss_logged():
    rows = []
    t = [NOW]
    k = FakeKalshi([mkt("A", 100, yes_ask=6, no_ask=95)])
    k.market = lambda tk: {"result": "yes"}
    b = bot.Bot(settings(LIVE="true", KALSHI_API_KEY_ID="x", KALSHI_PRIVATE_KEY="y"), k, clock=lambda: t[0])
    b.record = rows.append
    b.step()
    t[0] = NOW + 130
    k.markets = []
    b.step()
    assert rows[0]["result"] == "lost" and rows[0]["profit"] == "-1.94" and rows[0]["side"] == "no"


def test_first_failure_logged_once():
    rows = []

    class Broken(FakeKalshi):
        def buy(self, *a):
            raise RuntimeError("410 gone")
    k2 = Broken([mkt("B", 100, yes_ask=93, no_ask=8)])
    b2 = bot.Bot(settings(LIVE="true", KALSHI_API_KEY_ID="x", KALSHI_PRIVATE_KEY="y"), k2, clock=lambda: NOW)
    b2.record = rows.append
    for _ in range(3):
        b2.step()
    assert len(rows) == 1 and rows[0]["result"] == "order failed" and "410" in rows[0]["note"]


class FakeGitHub:
    def __init__(self):
        self.files, self.puts = {}, []

    def __call__(self, method, url, body):
        path = url.split("/contents/")[1]
        if method == "GET":
            if path not in self.files:
                raise bot.urllib.error.HTTPError(url, 404, "nf", {}, None)
            text, sha = self.files[path]
            return {"content": base64.b64encode(text.encode()).decode(), "sha": sha}
        if path in self.files:
            assert body.get("sha") == self.files[path][1]       # must send current sha to update
        self.puts.append(path)
        self.files[path] = (base64.b64decode(body["content"]).decode(), f"sha{len(self.puts)}")
        return {}


def test_trades_md_page():
    gh = FakeGitHub()
    log = bot.TradeLog("tok", "kii-rin/kalshi-gold", opener=gh)
    close = 1795567500   # Nov 24 2026, 7:45 PM ET
    log.add({"closed": close, "ticker": "KXGOLD15M-26NOV241945-45", "side": "yes", "contracts": 1, "price_c": 89,
             "paid": "0.89", "result": "won", "profit": "0.11"})
    log.add({"closed": close + 900, "ticker": "KXGOLD15M-26NOV242000-00", "side": "no", "contracts": 1, "price_c": 95,
             "paid": "0.95", "result": "lost", "profit": "-0.95"})
    log.add({"closed": close + 1800, "ticker": "KXGOLD15M-26NOV242015-15", "side": "yes", "result": "order failed",
             "note": "400 bad price"})
    md = gh.files["TRADES.md"][0]
    assert "| **All time** | 2 | 1 | 1 | 50% | **-$0.84** |" in md
    assert "| Nov 24 7:45 PM | YES x1 | 89c | $0.89 | Won | +$0.11 |" in md
    assert "| Nov 24 8:00 PM | NO x1 | 95c | $0.95 | **Lost** | -$0.95 |" in md
    assert md.index("8:00 PM | NO") < md.index("7:45 PM | YES")          # newest first
    assert "## Problems" in md and "400 bad price" in md
    assert len(bot.parse_csv(gh.files["trades.csv"][0])) == 3


def test_needs_two_steady_checks_and_fresh_price():
    k = FakeKalshi([mkt("A", 100, yes_ask=93, no_ask=8)])
    t = [NOW]
    b = bot.Bot(settings(LIVE="true", KALSHI_API_KEY_ID="x", KALSHI_PRIVATE_KEY="y", CONFIRM_CHECKS=2), k,
                clock=lambda: t[0])
    b.step()
    assert k.orders == []                      # first sighting: wait for a second check
    t[0] += 3
    b.step()
    assert k.orders == [("A", "yes", 2, 94)]  # steady -> buy


def test_skips_when_price_swings_between_checks():
    k = FakeKalshi([mkt("A", 100, yes_ask=4, no_ask=96)])
    t = [NOW]
    b = bot.Bot(settings(LIVE="true", KALSHI_API_KEY_ID="x", KALSHI_PRIVATE_KEY="y", CONFIRM_CHECKS=2), k,
                clock=lambda: t[0])
    b.step()                                   # NO 96 in band
    k.markets = [mkt("A", 97, yes_ask=18, no_ask=83)]
    t[0] += 3
    b.step()                                   # swung to NO 83 -> streak broken
    assert k.orders == []


def test_fresh_recheck_blocks_stale_quote():
    k = FakeKalshi([mkt("A", 100, yes_ask=4, no_ask=96)])
    k.market = lambda tk: mkt("A", 99, yes_ask=18, no_ask=83)   # live price already moved
    t = [NOW]
    b = bot.Bot(settings(LIVE="true", KALSHI_API_KEY_ID="x", KALSHI_PRIVATE_KEY="y", CONFIRM_CHECKS=2), k,
                clock=lambda: t[0])
    b.step()
    t[0] += 3
    b.step()
    assert k.orders == []
