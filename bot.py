#!/usr/bin/env python3
"""Kalshi gold bot for the cloud (Railway or any server that runs Python all day).

Rule (from the backtest): in the last 3 minutes before a 15-minute gold market closes,
if the favorite's price is between 88c and 97c, buy it once and hold to settlement.

Starts in PAPER mode (it only logs what it would buy). Set LIVE=true to trade for real.
All settings come from environment variables, so nothing secret lives in the code.
"""
import base64
import json
import math
import os
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

API = "https://api.elections.kalshi.com/trade-api/v2"
ET = ZoneInfo("America/New_York")


def env(name, default=None):
    v = os.environ.get(name)
    return default if v is None or v.strip() == "" else v.strip()


class Settings:
    def __init__(self, e=env):
        self.live = str(e("LIVE", "false")).lower() in ("1", "true", "yes", "on")
        self.series = e("SERIES", "KXGOLD15M")
        self.low = float(e("BAND_LOW", "88"))            # cents
        self.high = float(e("BAND_HIGH", "97"))          # cents
        self.start_seconds = int(e("START_SECONDS", "180"))
        self.dollars = float(e("DOLLARS_PER_TRADE", "2"))
        self.daily_limit = float(e("DAILY_LIMIT", "20"))  # dollars; 0 = no limit
        self.slip = float(e("SLIPPAGE_CENTS", "1"))       # may pay up to this much above the ask seen
        self.poll = float(e("POLL_SECONDS", "3"))
        self.max_tries = int(e("MAX_TRIES_PER_MARKET", "3"))
        self.key_id = e("KALSHI_API_KEY_ID")
        self.private_key = (e("KALSHI_PRIVATE_KEY") or "").replace("\\n", "\n")
        self.ntfy_topic = e("NTFY_TOPIC")                 # optional phone alerts via ntfy.sh
        self.github_token = e("GITHUB_TOKEN")             # set by GitHub Actions: alerts as GitHub issues
        self.github_repo = e("GITHUB_REPOSITORY")
        self.run_minutes = float(e("RUN_MINUTES", "0"))   # stop after this long (0 = run forever)
        if not (0 < self.low <= self.high < 100):
            raise ValueError("BAND_LOW/BAND_HIGH must be like 88 and 97")
        if self.dollars < 0.01:
            raise ValueError("DOLLARS_PER_TRADE must be above 0")
        if self.live and not (self.key_id and self.private_key):
            raise ValueError("LIVE=true needs KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY")


def log(msg):
    print(f"{datetime.now(ET):%Y-%m-%d %H:%M:%S} ET  {msg}", flush=True)


