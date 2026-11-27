#!/usr/bin/env python3
"""Gold strategy research on Kalshi 15-minute gold markets (does not touch the live bot).

Data (all in data/):
  KXGOLD15M-full.json.gz   Kalshi minute quotes (yes bid/ask, volume) for the last 15 minutes of each market
  KXGOLD15M-pyth.json.gz   each market's Pyth target (floor_strike) and settlement value
  XAUT-USDT-1m.json.gz     OKX Tether Gold 1-minute closes (live gold stand-in, ~96% of minutes trade)
  PAXG-USD-1m.json.gz      Coinbase PAXG 1-minute closes (what the live bot uses; thinner)

Every strategy trades at most once per market: 1 contract at the ask, Kalshi taker fee, held to settlement.
Periods: TRAIN Aug 1-Sep 30 (fit), VALID Oct 1-31 (choose settings), TEST Nov 1-26 (looked at once, at the end).
Writes research/RESEARCH.md.
"""
import gzip
import json
import math
import os
import random
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(HERE, "data", *p)
ts = lambda y, m, d: int(datetime(y, m, d, tzinfo=ET).timestamp())
TRAIN, VALID, TEST = (ts(2026, 8, 1), ts(2026, 10, 1)), (ts(2026, 10, 1), ts(2026, 11, 1)), (ts(2026, 11, 1), ts(2026, 12, 1))
KMAX = 14                    # decision minutes available: 14..1 minutes before close
SQ2 = math.sqrt(2)


def Phi(x):
    return 0.5 * (1 + np.vectorize(math.erf)(np.asarray(x) / SQ2))


def fee_c(p):
    p = np.asarray(p, dtype=float)
    return np.ceil(np.round(7 * p * (100 - p) / 10000, 6))


