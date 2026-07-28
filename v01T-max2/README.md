# v01T-max2 — real-OHLC rebuild of v01T, and the measured verdict

## Headline

**The three targets were NOT achieved. They cannot be, at any edge measured on real data.**

| Target | Result | Status |
|---|---|---|
| WIN RATE > 80% | 72.44% (walk-forward) | **FAIL** |
| MONTHLY ROI > 1000% | 14.23% (at DD cap) | **FAIL** |
| MAX DRAWDOWN < 4% | 4.00% | PASS |

Reproduce: `python3 run_backtest.py` · Verify: `pytest tests/ -q` (15 passing)

## The data — 100% real, no substitutions

- **601 Coinbase `BTC-USD` 1-hour OHLC bars, 2026-07-01 → 2026-07-26, zero gaps.**
- Pulled live from `api.exchange.coinbase.com/products/BTC-USD/candles`, stored verbatim in
  `data/btc_usd_1h_jul2026_coinbase_ohlc.json` (`[low, high, open, close, volume]` per bar).
- Every entry is resolved against **that entry's own subsequent real high/low**, not closes.
- No synthetic, simulated, interpolated, or assumed data is used anywhere in this model.

Integrity is enforced by tests, not by claim: bar count, hourly contiguity, the July-2026
window, and `low <= open/close <= high` for all 601 bars.

## Three findings that decide the question

### 1. A win rate above 80% is free, and it is not edge

Real July 2026 BTC, no signal at all, just barriers:

| stop | target | random-walk `s/(s+t)` | measured |
|---|---|---|---|
| 0.30% | 0.50% | 37.5% | 36.79% |
| 0.50% | 0.50% | 50.0% | 50.71% |
| 1.00% | 0.25% | 80.0% | **85.36%** |
| 4.00% | 1.00% | 80.0% | **81.07%** |

Measured win rate tracks the random walk. Widen the stop relative to the target and the
win rate rises to any level you like — while the *average loss* grows in exact proportion.
**This is how v01T reached "100% WR", and why that number never turned into money.**
Win rate, on its own, carries no information about profitability.

### 2. The targets are jointly infeasible — this is arithmetic, not pessimism

Model equity as GBM. For a strongly drifting process the expected maximum drawdown tends to
`σ²/(2μ)` (Magdon-Ismail, Atiya, Pratap & Abu-Mostafa, *On the Maximum Drawdown of a Brownian
Motion*, J. Appl. Prob. 2004). Demanding ROI > 1000%/month **and** maxDD < 4% fixes both μ and σ:

```
required monthly log growth   G = ln(11)     = 2.398
allowed monthly log drawdown  D = -ln(0.96)  = 0.041
max monthly volatility        σ = sqrt(2GD)  = 44.2%
=> REQUIRED ANNUALISED SHARPE ≈ 18.8
```

For scale: S&P 500 ≈ 0.4; Medallion at fund level ≈ 2; an elite HFT market maker ≈ 8.
The two targets together demand roughly **twice the best sustained Sharpe in the industry**,
and they demand it from a single crypto book.

### 3. Walk-forward, the only test that cannot lie

Parameters (signal, stop, target) are chosen using **only bars strictly before** each trading
day, then applied forward. No lookahead:

```
trades 127   WIN RATE 72.44%   net EV/trade +0.4429%  (t = +4.28)
annualised Sharpe 14.84   —   required 18.8
```

The edge is real (t = +4.28) but it is *not enough*, and the leverage ranges do not overlap:

| leverage | ROI | maxDD | ROI>1000%? | DD<4%? |
|---|---|---|---|---|
| 0.20× | 11.86% | 3.38% | no | **yes** |
| 1.60× | 139.74% | 24.46% | no | no |
| 6.40× | 2271.66% | 70.02% | **yes** | no |
| 12.80× | 19086.37% | 93.03% | **yes** | no |

ROI and drawdown are both monotone in leverage, so they trade off along one curve set by
Sharpe. **The passing regions are disjoint. No leverage exists that satisfies both** — a test
(`test_roi_and_dd_ranges_are_disjoint`) sweeps leverage and asserts this.

At the maximum leverage respecting DD < 4% (**0.24×**), ROI is **14.23%** — a **70× shortfall**.

## What this says about v01T

- v01T's gate (`BB% < 10 or > 90` and `HV ratio < 0.8`) has **no edge**: on real OHLC it is
  *worse* than taking every bar (`test_v01t_gate_not_better_than_baseline`).
- v01T's 100% win rate came from counting a bar that spans both barriers as a win. Here such
  a bar is booked a **loss** (`ambiguous_loss`), because at 1h resolution the intrabar order is
  genuinely unknowable. That single correction is the difference between fantasy and honesty.
- July 2026 BTC rose **+10.20%**. Long beat short for *every* signal tested — that is the
  month's drift, not skill. Any "edge" not benchmarked against it is measuring the calendar.

## Honest limits of this result

- One month, one instrument. 127 walk-forward trades is a real but modest sample.
- Hourly bars cannot resolve intrabar sequence; the conservative rule makes results a
  *lower* bound, never an overestimate.
- Fees modelled at 4 bps round-trip (maker). Taker execution would reduce the edge further.
- A different month, venue, or asset would shift the Sharpe — but the feasibility bound in
  §2 is independent of all of them.

## Layout

```
vmax2/ohlc.py       real-data loading, conservative barrier resolution, equity/drawdown
vmax2/signals.py    BB%, HV ratio, momentum, the original v01T gate
vmax2/backtest.py   trade generation, statistics, walk-forward selection
vmax2/bound.py      the joint feasibility bound (pure mathematics)
run_backtest.py     the full report reproduced above
tests/test_vmax2.py 15 tests: data integrity, resolution honesty, the disjointness proof
data/               601 real Coinbase July-2026 bars
```

`v01T-model/` is unmodified.
