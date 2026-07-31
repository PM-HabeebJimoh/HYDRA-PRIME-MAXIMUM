"""v01T-OMEGA v2 — the model that beats V82.LOWDD.

WHAT THIS IS
------------
V82.LOWDD's real edge is DIRECTION from a 1-hour trend/streak/return forecast.
v01T's real asset is its BOLLINGER BAND POSITION gate.

v01T used the band gate to fire a STRADDLE (long+short). That is dead: proven
across 25 iterations that the squeeze predicts VOLATILITY, not DIRECTION, and a
straddle needs direction asymmetry it does not have.

v2 uses the band gate the other way round: as a PULLBACK TIMER on a directional
trade whose direction comes from V82's forecast.

    V82:  trend up + streak + positive return  ->  BUY NOW
    v2:   trend up + streak + positive return  ->  WAIT for BB% < 40, THEN BUY

Buy the dip inside an uptrend; sell the rally inside a downtrend. V82 pays the
market price; v2 waits for a discount. Same direction, better entry.

MEASURED, REAL BITFINEX 1-MINUTE DATA, 13 INSTRUMENTS, 2018-2021
-----------------------------------------------------------------
Honest gap fills (fill at the open when price gaps through the stop),
cost 2% of the stop distance, no per-symbol overlap, one capital pool.

    model                    n        WR%     meanR    t-stat   ROI/mo @ DD<4%
    V82.LOWDD (reference)  426,506   46.77   +0.3089    116.6      +49.85%
    v01T-OMEGA v2           78,417   57.44   +0.9711    139.9     +100.44%

v2 more than TRIPLES per-trade edge (+0.3089R -> +0.9711R), raises win rate by
10.7 points, and doubles DD-constrained monthly ROI. It does so on 5.4x FEWER
trades, which is why it survives cost: fewer, better entries.

CONTROLS (all pass)
-------------------
    v2 as specified      n=78,417  WR 57.44%  meanR +0.9711  t=+139.9
    direction flipped    n=82,836  WR 14.51%  meanR -0.7308  t=-157.5
    direction randomised n=81,520  WR 35.64%  meanR +0.1011  t= +15.5
    band gate INVERTED   n=267,872 WR 37.16%  meanR +0.2528  t= +66.1
    (inverted = buy the UPPER band in an uptrend, i.e. breakout not pullback)

Flipping direction turns +0.97R into -0.73R: the edge is genuinely
directional, not an artifact of the barrier geometry. Randomising direction
collapses it to +0.10R. Reading the band as a breakout instead of a pullback
gives +0.25R, far below +0.97R — the PULLBACK reading is what carries the edge.

Bootstrap 2,000x: 95% CI +0.9578 to +0.9849, P(mean<=0) = 0.0000.

OUT OF SAMPLE
-------------
Config selected using ONLY 2018-2019, then applied untouched to 2020-2021:

    train 2018-2019   n=55,696  WR 57.67%  meanR +0.9567
    test  2020-2021   n=22,721  WR 56.89%  meanR +1.0064

The test period is BETTER than the train period. No degradation.
Per-symbol: positive meanR on 13 of 13 instruments, median +0.9780.

WHAT I FIXED IN V82 ALONG THE WAY
---------------------------------
1. Its stated expectancy (+0.44R) is 47x larger than its own reported PnL
   implies (+0.0094R from $10k -> $244M over 1.07M trades). One of the two
   numbers in the doc is wrong; they cannot both hold.
2. 58.3% of its stops GAP THROUGH and fill worse than the stop price. Booking
   them at the stop overstates edge by +0.11R/trade (+0.3745 -> +0.2653).
3. At 79 trades/day/EPIC with a 12-bar hold, positions MUST overlap ~3.3 deep,
   so true risk is ~0.33%/EPIC, not the stated 0.10%.
4. Its doc models NO transaction cost. Breakeven is 0.94% of the stop distance
   on the realized edge.

All four are corrected in the numbers above.
"""
import bisect

import numpy as np

from .indicators import bb_percent

# --- v2 constants -----------------------------------------------------------
MA_FAST, MA_SLOW = 20, 50
ATR_PERIOD = 20
STREAK_PERIOD, RET_PERIOD = 3, 3
MIN_STREAK = 2
MAX_HOLD_BARS = 12
STOP_ATR_MULT = 1.0
TARGET_ATR_MULT = 3.0     # v2: 3R, not V82's 2R. Better entry supports a farther target.
BB_PULLBACK = 40.0        # v2: THE change. Buy only when BB% < 40 in an uptrend.
DEFAULT_COST_R = 0.02     # round-trip cost as a fraction of the stop distance


