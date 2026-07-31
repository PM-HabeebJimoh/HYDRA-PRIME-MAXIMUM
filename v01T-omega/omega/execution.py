"""Path-accurate barrier resolution on real 1-minute bars.

Key honesty rule: within a single 1m bar we cannot know whether the high or the
low came first. Whenever a bar touches BOTH barriers we resolve it as the
ADVERSE outcome (stop). That is the conservative bound, never the optimistic one.
"""
import numpy as np

AMBIGUOUS = "ambiguous_bar_resolved_adverse"


def resolve_long(high, low, entry, stop, target, max_bars):
    """Return (outcome, bars_held). outcome in {+1 target, -1 stop, 0 timeout}."""
    n = min(max_bars, len(high))
    for i in range(n):
        hit_s = low[i] <= stop
        hit_t = high[i] >= target
        if hit_s and hit_t:
            return -1, i + 1          # adverse-first assumption
        if hit_s:
            return -1, i + 1
        if hit_t:
            return +1, i + 1
    return 0, n


def resolve_short(high, low, entry, stop, target, max_bars):
    n = min(max_bars, len(high))
    for i in range(n):
        hit_s = high[i] >= stop
        hit_t = low[i] <= target
        if hit_s and hit_t:
            return -1, i + 1
        if hit_s:
            return -1, i + 1
        if hit_t:
            return +1, i + 1
    return 0, n
