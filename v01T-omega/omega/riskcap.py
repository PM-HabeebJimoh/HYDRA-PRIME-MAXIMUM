"""Per-signal concentration cap.

Measured failure mode. On 2020-11-24 the book opened 12 positions in a single
minute - one in every listed alt - because all 12 respond to the SAME BTC
impulse. That is one bet held twelve times, not twelve bets. The whole 31.8%
unlevered drawdown of 2020 was produced in under four hours by this mechanism.

Independent-bet accounting measured earlier: 6 alts on one impulse behave like
1.64 independent bets; 12 alts like ~2.1. So notional must be shared across
the legs of a signal, not replicated per leg.

`cap_per_signal` keeps at most `k` legs from any single BTC impulse, choosing
the most liquid instruments (those with the highest trailing coverage), which
is the choice a real desk can make in real time.
"""
import numpy as np


def cap_per_signal(events, k):
    """events: (open, close, ret, name, signal_id). Keep <= k legs per signal."""
    keep = []
    seen = {}
    for i, e in enumerate(events):
        sid = e[4]
        n = seen.get(sid, 0)
        if n < k:
            keep.append(i)
            seen[sid] = n + 1
    return np.array(keep, dtype=np.int64)


def share_notional(events, weights, k_ref):
    """Scale each leg by 1/n_legs of its signal, so one impulse = one unit."""
    from collections import Counter
    cnt = Counter(e[4] for e in events)
    scale = np.array([1.0 / max(cnt[e[4]], 1) for e in events])
    return np.asarray(weights) * scale * k_ref
