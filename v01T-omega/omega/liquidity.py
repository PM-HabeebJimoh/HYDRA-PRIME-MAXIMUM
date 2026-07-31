"""Causal tradability gate.

An instrument is only tradable once the venue actually quotes it continuously.
Measured coverage on real Bitfinex data:

    EOSUSD: 0% of minutes before 2017-07  (the pair did not exist)
    NEOUSD: 0% of minutes before 2017-09  (the pair did not exist)
    ETHUSD: 27% in 2017-01 rising to 100% by 2017-09

Backtesting a pair before it was listed - or while it quotes 27% of minutes -
is not a strategy result, it is a data artifact. This gate requires that the
instrument had continuous quoting over a trailing window ENDING BEFORE the
signal, so it is knowable in real time and cannot peek.
"""
import numpy as np


def trailing_coverage(present, window):
    """Fraction of the trailing `window` minutes that had a real bar,
    evaluated strictly before the current bar."""
    p = present.astype(np.float64)
    c = np.cumsum(np.insert(p, 0, 0.0))
    out = np.full(len(p), np.nan)
    out[window:] = (c[window:-1] - c[:-window - 1]) / window
    return out


def tradable_mask(panel, window=1440, min_cov=0.90):
    """True where the instrument has been continuously quoted."""
    return {nm: np.nan_to_num(trailing_coverage(panel[nm]["present"], window),
                              nan=0.0) >= min_cov
            for nm in panel}
