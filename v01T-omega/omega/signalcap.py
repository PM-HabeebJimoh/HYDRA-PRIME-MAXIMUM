"""Per-signal risk budget.

Measured on 2018: the worst unlevered drawdown was 135.7% across 658 trades,
but FIVE signals out of 223 in that window produced 96.91% of it, and a single
signal produced 32.74% on its own by firing 11 legs at once.

Risk is therefore not diffuse across trades - it is concentrated in a handful
of impulses where every listed alt stops out together. Limiting how much of the
book any ONE impulse can lose is the direct fix, and it is fully causal: the
number of legs and the stop distance are both known at entry.

`budget` is the maximum fraction of equity a single signal may risk. Each leg
of a signal with `n` legs is sized so that n * leg_risk <= budget.
"""
import numpy as np
from collections import Counter


def per_signal_weights(events, budget_frac=1.0, max_legs=None):
    """Weight each leg so one signal risks at most `budget_frac` units.

    events: (open, close, ret, name, signal_id), any order.
    Returns weights aligned to `events`, plus a keep-mask if max_legs is set.
    """
    cnt = Counter(e[4] for e in events)
    w = np.empty(len(events))
    keep = np.ones(len(events), dtype=bool)
    seen = {}
    for i, e in enumerate(events):
        sid = e[4]
        n = cnt[sid]
        k = seen.get(sid, 0)
        seen[sid] = k + 1
        if max_legs is not None and k >= max_legs:
            keep[i] = False
            w[i] = 0.0
            continue
        eff = min(n, max_legs) if max_legs is not None else n
        w[i] = budget_frac / max(eff, 1)
    return w, keep
