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
    vals = {"LIVE": "false", "DAILY_LIMIT": "20"}
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


def test_signature_is_valid_rsa_pss():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption()).decode()
    seen = {}

    def opener(method, url, headers, body):
        seen.update(method=method, url=url, headers=headers, body=json.loads(body) if body else None)
        return {"order": {"fill_count_fp": "2.00"}}

    k = bot.Kalshi("key-123", pem.replace("\n", "\\n").replace("\\n", "\n"), opener=opener)
    k.buy("KXGOLD15M-X", "no", 2, 95)
    h = seen["headers"]
    msg = f"{h['KALSHI-ACCESS-TIMESTAMP']}POST/trade-api/v2/portfolio/orders".encode()
    key.public_key().verify(base64.b64decode(h["KALSHI-ACCESS-SIGNATURE"]), msg,
                            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
                            hashes.SHA256())
    assert h["KALSHI-ACCESS-KEY"] == "key-123"
    b = seen["body"]
    assert b["side"] == "no" and b["action"] == "buy" and b["count"] == 2 and b["no_price_dollars"] == "0.9500"
    assert b["time_in_force"] == "immediate_or_cancel"


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
