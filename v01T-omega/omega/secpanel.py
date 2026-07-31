"""Second-resolution panel from real Binance ticks.

Illiquid alts do not print every second (NEO 13.7%, QTUM 5.6% of BTC seconds).
Requiring an exact-second bar throws away most events. A real desk instead
trades against the LAST OBSERVED price, so the panel carries, for each second:

    last_px  - price of the most recent real trade at or before this second
    age      - how many seconds stale that price is

Nothing is invented: `last_px` is always an actually-executed trade price, and
`age` makes the staleness explicit so it can be gated on. Entries are rejected
when the quote is too old to be actionable.
"""
import numpy as np


def forward_fill_last(master_ts, d):
    """Return (last_price, age_seconds) on the master grid. Causal by design."""
    pos = np.searchsorted(d["ts"], master_ts, side="right") - 1
    ok = pos >= 0
    p = np.full(len(master_ts), np.nan)
    age = np.full(len(master_ts), np.inf)
    idx = pos[ok]
    p[ok] = d["close"][idx]
    age[ok] = master_ts[ok] - d["ts"][idx]
    return p, age


def build(master_ts, syms):
    out = {}
    for name, d in syms.items():
        px, age = forward_fill_last(master_ts, d)
        out[name] = dict(px=px, age=age)
    return out
