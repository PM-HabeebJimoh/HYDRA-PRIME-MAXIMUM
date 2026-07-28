"""
The joint feasibility bound. Pure mathematics - no data, no assumptions.

For equity following geometric Brownian motion with monthly log-drift mu and
monthly log-vol sigma, the expected maximum drawdown for a strongly drifting
process converges to sigma^2 / (2*mu)  (Magdon-Ismail, Atiya, Pratap, Abu-Mostafa,
"On the Maximum Drawdown of a Brownian Motion", J. Applied Probability 2004).

Requiring ROI > 1000%/month AND maxDD < 4% pins both mu and sigma, hence Sharpe.
"""
import math

ROI_TARGET = 10.0    # +1000% => equity multiplies by 11
DD_TARGET  = 0.04

def required_sharpe(roi=ROI_TARGET, dd=DD_TARGET):
    G = math.log(1 + roi)        # required monthly log growth
    D = -math.log(1 - dd)        # allowed monthly log drawdown
    sigma = math.sqrt(2 * G * D)
    monthly = G / sigma
    return dict(log_growth=G, log_dd=D, max_monthly_vol=sigma,
                monthly_sharpe=monthly, annual_sharpe=monthly * math.sqrt(12))

def required_win_rate(n_trades, stop_over_target=4.0, roi=ROI_TARGET, dd=DD_TARGET):
    """Win rate needed at N trades/month for a stop:target ratio."""
    sh = required_sharpe(roi, dd)['monthly_sharpe']
    spt = sh / math.sqrt(n_trades)
    k = stop_over_target
    lo, hi = 0.5, 1.0
    for _ in range(200):
        p = (lo + hi) / 2
        val = ((1 + k) * p - k) / ((1 + k) * math.sqrt(p * (1 - p)))
        if val < spt: lo = p
        else: hi = p
    return (lo + hi) / 2
