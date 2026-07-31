"""v01T-OMEGA: BTC->alt lead-lag impulse, honest execution, non-overlapping.

Every number this module produces is measured on real 1-minute OHLCV bars.
Conservative choices, always:
  * a 1m bar touching both barriers resolves as the STOP (adverse)
  * trades strictly non-overlapping (capital cannot be reused)
  * entry at the OPEN of the bar AFTER the signal bar closes
  * round-trip cost subtracted from every trade
"""
import numpy as np
from .fastbarrier import first_touch
from .leadlag import max_drawdown


def build_trades(btc_close, alt_ohlc, ts, threshold, stop_bp, target_bp,
                 horizon_min, cost_bp):
    """alt_ohlc: dict name -> (open, high, low). Returns per-trade net returns."""
    r = np.diff(np.log(btc_close))
    s = np.sign(r) * (np.abs(r) > threshold)
    idx = np.flatnonzero(s != 0)
    idx = idx[idx + 2 < len(btc_close)]
    starts = idx + 1
    side = s[idx].astype(np.int8)

    legs = []
    for name, (O, H, L) in alt_ohlc.items():
        entry = O[starts]
        stop = entry * (1 - side * stop_bp / 1e4)
        tgt = entry * (1 + side * target_bp / 1e4)
        out, _ = first_touch(H, L, starts, entry, stop, tgt, side, horizon_min)
        legs.append(np.where(out == 1, target_bp / 1e4,
                             np.where(out == -1, -stop_bp / 1e4, 0.0)))
    basket = np.vstack(legs).mean(axis=0)

    # strictly non-overlapping in wall-clock time
    tmin = ts[starts]
    keep, last = [], -1 << 62
    for i, t in enumerate(tmin):
        if t - last >= horizon_min * 60_000:
            keep.append(i)
            last = t
    keep = np.array(keep, dtype=np.int64)
    return keep, basket[keep] - cost_bp / 1e4, tmin[keep]


def max_leverage_at_dd(net, dd_cap=0.04, hi=300.0):
    lo = 0.0
    for _ in range(80):
        mid = (lo + hi) / 2
        eq = np.cumprod(1 + mid * net)
        if not np.all(np.isfinite(eq)) or eq.min() <= 0 or max_drawdown(eq) > dd_cap:
            hi = mid
        else:
            lo = mid
    return lo


def metrics(net, months, leverage):
    eq = np.cumprod(1 + leverage * net)
    return dict(trades=int(len(net)), trades_per_month=len(net) / months,
                win_rate=float((net > 0).mean() * 100),
                ev_bp=float(net.mean() * 1e4),
                leverage=float(leverage),
                roi_month=float((eq[-1] ** (1 / months) - 1) * 100),
                max_dd=float(max_drawdown(eq) * 100))
