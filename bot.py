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

    def market(self, ticker):
        return self.request("GET", f"/markets/{ticker}").get("market", {})

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


# ------------------------------------------------------------------ trade log (TRADES.md in the repo)
LOG_FIELDS = ["closed", "ticker", "side", "contracts", "price_c", "paid", "result", "profit", "note"]


class TradeLog:
    """Keeps trades.csv (data) and TRADES.md (readable page) in the GitHub repo, via the contents API."""

    def __init__(self, token, repo, opener=None):
        self.token, self.repo = token, repo
        self.opener = opener or self._urlopen

    def _urlopen(self, method, url, body):
        req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method,
                                     headers={"Authorization": f"Bearer {self.token}",
                                              "Accept": "application/vnd.github+json",
                                              "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode() or "{}")

    def _get(self, path):
        try:
            d = self.opener("GET", f"https://api.github.com/repos/{self.repo}/contents/{path}", None)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "", None
            raise
        return base64.b64decode(d.get("content", "")).decode(), d.get("sha")

    def _put(self, path, text, sha, msg):
        body = {"message": msg, "content": base64.b64encode(text.encode()).decode()}
        if sha:
            body["sha"] = sha
        self.opener("PUT", f"https://api.github.com/repos/{self.repo}/contents/{path}", body)

    def add(self, row):
        for attempt in range(3):
            try:
                text, sha = self._get("trades.csv")
                rows = parse_csv(text)
                rows.append({k: str(row.get(k, "")) for k in LOG_FIELDS})
                self._put("trades.csv", to_csv(rows), sha, f"log: {row.get('result')} {row.get('ticker')}")
                _, md_sha = self._get("TRADES.md")
                self._put("TRADES.md", render_md(rows, time.time()), md_sha, "log: update TRADES.md")
                return True
            except urllib.error.HTTPError as e:
                if e.code in (409, 422) and attempt < 2:   # file changed underneath us: re-read and retry
                    continue
                log(f"(trade log update failed: {e})")
                return False
            except Exception as e:
                log(f"(trade log update failed: {e})")
                return False


def parse_csv(text):
    import csv, io
    if not text.strip():
        return []
    return [dict(r) for r in csv.DictReader(io.StringIO(text))]


def to_csv(rows):
    import csv, io
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=LOG_FIELDS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in LOG_FIELDS})
    return out.getvalue()


def money(x):
    return f"{'+' if x >= 0 else '-'}${abs(x):.2f}"


def render_md(rows, now):
    trades = [r for r in rows if r["result"] in ("won", "lost")]
    problems = [r for r in rows if r["result"] not in ("won", "lost")]

    def stats(rs):
        w = sum(r["result"] == "won" for r in rs)
        n = len(rs)
        pnl = sum(float(r["profit"] or 0) for r in rs)
        paid = sum(float(r["paid"] or 0) for r in rs)
        return n, w, n - w, (f"{w / n * 100:.0f}%" if n else "-"), money(pnl), paid

    def day(r):
        return datetime.fromtimestamp(float(r["closed"]), ET).strftime("%a %b %d")

    def when(r):
        return datetime.fromtimestamp(float(r["closed"]), ET).strftime("%b %d %I:%M %p").replace(" 0", " ")

    today = datetime.fromtimestamp(now, ET).strftime("%a %b %d")
    a, t = stats(trades), stats([r for r in trades if day(r) == today])
    L = ["# Gold bot trade log (personal test)", "",
         "> **This is a small personal experiment with $1 trades, not investment advice.** "
         "A few days of wins says little: one loss at 95c wipes out about 15 wins, and results like these "
         "can reverse at any time. Don't put in money you can't afford to lose.", "",
         f"_Updated {datetime.fromtimestamp(now, ET).strftime('%b %d, %I:%M %p').replace(' 0', ' ')} ET. "
         "Each row is one trade, added when the market settles._", "",
         "| | Trades | Won | Lost | Win rate | Profit |", "|---|--:|--:|--:|--:|--:|",
         f"| **Today** | {t[0]} | {t[1]} | {t[2]} | {t[3]} | **{t[4]}** |",
         f"| **All time** | {a[0]} | {a[1]} | {a[2]} | {a[3]} | **{a[4]}** |", ""]
    days = []
    for r in trades:
        if day(r) not in days:
            days.append(day(r))
    if len(days) > 1:
        L += ["## By day", "", "| Day | Trades | Won | Lost | Profit |", "|---|--:|--:|--:|--:|"]
        for d in reversed(days):
            s = stats([r for r in trades if day(r) == d])
            L.append(f"| {d} | {s[0]} | {s[1]} | {s[2]} | {s[4]} |")
        L.append("")
    L += ["## Trades (newest first)", "", "| Market closed (ET) | Bought | Price | Paid | Result | Profit |",
          "|---|---|--:|--:|---|--:|"]
    for r in reversed(trades):
        won = r["result"] == "won"
        L.append(f"| {when(r)} | {r['side'].upper()} x{float(r['contracts']):g} | {float(r['price_c']):.0f}c | "
                 f"${float(r['paid']):.2f} | {'Won' if won else '**Lost**'} | {money(float(r['profit']))} |")
    if not trades:
        L.append("| no trades yet | | | | | |")
    if problems:
        L += ["", "## Problems", ""]
        for r in reversed(problems[-20:]):
            L.append(f"- {when(r)} {r['ticker']}: {r['result']} - {r['note']}")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main loop