# ----------------------------------------------------------------------------- gold price series
class Series:
    """1-minute closes on a regular grid, forward-filled up to `ffill` minutes. price(t) = close of the
    latest candle that ended at or before t."""

    def __init__(self, path, ffill=5):
        raw = {int(k): v for k, v in json.load(gzip.open(path, "rt")).items()}
        self.t0 = min(raw) - min(raw) % 60
        n = (max(raw) - self.t0) // 60 + 2
        a = np.full(n, np.nan)
        for k, v in raw.items():
            a[(k - self.t0) // 60] = v
        last, age = np.nan, 10 ** 9
        for i in range(n):              # forward fill with a limit
            if np.isnan(a[i]):
                age += 1
                if age <= ffill:
                    a[i] = last
            else:
                last, age = a[i], 0
        self.a = a
        self.lr = np.diff(np.log(a), prepend=np.nan)      # 1-minute log returns

    def idx(self, t):
        return int((t - 60 - self.t0) // 60)

    def price(self, t):
        i = self.idx(t)
        return self.a[i] if 0 <= i < len(self.a) else np.nan

    def rets(self, t, minutes):
        i = self.idx(t)
        if i - minutes < 1 or i >= len(self.a):
            return None
        r = self.lr[i - minutes + 1:i + 1]
        r = r[~np.isnan(r)]
        return r if len(r) >= minutes * 0.6 else None


# ----------------------------------------------------------------------------- dataset
FEATS = ["zs", "kal_logit", "kal_mom1", "kal_mom3", "gold_mom5", "rsi", "volratio", "spread", "k"]


def build(gold_path):
    G = Series(gold_path)
    pyth = {m["ticker"]: m for m in json.load(gzip.open(D("KXGOLD15M-pyth.json.gz"), "rt"))}
    ms = sorted((m for m in json.load(gzip.open(D("KXGOLD15M-full.json.gz"), "rt")) if m.get("c")),
                key=lambda m: m["close"])
    # Pyth 15-minute log returns in time order (accurate realized volatility)
    chain = sorted(((datetime.fromisoformat(p["close"].replace("Z", "+00:00")).timestamp(),
                     math.log(float(p["settle"]) / float(p["strike"])))
                    for p in pyth.values() if p.get("settle") and p.get("strike")), key=lambda x: x[0])
    ch_t = np.array([c[0] for c in chain])
    ch_r = np.array([c[1] for c in chain])
    rows = []
    for m in ms:
        C = m["close"]
        q = {k: (b, a) for k, b, a, v in m["c"] if b is not None and a is not None}
        vol = {k: v for k, b, a, v in m["c"]}
        x_open = G.price(C - 900)
        # Pyth vol: previous 16 settled windows (before this one opened), per minute
        j = np.searchsorted(ch_t, C - 900, side="right")
        prev = ch_r[max(0, j - 16):j]
        pyth_sd = float(np.std(prev) / math.sqrt(15)) if len(prev) >= 8 else np.nan
        for k in range(KMAX, 0, -1):
            if k not in q:
                continue
            t = C - 60 * k
            b, a = q[k]
            if not (0 < a < 100 and 0 < b < 100):
                continue
            x = G.price(t)
            r30, r60, r120 = G.rets(t, 30), G.rets(t, 60), G.rets(t, 120)
            if np.isnan(x) or np.isnan(x_open) or r30 is None:
                move, rv30, rv60, ewma = np.nan, np.nan, np.nan, np.nan
            else:
                move = math.log(x / x_open)
                rv30 = max(float(np.std(r30)), 1e-5)
                rv60 = max(float(np.std(r60)), 1e-5) if r60 is not None else rv30
                if r120 is not None:
                    w = 0.94 ** np.arange(len(r120))[::-1]
                    ewma = max(math.sqrt(float(np.sum(w * r120 ** 2) / np.sum(w))), 1e-5)
                else:
                    ewma = rv30
            r5 = G.rets(t, 5)
            gold_mom5 = float(np.sum(r5)) if r5 is not None else 0.0
            r14 = G.rets(t, 14)
            if r14 is not None and len(r14):
                up, dn = r14[r14 > 0].sum(), -r14[r14 < 0].sum()
                rsi = 100 * up / (up + dn) if up + dn > 0 else 50.0
            else:
                rsi = 50.0
            mid = (a + b) / 2
            mid1 = sum(q.get(k + 1, (b, a))) / 2
            mid3 = sum(q.get(k + 3, q.get(k + 2, q.get(k + 1, (b, a))))) / 2
            rows.append({"close": C, "k": k, "yb": b, "ya": a, "na": round(100 - b, 2), "won_yes": m["result"] == "yes",
                         "move": move, "rv30": rv30, "rv60": rv60, "ewma": ewma, "pyth": pyth_sd,
                         "gold_mom5": gold_mom5, "rsi": rsi, "mid": mid, "mid1": mid1, "mid3": mid3,
                         "vol1": vol.get(k, 0.0) or 0.0, "hour": datetime.fromtimestamp(C, ET).hour})
    R = {key: np.array([r[key] for r in rows]) for key in rows[0]}
    return R, len(ms)


def zscore(R, sig_name, drift=0.0):
    sig = R[sig_name] if sig_name != "blend" else np.sqrt((np.nan_to_num(R["rv30"]) ** 2 + np.nan_to_num(R["pyth"], nan=0) ** 2) / 2)
    return (R["move"] + drift) / (sig * np.sqrt(R["k"]))


# ----------------------------------------------------------------------------- trading engine
def trade(R, mask_period, choose):
    """choose(R) -> (side array: +1 yes / -1 no / 0 none, score). Takes the earliest qualifying minute per market
    (rows are ordered 14..1 within a market). Returns per-trade P&L (cents), prices, closes."""
    side = choose(R)
    sel = mask_period & (side != 0)
    seen, pnl, price, close, won = set(), [], [], [], []
    for i in np.nonzero(sel)[0]:
        c = R["close"][i]
        if c in seen:
            continue
        seen.add(c)
        p = R["ya"][i] if side[i] > 0 else R["na"][i]
        w = R["won_yes"][i] if side[i] > 0 else not R["won_yes"][i]
        pnl.append((100 - p if w else -p) - fee_c(p))
        price.append(p); close.append(c); won.append(w)
    return {"pnl": np.array(pnl, dtype=float), "p": np.array(price, dtype=float), "close": np.array(close), "won": np.array(won)}


def stats(t, slip=0.0):
    pnl = t["pnl"] - slip
    n = len(pnl)
    if n == 0:
        return {"n": 0, "per": 0.0, "pnl": 0.0, "wr": 0.0, "need": 0.0, "t": 0.0, "dd": 0.0, "lo": 0.0, "hi": 0.0}
    eq = np.cumsum(pnl)
    dd = float(np.max(np.maximum.accumulate(np.concatenate([[0], eq])) - np.concatenate([[0], eq])))
    rng = np.random.default_rng(0)
    boots = [float(np.mean(rng.choice(pnl, n))) for _ in range(1000)]
    return {"n": n, "per": float(pnl.mean()), "pnl": float(pnl.sum()) / 100, "wr": float(t["won"].mean()),
            "need": float(np.mean(t["p"] + fee_c(t["p"]))) / 100, "t": float(pnl.mean() / (pnl.std() + 1e-9) * math.sqrt(n)),
            "dd": dd / 100, "lo": float(np.percentile(boots, 2.5)), "hi": float(np.percentile(boots, 97.5))}


def period(R, p):
    return (R["close"] >= p[0]) & (R["close"] < p[1])


# ----------------------------------------------------------------------------- strategy families
def s_live_rule(lo=70, hi=95, zmin=1.0, sig="rv30", kmax=3):
    def f(R):
        z = zscore(R, sig)
        fav_yes = R["ya"] >= R["na"]
        price = np.where(fav_yes, R["ya"], R["na"])
        agree = np.where(fav_yes, R["move"] > 0, R["move"] < 0)
        ok = (R["k"] <= kmax) & (price >= lo) & (price <= hi) & agree & (np.abs(z) >= zmin)
        return np.where(ok, np.where(fav_yes, 1, -1), 0)
    return f


def s_fair(edge=3.0, sig="rv30", kmax=3, scale=1.0, drift=None, pmin=1, pmax=99, rsi_filter=False):
    """Fair value (digital option): P(up) = Phi(scale * (move + drift) / (sigma * sqrt(minutes left))).
    Buy the side whose model probability beats its ask + fee by `edge` cents."""
    def f(R):
        d = 0.0 if drift is None else drift(R)
        p_yes = Phi(scale * zscore(R, sig, d))
        e_yes = 100 * p_yes - R["ya"] - fee_c(R["ya"])
        e_no = 100 * (1 - p_yes) - R["na"] - fee_c(R["na"])
        ok_k = (R["k"] <= kmax) & ~np.isnan(p_yes)
        buy_yes = ok_k & (e_yes >= edge) & (e_yes >= e_no) & (R["ya"] >= pmin) & (R["ya"] <= pmax)
        buy_no = ok_k & (e_no >= edge) & (e_no > e_yes) & (R["na"] >= pmin) & (R["na"] <= pmax)
        if rsi_filter:   # don't buy against strong short-term momentum (RSI 14)
            buy_yes &= R["rsi"] > 30
            buy_no &= R["rsi"] < 70
        return np.where(buy_yes, 1, np.where(buy_no, -1, 0))
    return f


def s_overreact(jump=15, zmax=0.5, kmax=5):
    """Fade a Kalshi jump that gold didn't back up: Kalshi mid moved >= jump cents in 1 minute while gold's
    distance score is still small -> buy the side that just got cheaper."""
    def f(R):
        dm = R["mid"] - R["mid1"]
        z = np.abs(zscore(R, "rv30"))
        ok = (R["k"] <= kmax) & (np.abs(dm) >= jump) & (z <= zmax) & ~np.isnan(z)
        return np.where(ok & (dm > 0), -1, np.where(ok & (dm < 0), 1, 0))
    return f


def calib_table(R, mask, bucket=5):
    """Kalshi-only calibration: win rate of the YES side by (minutes left, YES-ask bucket, 1-min Kalshi momentum sign)."""
    key = lambda i: (int(R["k"][i]), int(R["ya"][i] // bucket), int(np.sign(R["mid"][i] - R["mid1"][i])))
    tab = {}
    for i in np.nonzero(mask)[0]:
        tab.setdefault(key(i), []).append(R["won_yes"][i])
    return {k: (float(np.mean(v)), len(v)) for k, v in tab.items()}, key


def s_calib(tab, key, edge=2.0, nmin=60, kmax=14):
    def f(R):
        out = np.zeros(len(R["k"]), dtype=int)
        for i in range(len(out)):
            if R["k"][i] > kmax:
                continue
            w = tab.get(key(i))
            if not w or w[1] < nmin:
                continue
            ey = 100 * w[0] - R["ya"][i] - fee_c(R["ya"][i])
            en = 100 * (1 - w[0]) - R["na"][i] - fee_c(R["na"][i])
            out[i] = 1 if ey >= edge and ey >= en else (-1 if en >= edge else 0)
        return out
    return f


def features(R):
    z = zscore(R, "rv30")
    mid = np.clip(R["mid"], 1, 99) / 100
    X = np.column_stack([np.clip(np.nan_to_num(z), -8, 8), np.log(mid / (1 - mid)), (R["mid"] - R["mid1"]) / 10,
                         (R["mid"] - R["mid3"]) / 10, np.nan_to_num(R["gold_mom5"] / (R["rv30"] + 1e-9)) / 3,
                         (R["rsi"] - 50) / 25, np.nan_to_num(R["rv30"] / R["pyth"], nan=1.0), (R["ya"] - R["yb"]) / 5,
                         R["k"] / 10])
    return np.clip(X, -10, 10)


def fit_logit(X, y, l2=1.0, iters=400, lr=0.5):
    Xb = np.column_stack([np.ones(len(X)), X])
    w = np.zeros(Xb.shape[1])
    for _ in range(iters):            # plain gradient descent, L2 penalty
        p = 1 / (1 + np.exp(-(Xb @ w)))
        g = Xb.T @ (p - y) / len(y) + l2 * np.r_[0, w[1:]] / len(y)
        w -= lr * g
    return w


def s_logit(w, edge=3.0, kmax=5):
    def f(R):
        X = np.column_stack([np.ones(len(R["k"])), features(R)])
        p = 1 / (1 + np.exp(-(X @ w)))
        e_yes = 100 * p - R["ya"] - fee_c(R["ya"])
        e_no = 100 * (1 - p) - R["na"] - fee_c(R["na"])
        ok = (R["k"] <= kmax) & ~np.isnan(R["move"])
        return np.where(ok & (e_yes >= edge) & (e_yes >= e_no), 1, np.where(ok & (e_no >= edge) & (e_no > e_yes), -1, 0))
    return f


def fit_scale(R, mask, sig):
    """Calibrate the fair-value model on training rows: best `scale` by log-likelihood (grid)."""
    z = zscore(R, sig)
    ok = mask & ~np.isnan(z)
    y = R["won_yes"][ok]
    best = None
    for s in np.arange(0.3, 2.01, 0.05):
        p = np.clip(Phi(s * np.clip(z[ok], -8, 8)), 1e-4, 1 - 1e-4)
        ll = float(np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
        if best is None or ll > best[1]:
            best = (round(float(s), 2), ll)
    return best[0]


# ----------------------------------------------------------------------------- run
def main():
    random.seed(0)
    out = ["# Gold strategy research", ""]
    results = {}
    for gname, gpath in (("XAUT (OKX)", D("XAUT-USDT-1m.json.gz")), ("PAXG (Coinbase)", D("PAXG-USD-1m.json.gz"))):
        if not os.path.exists(gpath):
            continue
        R, nm = build(gpath)
        tr, va, te = period(R, TRAIN), period(R, VALID), period(R, TEST)
        ok = ~np.isnan(R["move"])
        print(f"{gname}: {nm} markets, {len(R['k'])} market-minutes, gold price available {ok.mean() * 100:.0f}%", flush=True)
        cands = []          # (family, label, strategy)
        # A. live rule (baseline)
        for lo, hi in ((70, 95), (80, 90)):
            for zmin in (1.0, 1.5):
                cands.append(("A. Live rule (band + distance)", f"{lo}-{hi}c, z>={zmin:g}", s_live_rule(lo, hi, zmin)))
        # B/C/D. fair value with different volatility estimates, windows, edges
        scales = {sg: fit_scale(R, tr, sg) for sg in ("rv30", "rv60", "ewma", "pyth", "blend")}
        for sg in ("rv30", "rv60", "ewma", "pyth", "blend"):
            for kmax in (3, 5, 10):
                for edge in (2, 4, 6, 8):
                    cands.append(("B. Fair value (option model)", f"vol={sg} (scale {scales[sg]}), last {kmax} min, edge>={edge}c",
                                  s_fair(edge, sg, kmax, scales[sg])))
        # momentum / mean-reversion drift overlays and RSI filter
        for name, drift in (("momentum: + last 5 min trend", lambda R: R["gold_mom5"] * R["k"] / 5),
                            ("mean reversion: - last 5 min trend", lambda R: -R["gold_mom5"] * R["k"] / 5)):
            for edge in (4, 6):
                cands.append(("C. Fair value + trend", f"{name}, last 5 min, edge>={edge}c",
                              s_fair(edge, "rv30", 5, scales["rv30"], drift=drift)))
        for edge in (4, 6):
            cands.append(("C. Fair value + trend", f"RSI filter, last 5 min, edge>={edge}c",
                          s_fair(edge, "rv30", 5, scales["rv30"], rsi_filter=True)))
        # E. Kalshi overreaction fade
        for jump in (10, 15, 25):
            for zmax in (0.3, 0.7):
                cands.append(("D. Fade Kalshi overreaction", f"jump>={jump}c in 1 min, gold z<={zmax}", s_overreact(jump, zmax)))
        # F. calibration table (Kalshi only)
        tab, key = calib_table(R, tr)
        for edge in (2, 4, 6):
            for kmax in (3, 14):
                cands.append(("E. Calibration table (Kalshi prices only)", f"edge>={edge}c, last {kmax} min", s_calib(tab, key, edge, 60, kmax)))
        # G. logistic regression
        X = features(R)
        fitmask = tr & ok & (R["k"] <= 5)
        w = fit_logit(X[fitmask], R["won_yes"][fitmask].astype(float))
        for edge in (2, 4, 6, 8):
            for kmax in (3, 5):
                cands.append(("F. Logistic regression (all features)", f"last {kmax} min, edge>={edge}c", s_logit(w, edge, kmax)))

        rows = []
        for fam, label, strat in cands:
            a, b = stats(trade(R, tr, strat)), stats(trade(R, va, strat))
            rows.append({"fam": fam, "label": label, "strat": strat, "train": a, "valid": b})
        # choose one per family on VALIDATION (needs >= 40 trades, positive train)
        chosen = []
        for fam in dict.fromkeys(r["fam"] for r in rows):
            fr = [r for r in rows if r["fam"] == fam and r["valid"]["n"] >= 40 and r["train"]["n"] >= 60 and r["train"]["per"] > 0]
            pick = max(fr, key=lambda r: r["valid"]["t"], default=None) or max(
                (r for r in rows if r["fam"] == fam), key=lambda r: r["valid"]["t"])
            pick["test"] = stats(trade(R, te, pick["strat"]))
            pick["test_slip"] = stats(trade(R, te, pick["strat"]), slip=1.0)
            chosen.append(pick)
        results[gname] = {"rows": rows, "chosen": chosen, "scales": scales, "n": nm, "avail": float(ok.mean())}
        print(f"  {len(cands)} strategies tested", flush=True)

    usd = lambda v: f"{'+' if v >= 0 else '-'}${abs(v):.2f}"
    for gname, res in results.items():
        out += [f"## Gold price from {gname}", "",
                f"_{res['n']} markets; gold price available for {res['avail'] * 100:.0f}% of market-minutes. "
                f"Train Aug 1-Sep 30 (fit), validation Oct (choose), **test Nov 1-26 (looked at once)**. "
                f"1 contract per trade, taker fee included; '+1c slip' assumes every fill is 1c worse._", "",
                "### One pick per family (chosen on validation), then the test", "",
                "| Family | Chosen settings | Train: trades, per trade | Valid: trades, per trade | **Test: trades** | **win / need** | **per trade (95% range)** | **profit** | test +1c slip | worst dip |",
                "|---|---|---|---|--:|--:|--:|--:|--:|--:|"]
        for r in res["chosen"]:
            a, b, c, cs = r["train"], r["valid"], r["test"], r["test_slip"]
            out.append(f"| {r['fam']} | {r['label']} | {a['n']}, {a['per']:+.2f}c | {b['n']}, {b['per']:+.2f}c | {c['n']} | "
                       f"{c['wr'] * 100:.1f}% / {c['need'] * 100:.1f}% | {c['per']:+.2f}c ({c['lo']:+.1f} to {c['hi']:+.1f}) | "
                       f"**{usd(c['pnl'])}** | {usd(cs['pnl'])} | ${c['dd']:.2f} |")
        out += ["", "### Every strategy on train and validation (test hidden)", "",
                "| Family | Settings | Train trades | Train per trade | Train profit | Valid trades | Valid per trade | Valid profit |",
                "|---|---|--:|--:|--:|--:|--:|--:|"]
        for r in res["rows"]:
            a, b = r["train"], r["valid"]
            out.append(f"| {r['fam']} | {r['label']} | {a['n']} | {a['per']:+.2f}c | {usd(a['pnl'])} | {b['n']} | {b['per']:+.2f}c | {usd(b['pnl'])} |")
        out.append("")
    open(os.path.join(HERE, "research", "RESEARCH.md"), "w").write("\n".join(out) + "\n")
    for gname, res in results.items():
        print(f"\n== {gname}")
        for r in res["chosen"]:
            c = r["test"]
            print(f"{r['fam'][:38]:38} {r['label'][:52]:52} valid {r['valid']['n']:4d} {r['valid']['per']:+5.2f}c | "
                  f"TEST {c['n']:4d} {c['per']:+5.2f}c ({c['lo']:+.1f}..{c['hi']:+.1f}) {usd(c['pnl'])} slip {usd(r['test_slip']['pnl'])}")


if __name__ == "__main__":
    main()