# ------------------------------------------------------------------ Kalshi client
class Kalshi:
    def __init__(self, key_id=None, private_key_pem=None, base=API, opener=None):
        self.base, self.key_id = base, key_id
        self._key = None
        if private_key_pem:
            from cryptography.hazmat.primitives import serialization
            self._key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
        self.opener = opener or self._urlopen

    def sign(self, method, path, ts_ms):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.asymmetric import ed25519
        msg = f"{ts_ms}{method}{urllib.parse.urlparse(self.base).path}{path}".encode()
        if isinstance(self._key, ed25519.Ed25519PrivateKey):   # Kalshi's default key type: signs the message itself
            return base64.b64encode(self._key.sign(msg)).decode()
        sig = self._key.sign(msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                              salt_length=padding.PSS.DIGEST_LENGTH), hashes.SHA256())
        return base64.b64encode(sig).decode()

    @staticmethod
    def _urlopen(method, url, headers, body):
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode() or "{}")

    def request(self, method, path, params=None, body=None, auth=False):
        url = self.base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        headers = {"Accept": "application/json", "User-Agent": "kalshi-gold-cloud-bot/1.0"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if auth:
            ts = str(int(time.time() * 1000))
            headers.update({"KALSHI-ACCESS-KEY": self.key_id, "KALSHI-ACCESS-TIMESTAMP": ts,
                            "KALSHI-ACCESS-SIGNATURE": self.sign(method, path, ts)})
        for attempt in range(4):
            try:
                return self.opener(method, url, headers, data)
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    time.sleep(2 ** attempt)
                    continue
                detail = ""
                try:
                    detail = e.read().decode()[:300]
                except Exception:
                    pass
                raise RuntimeError(f"Kalshi {method} {path} -> {e.code} {detail}") from None
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt == 3:
                    raise RuntimeError(f"network error: {e}") from None
                time.sleep(2 ** attempt)
        raise RuntimeError(f"Kalshi {method} {path}: still rate limited")

    def open_markets(self, series):
        return self.request("GET", "/markets", {"series_ticker": series, "status": "open", "limit": 100}).get("markets", [])

    def fills_since(self, ts):
        out, cursor = [], None
        for _ in range(20):
            p = {"min_ts": int(ts), "limit": 200}
            if cursor:
                p["cursor"] = cursor
            d = self.request("GET", "/portfolio/fills", p, auth=True)
            out += d.get("fills", [])
            cursor = d.get("cursor")
            if not cursor or not d.get("fills"):
                break
        return out

    def balance(self):
        return self.request("GET", "/portfolio/balance", auth=True)

    def buy(self, ticker, side, count, limit_cents):
        """Buy `count` contracts of `side` paying at most `limit_cents` each (immediate-or-cancel).

        Kalshi's V2 order endpoint only quotes the YES leg: "bid" buys YES, "ask" sells YES.
        Buying NO at up to L cents is the same as selling YES at L' = 100 - L cents or more.
        Returns {fill_count_fp, taker_fill_cost_dollars, taker_fees_dollars} for the side bought.
        """
        if side == "yes":
            v2_side, yes_price = "bid", limit_cents
        else:
            v2_side, yes_price = "ask", 100 - limit_cents
        body = {"ticker": ticker, "side": v2_side, "count": f"{int(count)}.00",
                "price": f"{yes_price / 100:.4f}", "time_in_force": "immediate_or_cancel",
                "self_trade_prevention_type": "taker_at_cross", "client_order_id": str(uuid.uuid4())}
        r = self.request("POST", "/portfolio/events/orders", body=body, auth=True)
        filled = float(r.get("fill_count") or 0)
        out = {"order_id": r.get("order_id"), "fill_count_fp": f"{filled:.2f}"}
        if filled > 0 and r.get("average_fill_price") not in (None, ""):
            yes_px = float(r["average_fill_price"])
            px = yes_px if side == "yes" else 1 - yes_px
            out["taker_fill_cost_dollars"] = f"{filled * px:.4f}"
            out["taker_fees_dollars"] = f"{filled * float(r.get('average_fee_paid') or 0):.4f}"
        return out


# ------------------------------------------------------------------ strategy
def dollars_to_cents(v):
    if v in (None, ""):
        return None
    return round(float(v) * 100, 2)


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def asks(m):
    """(yes_ask, no_ask) in cents; either may be None. Falls back to old whole-cent fields."""
    ya = dollars_to_cents(m.get("yes_ask_dollars"))
    na = dollars_to_cents(m.get("no_ask_dollars"))
    if ya is None and m.get("yes_ask") is not None:
        ya = float(m["yes_ask"])
    if na is None and m.get("no_ask") is not None:
        na = float(m["no_ask"])
    if na is None:
        yb = dollars_to_cents(m.get("yes_bid_dollars"))
        if yb is None and m.get("yes_bid") is not None:
            yb = float(m["yes_bid"])
        if yb:
            na = round(100 - yb, 2)
    ok = lambda p: p if p is not None and 0 < p < 100 else None
    return ok(ya), ok(na)


def decide(m, s, now):
    """What to do with one market right now: (action, details)."""
    secs_left = parse_ts(m["close_time"]) - now
    if secs_left <= 0 or secs_left > s.start_seconds:
        return "wait", {"secs_left": secs_left}
    ya, na = asks(m)
    opts = [(side, p) for side, p in (("yes", ya), ("no", na)) if p is not None]
    if not opts:
        return "skip", {"why": "no prices", "secs_left": secs_left}
    side, price = max(opts, key=lambda o: o[1])
    if not (s.low <= price <= s.high):
        return "skip", {"why": f"favorite {side.upper()} at {price:g}c is outside {s.low:g}-{s.high:g}c",
                        "secs_left": secs_left, "side": side, "price": price}
    count = int(s.dollars * 100 // price)
    if count < 1:
        return "skip", {"why": f"${s.dollars:g} can't buy one contract at {price:g}c", "secs_left": secs_left}
    limit = min(math.ceil(price + s.slip), s.high, 99)
    return "buy", {"side": side, "price": price, "count": count, "limit": limit, "secs_left": secs_left}


def fill_info(order, fallback_price):
    """(contracts filled, dollars spent incl. fees) from Kalshi's order reply."""
    def num(*keys):
        for k in keys:
            if order.get(k) not in (None, ""):
                return float(order[k])
        return None
    filled = num("fill_count_fp", "fill_count")
    if filled is None:
        filled = 0.0
    cost = num("taker_fill_cost_dollars")
    fees = num("taker_fees_dollars") or 0.0
    if cost is None:
        cost = filled * fallback_price / 100
    return filled, cost + fees


# ------------------------------------------------------------------ main loop
class Bot:
    def __init__(self, s, kalshi, clock=time.time, sleep=time.sleep):
        self.s, self.k, self.clock, self.sleep = s, kalshi, clock, sleep
        self.done, self.tries, self.logged = set(), {}, set()
        self.day, self.spent = None, 0.0

    def notify(self, msg, title=None):
        log(msg)
        if self.s.github_token and self.s.github_repo:
            try:
                body = json.dumps({"title": (title or msg)[:120], "body": msg}).encode()
                req = urllib.request.Request(f"https://api.github.com/repos/{self.s.github_repo}/issues", data=body,
                                             method="POST", headers={"Authorization": f"Bearer {self.s.github_token}",
                                                                     "Accept": "application/vnd.github+json",
                                                                     "Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=10).close()
            except Exception as e:
                log(f"(GitHub alert failed: {e})")
        if self.s.ntfy_topic:
            try:
                req = urllib.request.Request(f"https://ntfy.sh/{self.s.ntfy_topic}", data=msg.encode(), method="POST")
                urllib.request.urlopen(req, timeout=10).close()
            except Exception as e:
                log(f"(phone alert failed: {e})")

    def load_today(self):
        """Count today's buys already on Kalshi, so restarts don't reset the daily limit or re-buy."""
        start = datetime.fromtimestamp(self.clock(), ET).replace(hour=0, minute=0, second=0, microsecond=0)
        self.roll_day()
        spent = 0.0
        for f in self.k.fills_since(start.timestamp()):
            if f.get("action", "buy") != "buy" or not str(f.get("ticker", "")).startswith(self.s.series):
                continue
            n = float(f.get("count_fp") or f.get("count") or 0)
            side = f.get("side", "yes")
            px = f.get(f"{side}_price_dollars")
            px = float(px) if px not in (None, "") else float(f.get(f"{side}_price") or 0) / 100
            spent += n * px
            self.done.add(f["ticker"])
        self.spent = spent
        log(f"Already spent today on {self.s.series}: ${spent:.2f} ({len(self.done)} markets)")

    def roll_day(self):
        today = datetime.fromtimestamp(self.clock(), ET).date()
        if today != self.day:
            if self.day is not None:
                log(f"New day. Spent ${self.spent:.2f} yesterday.")
            self.day, self.spent = today, 0.0

    def step(self):
        """One pass. Returns how long to sleep before the next pass."""
        self.roll_day()
        now = self.clock()
        markets = self.k.open_markets(self.s.series)
        next_wake = 60.0
        for m in markets:
            t = m.get("ticker")
            if not t or t in self.done or not m.get("close_time"):
                continue
            action, d = decide(m, self.s, now)
            secs_left = d.get("secs_left", 0)
            if action == "wait":
                if secs_left > 0:
                    next_wake = min(next_wake, max(1.0, secs_left - self.s.start_seconds))
                continue
            next_wake = min(next_wake, self.s.poll)
            if action == "skip":
                key = (t, d.get("why", "")[:20])
                if key not in self.logged:
                    self.logged.add(key)
                    log(f"{t}: {int(secs_left)}s left, no buy - {d['why']}")
                continue
            cost_est = d["count"] * d["limit"] / 100
            if self.s.daily_limit > 0 and self.spent + cost_est > self.s.daily_limit:
                key = (t, "limit")
                if key not in self.logged:
                    self.logged.add(key)
                    log(f"{t}: would buy but daily limit ${self.s.daily_limit:g} reached (spent ${self.spent:.2f})")
                continue
            what = f"{d['side'].upper()} x{d['count']} at {d['price']:g}c (limit {d['limit']}c), {int(secs_left)}s left"
            if not self.s.live:
                self.done.add(t)
                self.spent += d["count"] * d["price"] / 100
                self.notify(f"PAPER {t}: would buy {what}")
                continue
            self.tries[t] = self.tries.get(t, 0) + 1
            try:
                order = self.k.buy(t, d["side"], d["count"], d["limit"])
            except RuntimeError as e:
                if self.tries[t] == 1:
                    self.notify(f"{t}: order failed - {e}", title=f"Order FAILED on {t}")
                else:
                    log(f"{t}: order failed - {e}")
                if self.tries[t] >= self.s.max_tries:
                    self.done.add(t)
                continue
            filled, spent = fill_info(order, d["price"])
            if filled > 0:
                self.done.add(t)
                self.spent += spent
                self.notify(f"BOUGHT {t}: {d['side'].upper()} {filled:g} contracts for ${spent:.2f} "
                            f"(saw {d['price']:g}c, {int(secs_left)}s left). Spent today: ${self.spent:.2f}",
                            title=f"Bought {d['side'].upper()} {t} for ${spent:.2f}")
            else:
                log(f"{t}: not filled (try {self.tries[t]}/{self.s.max_tries}) - {what}")
                if self.tries[t] >= self.s.max_tries:
                    self.done.add(t)
        if len(self.done) > 500:
            self.done = set(list(self.done)[-200:])
        return next_wake

    def run(self):
        s = self.s
        mode = "LIVE - real orders" if s.live else "PAPER - no real orders"
        log(f"Gold bot starting ({mode}). {s.series}: favorite at {s.low:g}-{s.high:g}c in the last "
            f"{s.start_seconds}s, ${s.dollars:g} per trade, daily limit "
            + (f"${s.daily_limit:g}" if s.daily_limit > 0 else "none") + ".")
        if s.key_id and s.private_key:
            try:
                b = self.k.balance()
                bal = b.get("balance_dollars") or (b.get("balance", 0) / 100)
                log(f"Kalshi key works. Balance: ${float(bal):.2f}")
            except Exception as e:
                if s.live:
                    raise SystemExit(f"Kalshi key check failed: {e}")
                log(f"(Key check failed, fine in paper mode: {e})")
        if s.live:
            try:
                self.load_today()
            except Exception as e:
                raise SystemExit(f"Couldn't read today's trades from Kalshi: {e}")
        stop_at = self.clock() + s.run_minutes * 60 if s.run_minutes > 0 else None
        while True:
            if stop_at and self.clock() >= stop_at:
                log(f"Ran {s.run_minutes:g} minutes, stopping. Spent today: ${self.spent:.2f}")
                return
            try:
                wait = self.step()
            except Exception as e:
                log(f"error: {e} - retrying in 10s")
                wait = 10
            if stop_at:
                wait = min(wait, max(0.0, stop_at - self.clock()))
            self.sleep(max(0.5, wait))


def main():
    try:
        s = Settings()
    except ValueError as e:
        print(f"Setting problem: {e}", file=sys.stderr)
        return 2
    Bot(s, Kalshi(s.key_id, s.private_key or None)).run()


if __name__ == "__main__":
    sys.exit(main())
