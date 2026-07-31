"""Per-asset alignment against the BTC clock.

Global 7-way intersection throws away most of the sample because the least
liquid alt gates every other asset. Instead each alt is aligned to the BTC
minute grid independently and simply ABSENT (weight 0) when that venue has no
bar. Nothing is interpolated or invented; a missing bar is missing.
"""
import numpy as np


def align_to(master_ts, d):
    """Return (present_mask, index_into_d) on the master timestamp grid."""
    pos = np.searchsorted(d["ts"], master_ts)
    pos_c = np.clip(pos, 0, len(d["ts"]) - 1)
    present = d["ts"][pos_c] == master_ts
    return present, pos_c


def build_panel(btc, alts):
    """btc, alts: loader dicts. Master grid = BTC timestamps."""
    ts = btc["ts"]
    panel = {}
    for name, d in alts.items():
        present, ix = align_to(ts, d)
        panel[name] = dict(
            present=present,
            open=np.where(present, d["open"][ix], np.nan),
            high=np.where(present, d["high"][ix], np.nan),
            low=np.where(present, d["low"][ix], np.nan),
            close=np.where(present, d["close"][ix], np.nan),
        )
    return ts, btc["close"], panel