class Bot:
    def __init__(self, s, kalshi, clock=time.time, sleep=time.sleep):
        self.s, self.k, self.clock, self.sleep = s, kalshi, clock, sleep
        self.done, self.tries, self.logged = set(), {}, set()
        self.day, self.spent = None, 0.0
        self.pending = {}            # ticker -> trade waiting for the market to settle
        self.tradelog = TradeLog(s.github_token, s.github_repo) if (s.github_token and s.github_repo) else None
        self.day_pnl, self.day_w, self.day_l = 0.0, 0, 0

    def record(self, row):
        if self.tradelog:
            self.tradelog.add(row)

    def notify(self, msg, title=None):
        """Log line, plus an optional phone alert via ntfy if NTFY_TOPIC is set."""
        log(msg)
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
            self.day_pnl, self.day_w, self.day_l = 0.0, 0, 0

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
                log(f"{t}: order failed - {e}")
                if self.tries[t] == 1:
                    self.record({"closed": int(parse_ts(m["close_time"])), "ticker": t, "side": d["side"],
                                 "result": "order failed", "note": str(e)[:200]})
                if self.tries[t] >= self.s.max_tries:
                    self.done.add(t)
                continue
            filled, spent = fill_info(order, d["price"])
            if filled > 0:
                self.done.add(t)
                self.spent += spent
                log(f"BOUGHT {t}: {d['side'].upper()} {filled:g} contracts for ${spent:.2f} "
                    f"(saw {d['price']:g}c, {int(secs_left)}s left)")
                self.pending[t] = {"side": d["side"], "n": filled, "cost": spent,
                                   "close": parse_ts(m["close_time"]), "checks": 0}
            else:
                log(f"{t}: not filled (try {self.tries[t]}/{self.s.max_tries}) - {what}")
                if self.tries[t] >= self.s.max_tries:
                    self.done.add(t)
        if self.pending:
            self.check_settled()
            if self.pending:
                next_wake = min(next_wake, 30.0)
        if len(self.done) > 500:
            self.done = set(list(self.done)[-200:])
        return next_wake

    def check_settled(self):
        """Send one alert per finished trade: price paid, won or lost, profit."""
        now = self.clock()
        for t, p in list(self.pending.items()):
            if now < p["close"] + 20:
                continue
            p["checks"] += 1
            try:
                m = self.k.market(t)
            except Exception as e:
                log(f"{t}: couldn't check result yet ({e})")
                continue
            res = (m.get("result") or "").lower()
            if res not in ("yes", "no"):
                if p["checks"] >= 60:           # ~30 min with no result: stop waiting
                    log(f"{t}: no result from Kalshi after 30 min. Check the Kalshi app.")
                    self.record({"closed": int(p["close"]), "ticker": t, "side": p["side"], "contracts": p["n"],
                                 "paid": f"{p['cost']:.2f}", "result": "no result",
                                 "note": "Kalshi gave no result after 30 min; check the Kalshi app"})
                    del self.pending[t]
                continue
            won = res == p["side"]
            payout = p["n"] * 1.0 if won else 0.0
            pnl = payout - p["cost"]
            self.day_pnl += pnl
            self.day_w += won
            self.day_l += not won
            each = p["cost"] / p["n"] * 100 if p["n"] else 0
            sign = "+" if pnl >= 0 else "-"
            title = (f"{'WON' if won else 'LOST'} {sign}${abs(pnl):.2f} - {p['side'].upper()} at {each:.0f}c "
                     f"(today {self.day_w}W/{self.day_l}L, {'+' if self.day_pnl >= 0 else '-'}${abs(self.day_pnl):.2f})")
            self.notify(f"{title}. {t}: {p['side'].upper()} x{p['n']:g}, paid ${p['cost']:.2f}, settled {res.upper()}.")
            self.record({"closed": int(p["close"]), "ticker": t, "side": p["side"], "contracts": p["n"],
                         "price_c": round(each, 1), "paid": f"{p['cost']:.2f}", "result": "won" if won else "lost",
                         "profit": f"{pnl:.2f}"})
            del self.pending[t]

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
                if self.pending and self.clock() < stop_at + 600:
                    self.check_settled()
                    self.sleep(30)
                    continue
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