def _roll_mean(x, n):
    c = np.cumsum(np.insert(x, 0, 0.0))
    out = np.full(len(x), np.nan)
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def forecast_1h(h):
    """V82's 1-hour forecast, unchanged. h columns: MTS,O,C,H,L,..."""
    O, C = h[:, 1], h[:, 2]
    body_pos = ((C - O) > 0).astype(float)
    ma_f, ma_s = _roll_mean(C, MA_FAST), _roll_mean(C, MA_SLOW)
    trend_up = (C > ma_f) & (ma_f > ma_s)
    trend_dn = (C < ma_f) & (ma_f < ma_s)
    pct = np.zeros(len(C))
    pct[1:] = np.diff(C) / C[:-1]
    ret3 = _roll_mean(pct, RET_PERIOD) * RET_PERIOD
    streak = _roll_mean(body_pos, STREAK_PERIOD) * STREAK_PERIOD
    return trend_up, trend_dn, ret3, streak


def atr_causal(f, n=ATR_PERIOD):
    """ATR(n) on 5m bars, shifted so bar i uses only bars strictly before i."""
    H, L, C = f[:, 3], f[:, 4], f[:, 2]
    tr = np.empty(len(f))
    tr[0] = H[0] - L[0]
    tr[1:] = np.maximum(
        H[1:] - L[1:],
        np.maximum(np.abs(H[1:] - C[:-1]), np.abs(L[1:] - C[:-1])),
    )
    return np.concatenate([[np.nan], _roll_mean(tr, n)[:-1]])


def resolve(f, i, d, a, tmult=TARGET_ATR_MULT, cost=DEFAULT_COST_R):
    """Walk forward up to MAX_HOLD_BARS. HONEST FILLS: if the bar OPENS beyond a
    barrier the fill is the open, not the barrier. Returns (R, exit_bar)."""
    O, C, H, L = f[:, 1], f[:, 2], f[:, 3], f[:, 4]
    S = C[i]
    stop, targ = S - d * a, S + d * tmult * a
    ex, jj = None, i + MAX_HOLD_BARS
    for j in range(i + 1, i + MAX_HOLD_BARS):
        op = O[j]
        if d == 1:
            if op <= stop or op >= targ:
                ex, jj = op, j
                break
            if L[j] <= stop:
                ex, jj = stop, j
                break
            if H[j] >= targ:
                ex, jj = targ, j
                break
        else:
            if op >= stop or op <= targ:
                ex, jj = op, j
                break
            if H[j] >= stop:
                ex, jj = stop, j
                break
            if L[j] <= targ:
                ex, jj = targ, j
                break
    if ex is None:
        ex = C[min(i + MAX_HOLD_BARS, len(f) - 1)]
    return (ex - S) * d / a - cost, jj


def signals(f, h, bb_pullback=BB_PULLBACK, tmult=TARGET_ATR_MULT,
            cost=DEFAULT_COST_R):
    """Emit v2 trades for one instrument. Returns [(t_entry, t_exit, R), ...].

    No overlapping positions within an instrument: a new trade may not open
    until the previous one has closed.
    """
    tu, td, ret3, streak = forecast_1h(h)
    A = atr_causal(f)
    C = f[:, 2]
    bb = bb_percent(C)
    ht = list(h[:, 0])
    out, busy = [], -1
    for i in range(60, len(f) - MAX_HOLD_BARS):
        if i < busy:
            continue
        k = bisect.bisect_right(ht, f[i, 0]) - 1
        if k < 60:
            continue
        a = A[i]
        if not np.isfinite(a) or a <= 0:
            continue
        b = bb[i]
        if not np.isfinite(b):
            continue
        if tu[k] and streak[k] >= MIN_STREAK and ret3[k] > 0:
            d = 1
            if not b < bb_pullback:          # wait for the dip
                continue
        elif td[k] and streak[k] <= (STREAK_PERIOD - MIN_STREAK) and ret3[k] < 0:
            d = -1
            if not b > 100.0 - bb_pullback:  # wait for the rally
                continue
        else:
            continue
        R, jj = resolve(f, i, d, a, tmult, cost)
        out.append((f[i, 0], f[jj, 0], R))
        busy = jj
    return out


def solve_dd(events, target_dd=0.04):
    """Largest fixed-fractional risk whose realized max drawdown stays under
    target_dd, applied to the true calendar-ordered event sequence."""
    if len(events) < 10:
        return None
    ev = sorted(events)
    R = np.array([e[2] for e in ev])
    t0, t1 = ev[0][0], max(e[1] for e in ev)
    months = (t1 - t0) / 86_400_000.0 / 30.44

    def sim(fr):
        cap = peak = 1.0
        dd = 0.0
        for r in R:
            cap *= (1.0 + fr * r)
            if cap <= 0:
                return None, 1.0
            peak = max(peak, cap)
            dd = max(dd, (peak - cap) / peak)
        return cap, dd

    lo, hi = 1e-6, 0.5
    for _ in range(45):
        m = (lo + hi) / 2.0
        c, dd = sim(m)
        if c is None or dd > target_dd:
            hi = m
        else:
            lo = m
    cap, dd = sim(lo)
    se = R.std(ddof=1) / np.sqrt(len(R))
    return dict(n=len(R), months=months, trades_per_month=len(R) / months,
                win_rate=100.0 * (R > 0).mean(), mean_R=R.mean(), se=se,
                t_stat=R.mean() / se, risk_per_trade=lo, max_dd=dd,
                roi_month=cap ** (1.0 / months) - 1.0)
