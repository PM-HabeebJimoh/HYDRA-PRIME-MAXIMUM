"""BTC -> altcoin lead-lag impulse strategy on real 1-minute Bitfinex data.

Economic mechanism (first principles): BTC is the numeraire and the deepest
book in the venue. A large BTC print moves BTC immediately, but the altcoin
books requote with latency because their market makers hedge in BTC first.
The lag-1 cross-correlation is strongly asymmetric (BTC->alt >> alt->BTC),
which is the signature of a genuine causal lead, not a common factor.
"""
import numpy as np


def signals(btc_close, threshold):
    """Signal at bar t from BTC log-return over [t-1, t]. Trade opens at t+1."""
    r = np.diff(np.log(btc_close))
    s = np.sign(r) * (np.abs(r) > threshold)
    return s.astype(np.int8)


def basket_returns(btc_close, alt_closes, threshold, horizon=1):
    """Signed equal-weight basket return per signal. Strictly causal."""
    s = signals(btc_close, threshold)
    idx = np.flatnonzero(s[:-horizon] != 0)
    rows = []
    for c in alt_closes:
        lc = np.log(c)
        rows.append(lc[idx + 1 + horizon] - lc[idx + 1])
    M = np.vstack(rows) * s[idx]
    return idx, M.mean(axis=0), M


def equity_curve(per_trade_net, leverage):
    """Compound leveraged returns. Returns equity path."""
    return np.cumprod(1.0 + leverage * per_trade_net)


def max_drawdown(eq):
    peak = np.maximum.accumulate(eq)
    return float(np.max((peak - eq) / peak))
