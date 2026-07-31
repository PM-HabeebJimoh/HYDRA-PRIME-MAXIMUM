"""Portfolio simulation with causal per-trade exposure weights."""
import numpy as np
import heapq


def simulate_w(events, lev, max_concurrent, weights=None, equity0=1.0):
    """events: (open_bar, close_bar, ret) sorted-agnostic.

    weights[i] scales the notional of trade i. Strictly causal - the caller
    must build weights from information available before each open.
    Returns (times, equity_curve, n_taken, taken_index).
    """
    order = np.argsort([e[0] for e in events], kind="stable")
    ob = np.array([events[i][0] for i in order], dtype=np.int64)
    cb = np.array([events[i][1] for i in order], dtype=np.int64)
    rt = np.array([events[i][2] for i in order], dtype=float)
    w = np.ones(len(order)) if weights is None else np.asarray(weights)[order]

    active = []
    taken = np.zeros(len(order), dtype=bool)
    for j in range(len(order)):
        while active and active[0] <= ob[j]:
            heapq.heappop(active)
        if len(active) >= max_concurrent:
            continue
        taken[j] = True
        heapq.heappush(active, cb[j])

    ob_t, cb_t, rt_t, w_t = ob[taken], cb[taken], rt[taken], w[taken]
    stream = []
    for k in range(len(ob_t)):
        stream.append((int(ob_t[k]), 0, k))
        stream.append((int(cb_t[k]), 1, k))
    stream.sort()

    eq = equity0
    size = np.zeros(len(ob_t))
    tvals, vvals = [0], [equity0]
    ruined = False
    for t, typ, k in stream:
        if typ == 0:
            size[k] = eq * w_t[k] / max_concurrent
        else:
            eq += size[k] * lev * rt_t[k]
            tvals.append(t)
            vvals.append(eq)
            if (not np.isfinite(eq)) or eq <= 0:
                ruined = True
                break
    v = np.array(vvals)
    if ruined or not np.all(np.isfinite(v)):
        return np.array(tvals), np.array([equity0, 0.0]), int(taken.sum()), taken
    return np.array(tvals), v, int(taken.sum()), taken


def max_dd(v):
    peak = np.maximum.accumulate(v)
    return float(np.max((peak - v) / peak))


def solve_lev(events, slots, weights, dd_cap=0.04, hi=2000.0):
    lo = 0.0
    for _ in range(50):
        mid = (lo + hi) / 2
        _, v, _, _ = simulate_w(events, mid, slots, weights)
        ok = len(v) > 10 and np.all(np.isfinite(v)) and v[-1] > 0 and max_dd(v) <= dd_cap
        if ok:
            lo = mid
        else:
            hi = mid
    return lo


def simulate_gov(events, lev, max_concurrent, weights=None, equity0=1.0,
                 dd_soft=0.02, dd_hard=0.04, floor=0.0):
    """Same as simulate_w but with a causal DRAWDOWN GOVERNOR.

    Exposure is throttled continuously as live equity falls below its running
    peak: full size above `dd_soft`, scaling linearly to `floor` at `dd_hard`.
    This uses only the realised equity curve up to the moment of entry, so it
    is implementable in real time.

    The economics: the drawdown cap is a hard constraint on the WORST path.
    With static sizing the whole year must be sized for that one path. A
    governor spends risk budget only when the book is healthy, which lets the
    average exposure be far higher for the same worst-case depth.
    """
    import heapq
    order = np.argsort([e[0] for e in events], kind="stable")
    ob = np.array([events[i][0] for i in order], dtype=np.int64)
    cb = np.array([events[i][1] for i in order], dtype=np.int64)
    rt = np.array([events[i][2] for i in order], dtype=float)
    w = np.ones(len(order)) if weights is None else np.asarray(weights)[order]

    active = []
    taken = np.zeros(len(order), dtype=bool)
    for j in range(len(order)):
        while active and active[0] <= ob[j]:
            heapq.heappop(active)
        if len(active) >= max_concurrent:
            continue
        taken[j] = True
        heapq.heappush(active, cb[j])

    ob_t, cb_t, rt_t, w_t = ob[taken], cb[taken], rt[taken], w[taken]
    stream = []
    for k in range(len(ob_t)):
        stream.append((int(ob_t[k]), 0, k))
        stream.append((int(cb_t[k]), 1, k))
    stream.sort()

    eq = equity0
    peak = equity0
    size = np.zeros(len(ob_t))
    tvals, vvals = [0], [equity0]
    ruined = False
    span = max(dd_hard - dd_soft, 1e-12)
    for t, typ, k in stream:
        if typ == 0:
            d = (peak - eq) / peak if peak > 0 else 1.0
            if d <= dd_soft:
                g = 1.0
            elif d >= dd_hard:
                g = floor
            else:
                g = floor + (1.0 - floor) * (dd_hard - d) / span
            size[k] = eq * w_t[k] * g / max_concurrent
        else:
            eq += size[k] * lev * rt_t[k]
            if eq > peak:
                peak = eq
            tvals.append(t)
            vvals.append(eq)
            if (not np.isfinite(eq)) or eq <= 0:
                ruined = True
                break
    v = np.array(vvals)
    if ruined or not np.all(np.isfinite(v)):
        return np.array(tvals), np.array([equity0, 0.0]), int(taken.sum()), taken
    return np.array(tvals), v, int(taken.sum()), taken


def solve_lev_gov(events, slots, weights, dd_cap=0.04, hi=100000.0, **kw):
    lo = 0.0
    for _ in range(60):
        mid = (lo + hi) / 2
        _, v, _, _ = simulate_gov(events, mid, slots, weights, **kw)
        ok = len(v) > 10 and np.all(np.isfinite(v)) and v[-1] > 0 and max_dd(v) <= dd_cap
        if ok:
            lo = mid
        else:
            hi = mid
    return lo
