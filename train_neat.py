#!/usr/bin/env python3
"""Evolve a trading brain for Kalshi 15-minute gold markets with ES-HyperNEAT (kii-rin/eshyperneat-trainer).

Decision: once per market, 2 minutes before close. The brain sees the market's recent price path and
answers "buy YES", "buy NO" or "skip". Each buy is 1 contract at the ask, Kalshi taker fee included,
held to settlement.

To avoid fooling ourselves, the data is split by time:
    train      (oldest ~60%)  evolution uses only this
    validation (next ~20%)    picks which generation's champion to keep
    test       (newest ~20%)  looked at once, at the end, to judge the final brain
The final brain is compared with the simple rule (favorite 90-95c, steady) on the same test markets.

Usage: python train_neat.py --data data/KXGOLD15M-full.json.gz --neat ../eshyperneat-trainer --gens 80
"""
import argparse
import gzip
import json
import math
import os
import random
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np

ET = ZoneInfo("America/New_York")
DECIDE_AT = 2   # minutes before close

FEATURES = ["yes mid", "mid - 1 min ago", "mid - 3 min ago", "mid - 8 min ago", "mid - 12 min ago",
            "range last 4 min", "spread", "log volume last 3 min", "log volume last 13 min",
            "hour sin", "hour cos"]


def fee_c(n, p):
    return math.ceil(round(0.07 * n * (p / 100) * (1 - p / 100) * 100, 6))


def features(m):
    """Feature vector known at DECIDE_AT minutes before close, plus (yes_ask, no_ask). None if data is missing."""
    by = {k: (b, a, v) for k, b, a, v in m.get("c", [])}
    if DECIDE_AT not in by:
        return None
    b2, a2, _ = by[DECIDE_AT]
    if b2 is None or a2 is None or not (0 < a2 < 100) or not (0 < b2 < 100):
        return None

    def mid(k):
        # last known mid at or before k minutes left (going back in time)
        for j in range(k, 16):
            if j in by and by[j][0] is not None and by[j][1] is not None:
                return (by[j][0] + by[j][1]) / 200
        return (b2 + a2) / 200

    m2 = (b2 + a2) / 200
    recent = [mid(k) for k in range(DECIDE_AT, DECIDE_AT + 4)]
    vol3 = sum(by[k][2] for k in range(DECIDE_AT, DECIDE_AT + 3) if k in by)
    vol13 = sum(by[k][2] for k in range(DECIDE_AT, 16) if k in by)
    h = datetime.fromtimestamp(m["close"], ET).hour + datetime.fromtimestamp(m["close"], ET).minute / 60
    x = [m2, m2 - mid(DECIDE_AT + 1), m2 - mid(DECIDE_AT + 3), m2 - mid(DECIDE_AT + 8), m2 - mid(DECIDE_AT + 12),
         max(recent) - min(recent), (a2 - b2) / 100, math.log1p(vol3) / 10, math.log1p(vol13) / 10,
         math.sin(2 * math.pi * h / 24), math.cos(2 * math.pi * h / 24)]
    return x, a2, round(100 - b2, 2)


def build_dataset(ms):
    X, ya, na, won_yes, close = [], [], [], [], []
    for m in ms:
        f = features(m)
        if f is None:
            continue
        x, a, n = f
        X.append(x); ya.append(a); na.append(n); won_yes.append(m["result"] == "yes"); close.append(m["close"])
    X = np.array(X, dtype=np.float64)
    ya, na = np.array(ya), np.array(na)
    won_yes = np.array(won_yes)
    # P&L in cents for 1 contract, per action
    fee = np.vectorize(lambda p: fee_c(1, p))
    pnl_yes = np.where(won_yes, 100 - ya, -ya) - fee(ya)
    pnl_no = np.where(~won_yes, 100 - na, -na) - fee(na)
    return {"X": X, "pnl_yes": pnl_yes, "pnl_no": pnl_no, "ya": ya, "na": na, "close": np.array(close)}


def split(d, a, b):
    return {k: v[a:b] for k, v in d.items()}


def normalizer(X):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    return {"offset": (-mu).tolist(), "scale": (1 / (2 * sd)).tolist()}


