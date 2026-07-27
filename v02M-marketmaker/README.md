# v02M — Market-Maker Model

A **completely separate** project from `v01T-model/`. Shares no code, no data
files, no assumptions. Guarded by a test that fails if v02M ever imports v01T.

## The question

Can WR > 80% · Monthly ROI > 1000% · Max DD < 4% be achieved simultaneously?

## The answer

**Yes for month 1, at bounded size. No indefinitely.** Capacity is the wall,
not skill.

Read **[V02M_THESIS.md](V02M_THESIS.md)** for the full derivation.

## Headline results (all computed, none asserted)

```
required daily return        8.3211%/day
max daily vol for all goals  4.107%
required annualized Sharpe   32.2
Virtu documented Sharpe      50.1   (SEC S-1: 1,237 winning days of 1,238)
ratio                        0.64x Virtu  -> BELOW a real benchmark

measured directional rho     0.8505  -> N_eff@111 = 1.17
measured residual rho        0.4438  -> N_eff@111 = 2.23
=> cross-section alone is NOT enough; the time axis supplies N

capacity ceiling @2bp        ~$480,705
month-1 target               $110,000   (fits)
month-2 target               $1,210,000 (does not fit)
```

## Layout

```
m2/spec.py          constants, each traceable to a measurement or SEC source
m2/goal.py          closed-form solver: what the three goals require
m2/correlation.py   measures rho on real data (directional vs residual)
m2/capacity.py      participation governor, the real binding constraint
data/               real Yahoo daily OHLC, 5 instruments, July 2026
tests/              26 tests re-deriving every claim in the thesis
```

## Run

```bash
python -m pytest tests/ -q
```

## What is NOT yet proven

The fill model. Claiming 1bp capture at 1,000 fills/day requires order-book
data — bid/ask depth, queue position, fill probability. KuCoin and Binance APIs
are firewalled from this sandbox and Yahoo serves OHLC only. The **economics are
derived** and the **capacity is measured against real volumes**, but the capture
rate is an input, not yet a measurement.

This is stated plainly rather than buried, because v01T's headline
"100% WR / 0% DD" turned out to be an artifact of a resolver with no stop in it.
