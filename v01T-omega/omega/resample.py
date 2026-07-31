"""Aggregate real 1m bars into higher timeframes. No interpolation, no fill."""
import numpy as np

MIN_MS = 60_000


def resample(d, minutes):
    step = minutes * MIN_MS
    bucket = (d["ts"] // step) * step
    uniq, start = np.unique(bucket, return_index=True)
    end = np.append(start[1:], len(bucket))
    o = d["open"][start]
    c = d["close"][end - 1]
    h = np.maximum.reduceat(d["high"], start)
    l = np.minimum.reduceat(d["low"], start)
    v = np.add.reduceat(d["vol"], start)
    n = end - start
    return dict(ts=uniq, open=o, high=h, low=l, close=c, vol=v, nsub=n,
                sub_start=start, sub_end=end)
