"""v01T indicators, exactly as specified. Causal: bar i uses only bars <= i."""
import numpy as np


def rolling_mean(x, n):
    c = np.cumsum(np.insert(x, 0, 0.0))
    out = np.full(len(x), np.nan)
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def rolling_std_pop(x, n):
    m = rolling_mean(x, n)
    c2 = np.cumsum(np.insert(x * x, 0, 0.0))
    ms = np.full(len(x), np.nan)
    ms[n - 1:] = (c2[n:] - c2[:-n]) / n
    return np.sqrt(np.maximum(ms - m * m, 0.0))


def rolling_std_samp(x, n):
    return rolling_std_pop(x, n) * np.sqrt(n / (n - 1.0))


def bb_percent(close, n=20, k=2.0):
    """BB% = (close - lower) / (upper - lower) * 100, population stdev."""
    m = rolling_mean(close, n)
    s = rolling_std_pop(close, n)
    upper, lower = m + k * s, m - k * s
    w = upper - lower
    out = np.full(len(close), np.nan)
    ok = w > 0
    out[ok] = (close[ok] - lower[ok]) / w[ok] * 100.0
    return out


def hv_ratio(close, short=5, long=20):
    """stdev(last `short` returns) / stdev(last `long` returns), sample stdev."""
    r = np.full(len(close), np.nan)
    r[1:] = np.diff(close) / close[:-1]
    rs = np.nan_to_num(r, nan=0.0)
    a = rolling_std_samp(rs, short)
    b = rolling_std_samp(rs, long)
    out = np.full(len(close), np.nan)
    ok = np.isfinite(a) & np.isfinite(b) & (b > 0)
    out[ok] = a[ok] / b[ok]
    # invalidate windows that touch the undefined first return
    out[:long + 1] = np.nan
    return out


def score_of(bb):
    s = np.full(len(bb), 72.0)
    s[bb > 90] = 85.0
    s[bb < 10] = 92.0
    s[~np.isfinite(bb)] = np.nan
    return s