def norm_apply(norm, X):
    return np.clip((X + np.array(norm["offset"])) * np.array(norm["scale"]), -3, 3)


def forward(net, Xn):
    """Batch forward pass of an eshyperneat Net (one step, no memory): Xn is (B, n_in) -> (B, n_out)."""
    B = Xn.shape[0]
    V = np.zeros((net.n, B))
    V[:net.n_in] = Xn.T
    V[net.n_in] = 1.0
    for a, b, Wg in net._g:
        V[a:b] = np.tanh(Wg @ V)
    return V[net.n - net.n_out:].T


def act(out, thr=0.0):
    """outputs (B,2) -> action per market: 0 skip, 1 buy YES, 2 buy NO."""
    a = np.zeros(len(out), dtype=int)
    yes = (out[:, 0] > thr) & (out[:, 0] >= out[:, 1])
    no = (out[:, 1] > thr) & (out[:, 1] > out[:, 0])
    a[yes], a[no] = 1, 2
    return a


def score(actions, d):
    pnl = np.where(actions == 1, d["pnl_yes"], np.where(actions == 2, d["pnl_no"], 0.0))
    n = int((actions > 0).sum())
    t = pnl[actions > 0]
    # t-stat of profit per trade: rewards steady profit, not a few lucky longshots
    tstat = float(t.mean() / (t.std() + 1e-9) * math.sqrt(n)) if n > 1 else -5.0
    return {"pnl": float(pnl.sum()) / 100, "trades": n, "per": float(pnl.sum()) / n if n else 0.0,
            "win": float((t > 0).mean()) if n else 0.0, "t": tstat}


def rule_actions(d, lo=90, hi=95):
    """Simple rule at the decision point: buy the favorite if its ask is in [lo, hi]."""
    a = np.zeros(len(d["ya"]), dtype=int)
    yes_fav = d["ya"] >= d["na"]
    a[yes_fav & (d["ya"] >= lo) & (d["ya"] <= hi)] = 1
    a[~yes_fav & (d["na"] >= lo) & (d["na"] <= hi)] = 2
    return a


