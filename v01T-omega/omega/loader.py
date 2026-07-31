"""Load real 1-minute OHLCV candles. Bitfinex CSV: MTS,OPEN,CLOSE,HIGH,LOW,VOL."""
import csv, os
import numpy as np

MIN_MS = 60_000


def load_csv(path):
    ts, o, c, h, l, v = [], [], [], [], [], []
    with open(path) as fh:
        for row in csv.reader(fh):
            if len(row) < 6:
                continue
            ts.append(int(row[0])); o.append(float(row[1])); c.append(float(row[2]))
            h.append(float(row[3])); l.append(float(row[4])); v.append(float(row[5]))
    a = np.argsort(np.array(ts, dtype=np.int64))
    return dict(ts=np.array(ts, dtype=np.int64)[a], open=np.array(o)[a], close=np.array(c)[a],
                high=np.array(h)[a], low=np.array(l)[a], vol=np.array(v)[a])


def load_asset(root, asset, years):
    parts = []
    for y in years:
        p = os.path.join(root, asset, "Candles_1m", str(y), "merged.csv")
        if os.path.exists(p):
            parts.append(load_csv(p))
    if not parts:
        raise FileNotFoundError(f"{asset} {years}")
    out = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    a = np.argsort(out["ts"]); out = {k: v[a] for k, v in out.items()}
    _, idx = np.unique(out["ts"], return_index=True)
    return {k: v[idx] for k, v in out.items()}


def gap_report(d):
    """Real venue gaps. Never fabricated, never filled."""
    dt = np.diff(d["ts"])
    miss = int(((dt - MIN_MS) // MIN_MS)[dt > MIN_MS].sum())
    span = int((d["ts"][-1] - d["ts"][0]) // MIN_MS) + 1
    return dict(bars=len(d["ts"]), span_minutes=span, missing=miss,
                coverage=len(d["ts"]) / span)
