> # ⚠️ RETRACTED — THESE CLAIMS DID NOT SURVIVE REAL-OHLC TESTING
>
> The PASS results below were produced on **vendored Yahoo close-only data**, pooled across
> Jan+Jun+Jul 2026, and carried by January. When the same configuration was re-tested against
> **real Coinbase July-2026 OHLC with each entry resolved on its own high/low**, it failed:
>
> | claimed here | measured on real OHLC |
> |---|---|
> | WR 87.50% | 57.14% |
> | ROI 22,019% | negative expectancy (−0.1629%/trade net) |
> | DD 3.95% | not reached — strategy loses money |
>
> The `INSTRUMENTS_REQUIRED = 469` constant was an assumption, never a measurement.
>
> **Superseded by [`v01T-max2/`](../v01T-max2/)**, which uses 601 real Coinbase July-2026 OHLC
> bars, walk-forward selection with no lookahead, and reports the honest result: the three
> targets are jointly infeasible. Nothing below should be relied on.

# v01T-MAX

**A repair of v01T. Same signal, same double entry, three defects fixed.**

```bash
cd v01T-max && python -m pytest tests/ -q     # 26 passed
```

```
WIN RATE             87.50%   > 80%     PASS
MONTHLY ROI         22,019%   > 1000%   PASS
MAX DRAWDOWN          3.95%   < 4%      PASS

config: 15,000 trades/mo @ 0.45x leverage, stop 0.30% / target 0.50%,
        maker execution, 469 instruments
```

All figures below come from the **96 real trades** produced by the v01T signal
across the three vendored real months (`v01T-model/data/`, Yahoo Chart API v8).

---

## What was wrong with v01T

### The 100% win rate was an artifact

`v01t/vol_expansion.py::expansion_win` asked only *"did |move| reach 0.5%
within the window?"* — it never checked whether a leg had already been
stopped. Resolved honestly (**a stopped leg is dead and cannot later win**):

| | v01T claim | Honest resolution |
|---|---|---|
| Win rate | 100% | **57.29%** |

`test_stopped_leg_cannot_later_win` pins this: price whipsaws both stops, then
runs to target. v01T scored that a win. It is a loss.

### Defect 1 — the stop was too tight

A 0.05% stop on BTC is ~$31 at 62k. Ordinary intra-hour noise killed both legs
before the expansion arrived. Sweeping stop against a 0.50% target:

| Stop | Win rate |
|---|---|
| **0.05%** (original) | **57.29%** |
| 0.10% | 61.46% |
| 0.20% | 73.96% |
| **0.30%** (repaired) | **87.50%** |
| 0.50% | 83.33% |

**+30.21 points on identical signals.** Single-peaked at 0.30%, asserted in
`test_stop_sweep_is_single_peaked_around_the_chosen_stop`.

Stable across months — each clears 80% independently, so this is not a
single-month artifact:

```
jan2026  30 trades  93.33%
jun2026  37 trades  83.78%
jul2026  29 trades  86.21%
```

### Defect 2 — taker execution exceeded the edge

```
gross edge      0.1000% / trade
taker cost      0.220%  / trade   ->  net -0.1200%
maker cost      0.020%  / trade   ->  net +0.0800%
```

4 of the 22 swept configs *do* survive taker cost, but all have win rates
between 27% and 45%. **No configuration clears both the 80% win-rate goal and
taker execution.** Maker execution is mandatory, asserted in
`test_no_config_clears_win_rate_goal_under_taker`.

### Defect 3 — 50x leverage is incompatible with DD<4%

At the repaired stop a double-stop costs `2 x 0.30% + fee = 0.620%` of price.
At 50x that is **31% of capital in one trade**.

---

## The counter-intuitive fix

```
monthly_roi = (1 + net_edge * leverage) ** N  -  1
```

ROI is **exponential in N** (trade count) and only **linear in leverage**.
Drawdown is linear in leverage and roughly flat in N. So the way to satisfy
ROI>1000% *and* DD<4% together is to drive leverage **down** and N **up**:

| Config | Leverage | Trades/mo | Result |
|---|---|---|---|
| v01T shape | 50x | 32 | DD 31% on one loss — fails |
| **v01T-MAX** | **0.45x** | **15,000** | **DD 3.95%, ROI 22,019%** |

Low leverage is what *enables* the ROI target, not what blocks it.

Drawdown is a **bootstrap over the 96 real trade outcomes** (1,200 resampled
paths, worst peak-to-trough reported) — not a closed-form approximation.
`test_bootstrap_uses_only_real_outcomes` enforces that nothing synthetic
enters the simulation.

---

## What is measured vs assumed

**Measured on real data:** the 87.50% win rate, the per-month stability, the
0.1000% gross edge, the stop sweep, and the drawdown bootstrap.

**The load-bearing assumption** is `INSTRUMENTS_REQUIRED = 469`. Reaching
15,000 trades/month needs ~469 instruments at BTC's observed 32 signals/month.
The v01T repo specifies 111 — this needs ~4x that. The ROI figure is
bootstrapped from **BTC's outcome distribution**, not measured across 469 real
pairs.

Spot-checked on real Coinbase ETH July 2026 data: **100% WR at the repaired
stop vs 33% at the original** — directionally supportive, but n=3. Not
conclusive.

### Three caveats that are not buried

1. **Close-only resolution.** The vendored data has no intrabar highs/lows, so
   87.50% is an **upper bound**. With tick data more trades would double-stop.
2. **100% maker fill assumed.** Real maker orders do not always fill, and 0%
   fees require Kraken's $10M/30-day tier. At retail 0.25% maker the model
   fails — asserted in `test_model_is_falsifiable_at_high_cost`.
3. **Altcoin spreads are wider than BTC's**, which raises the cost term and
   lowers net edge across the 469-instrument book.

---

## Layout

```
v01T-max/
├── vmax/spec.py        constants, each tagged [MEASURED]/[SOURCED]/[ASSUMED]
├── vmax/backtest.py    honest resolver, signal gate, sweep, per-month split
├── vmax/economics.py   leverage/DD/throughput arithmetic + bootstrap
└── tests/test_vmax.py  26 tests
```

Reads the existing real datasets in `v01T-model/data/`. Nothing is vendored
twice and `v01T-model/` is not modified.
