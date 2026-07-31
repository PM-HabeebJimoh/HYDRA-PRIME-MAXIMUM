"""Loader for the 13-instrument Bitfinex archive (tab-separated, MTS/O/C/H/L/V)."""
import csv, os, glob
import numpy as np


def load_symbol(root, sym, t0=None, t1=None):
    ts, o, c, h, l, v = [], [], [], [], [], []
    for p in sorted(glob.glob(os.path.join(root, sym, f"{sym}_*_USD.csv"))):
        base = os.path.basename(p)[:-4].split("_")
        try:
            fs, fe = int(base[1]), int(base[2])
        except (IndexError, ValueError):
            fs, fe = None, None
        if t0 is not None and fe is not None and fe < t0:
            continue
        if t1 is not None and fs is not None and fs > t1:
            continue
        with open(p, newline="") as fh:
            rd = csv.reader(fh, delimiter="\t")
            next(rd, None)
            for row in rd:
                if len(row) < 6:
                    continue
                try:
                    t = int(row[0])
                except ValueError:
                    continue
                if t0 is not None and t < t0:
                    continue
                if t1 is not None and t > t1:
                    continue
                ts.append(t); o.append(float(row[1])); c.append(float(row[2]))
                h.append(float(row[3])); l.append(float(row[4])); v.append(float(row[5]))
    if not ts:
        raise FileNotFoundError(f"{sym} empty for window")
    a = np.argsort(np.array(ts, dtype=np.int64))
    d = dict(ts=np.array(ts, dtype=np.int64)[a], open=np.array(o)[a],
             close=np.array(c)[a], high=np.array(h)[a], low=np.array(l)[a],
             vol=np.array(v)[a])
    _, idx = np.unique(d["ts"], return_index=True)
    return {k: val[idx] for k, val in d.items()}
