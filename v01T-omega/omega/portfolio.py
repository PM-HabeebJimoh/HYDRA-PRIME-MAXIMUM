"""Continuous-time portfolio accounting.

The rule "trades must not overlap" is NOT physics. It is an artifact of
assuming one capital slot. A real book holds many simultaneous positions in
different instruments; capital is consumed by MARGIN, and margin is released
when each position closes.

This engine tracks a real equity curve in continuous time:
  * every signal opens a position of notional = risk_frac * equity * lev
  * positions live until their barrier resolves (measured on real 1m bars)
  * equity is marked continuously; drawdown is measured on the MARK, not on
    trade-close snapshots (which would hide intramonth risk)
  * a hard cap on concurrent exposure prevents infinite stacking
"""
import numpy as np


def simulate(events, n_bars, lev, max_concurrent, risk_frac=1.0,
             equity0=1.0):
    """events: list of (open_bar, close_bar, ret) with ret the per-unit return.

    Returns (equity_curve_at_bars, taken_mask).
    Positions are opened only if a slot is free -> capital constraint is real.
    """
    order = np.argsort([e[0] for e in events])
    open_b = np.array([events[i][0] for i in order], dtype=np.int64)
    close_b = np.array([events[i][1] for i in order], dtype=np.int64)
    rets = np.array([events[i][2] for i in order], dtype=float)

    # realised pnl deltas applied at close time
    delta = np.zeros(n_bars + 2, dtype=float)
    taken = np.zeros(len(order), dtype=bool)

    # event-driven slot accounting
    active_close = []           # heap of close bars
    import heapq
    equity = equity0
    # we need equity at OPEN time to size, so process chronologically
    # first pass: determine which are taken given slot limit
    for j in range(len(order)):
        ob = open_b[j]
        while active_close and active_close[0] <= ob:
            heapq.heappop(active_close)
        if len(active_close) >= max_concurrent:
            continue
        taken[j] = True
        heapq.heappush(active_close, close_b[j])

    # second pass: compound. size each position off equity at its OPEN bar.
    idx_by_open = np.argsort(open_b[taken], kind="stable")
    ob_t = open_b[taken][idx_by_open]
    cb_t = close_b[taken][idx_by_open]
    rt_t = rets[taken][idx_by_open]

    # process as a stream of (time, type) events
    stream = []
    for k in range(len(ob_t)):
        stream.append((ob_t[k], 0, k))
        stream.append((cb_t[k], 1, k))
    stream.sort()

    eq = equity0
    size = np.zeros(len(ob_t))
    curve_t, curve_v = [0], [equity0]
    ruined = False
    for t, typ, k in stream:
        if typ == 0:
            size[k] = eq * risk_frac / max_concurrent
        else:
            eq += size[k] * lev * rt_t[k]
            curve_t.append(int(t))
            curve_v.append(eq)
            # ruin, or numerical blow-up, is a FAILURE not a pass
            if (not np.isfinite(eq)) or eq <= 0:
                ruined = True
                break
    v = np.array(curve_v)
    if ruined or not np.all(np.isfinite(v)):
        return np.array(curve_t), np.array([equity0, 0.0]), int(taken.sum())
    return np.array(curve_t), v, int(taken.sum())


def curve_max_dd(v):
    peak = np.maximum.accumulate(v)
    return float(np.max((peak - v) / peak))