def export(net, norm, path, meta):
    brain = {"format": "kalshi-neat-brain-v1", "features": FEATURES, "decide_at_min": DECIDE_AT,
             "n": net.n, "n_in": net.n_in, "n_out": net.n_out, "edges": [[int(a), int(b), float(w)] for a, b, w in net.edges],
             "groups": [[int(a), int(b)] for a, b in net.groups], "norm": norm, "meta": meta}
    with open(path, "w") as f:
        json.dump(brain, f)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/KXGOLD15M-full.json.gz")
    ap.add_argument("--neat", default="../eshyperneat-trainer", help="path to the eshyperneat-trainer repo")
    ap.add_argument("--gens", type=int, default=80)
    ap.add_argument("--pop", type=int, default=150)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--min-trades", type=int, default=100, help="training fitness penalty below this many trades")
    ap.add_argument("--out", default="brains/gold-neat.json")
    ap.add_argument("--report", default="NEAT.md")
    a = ap.parse_args(argv)
    sys.path.insert(0, os.path.abspath(a.neat))
    from eshyperneat import DEFAULT_P, Neat, build_net, compile_cppn
    random.seed(a.seed)
    np.random.seed(a.seed)

    ms = sorted(json.load(gzip.open(a.data, "rt")), key=lambda m: m["close"])
    ms = [m for m in ms if m.get("c")]
    d = build_dataset(ms)
    N = len(d["X"])
    i1, i2 = int(N * 0.6), int(N * 0.8)
    tr, va, te = split(d, 0, i1), split(d, i1, i2), split(d, i2, N)
    norm = normalizer(tr["X"])
    for part in (tr, va, te):
        part["Xn"] = norm_apply(norm, part["X"])
    day = lambda t: datetime.fromtimestamp(t, ET).strftime("%b %d")
    print(f"{N} markets: train {day(tr['close'][0])}-{day(tr['close'][-1])} ({len(tr['X'])}), "
          f"validation {day(va['close'][0])}-{day(va['close'][-1])} ({len(va['X'])}), "
          f"test {day(te['close'][0])}-{day(te['close'][-1])} ({len(te['X'])})")

    P = dict(DEFAULT_P, pop=a.pop)
    neat = Neat(P)
    n_in, n_out = len(FEATURES), 2
    best = {"val": -math.inf}
    hist = []
    t0 = time.time()
    for gen in range(a.gens):
        nets = {}
        for i, g in enumerate(neat.pop):
            try:
                net = build_net(compile_cppn(g), n_in, n_out, P)
                s = score(act(forward(net, tr["Xn"])), tr)
                pen = max(0, a.min_trades - s["trades"]) * 0.05     # discourage "never trade" and tiny samples
                g["fit"] = s["t"] - pen
                nets[i] = net
            except Exception:
                g["fit"] = -1e9
        champ_i = max(range(len(neat.pop)), key=lambda i: neat.pop[i]["fit"])
        net = nets.get(champ_i)
        s_tr = score(act(forward(net, tr["Xn"])), tr)
        s_va = score(act(forward(net, va["Xn"])), va)
        hist.append((gen, s_tr, s_va, net.n_hid, len(net.edges)))
        if s_va["trades"] >= 30 and s_va["t"] > best["val"]:
            best = {"val": s_va["t"], "gen": gen, "net": net, "tr": s_tr, "va": s_va}
        print(f"gen {gen:3d}  train {s_tr['pnl']:+7.2f}$ {s_tr['trades']:5d} tr {s_tr['per']:+5.2f}c | "
              f"val {s_va['pnl']:+6.2f}$ {s_va['trades']:4d} tr {s_va['per']:+5.2f}c | hid {net.n_hid} "
              f"({time.time() - t0:.0f}s)", flush=True)
        neat.epoch()

    rule = {k: score(rule_actions(p), p) for k, p in (("train", tr), ("validation", va), ("test", te))}
    if "net" not in best:
        print("No champion traded enough on validation.")
        return 1
    net = best["net"]
    s_te = score(act(forward(net, te["Xn"])), te)
    meta = {"generation": best["gen"], "train": best["tr"], "validation": best["va"], "test": s_te,
            "rule_90_95": rule, "trained": datetime.now(ET).isoformat(timespec="minutes"),
            "split": {"train": [day(tr['close'][0]), day(tr['close'][-1])],
                      "validation": [day(va['close'][0]), day(va['close'][-1])],
                      "test": [day(te['close'][0]), day(te['close'][-1])]}}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    export(net, norm, a.out, meta)

    f = lambda s: f"{s['trades']} | {s['win'] * 100:.1f}% | {s['per']:+.2f}c | **{'+' if s['pnl'] >= 0 else '-'}${abs(s['pnl']):.2f}**"
    L = ["# ES-HyperNEAT gold brain", "",
         f"_Trained {meta['trained']} on {N} markets. Decision 2 minutes before close; 1 contract per trade; "
         "Kalshi taker fee included._", "",
         "Evolution only saw **train**. **Validation** picked which generation to keep (generation "
         f"{best['gen']}). **Test** is the newest data, never used for any choice: it is the honest result.", "",
         "| | Markets | Trades | Win rate | Per trade | Profit |", "|---|---|--:|--:|--:|--:|"]
    for name, part, s in (("Brain, train", tr, best["tr"]), ("Brain, validation", va, best["va"]), ("**Brain, test**", te, s_te)):
        L.append(f"| {name} | {meta['split'][name.strip('*').split(', ')[1]][0]}-{meta['split'][name.strip('*').split(', ')[1]][1]} | {f(s)} |")
    for k, s in rule.items():
        L.append(f"| Rule 90-95c, {k} | | {f(s)} |")
    L += ["", f"Brain size: {net.n_hid} hidden neurons, {len(net.edges)} links. Inputs: " + ", ".join(FEATURES) + ".", "",
          "## Champion by generation", "", "| Gen | Train profit | Train trades | Validation profit | Validation trades |",
          "|--:|--:|--:|--:|--:|"]
    for gen, s1, s2, _, _ in hist:
        L.append(f"| {gen} | {s1['pnl']:+.2f} | {s1['trades']} | {s2['pnl']:+.2f} | {s2['trades']} |")
    with open(a.report, "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L[:14]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
