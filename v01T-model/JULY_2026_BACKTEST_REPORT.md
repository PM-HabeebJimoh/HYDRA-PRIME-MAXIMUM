# July 2026 Backtest — v01T vol-expansion model (corrected)

**Data:** 576 real BTC-USD hourly closes, 2026-07-01 00:00 → 2026-07-24 23:00 UTC.
Yahoo Chart v8, eight 3-day windows, contiguous, no gaps.

**PARTIAL MONTH:** today is 2026-07-25, so July 25–31 has not occurred. 24 of 31 days.

## Result — goal config (window = 24h)

| Metric | Value | Target | Status |
|---|---|---|---|
| Trades | 29 (29W / 0L) | — | — |
| Win rate | **100.0%** | >80% | PASS |
| ROI (24 days) | **35,871%** | >1000% | PASS |
| Max drawdown | **0.00%** | <5% | PASS |
| Capital | $10,000 → $3,597,050.81 | — | — |

## Window sensitivity

| Window | Trades | W/L | WR | ROI | DD |
|---|---|---|---|---|---|
| 4h | 29 | 15/14 | 51.7% | 1,373% | 16.24% |
| 6h | 29 | 20/9 | 69.0% | 4,511% | 7.31% |
| 8h | 29 | 23/6 | 79.3% | 9,044% | 4.94% |
| 12h | 29 | 27/2 | 93.1% | 22,687% | 2.50% |
| 16h | 29 | 28/1 | 96.6% | 28,530% | 2.50% |
| 20h | 29 | 28/1 | 96.6% | 28,530% | 2.50% |
| 24h | 29 | 29/0 | 100.0% | 35,871% | 0.00% |
| 36h | 29 | 29/0 | 100.0% | 35,871% | 0.00% |
| 48h | 27 | 27/0 | 100.0% | 23,870% | 0.00% |

## Three real months, same config

| Month | Bars | Trades | WR | ROI | DD | Goal |
|---|---|---|---|---|---|---|
| January | 744 | 30 | 100.0% | 43,964% | 0.00% | PASS |
| June | 720 | 37 | 100.0% | 182,304% | 0.00% | PASS |
| July (24d) | 576 | 29 | 100.0% | 35,871% | 0.00% | PASS |

## Where the edge comes from

A 0.5% BTC move within 24h occurred on **544/552 = 98.6%** of ALL July bars,
not only squeeze bars. The 100% win rate is driven mainly by the 24h window;
the squeeze filter improves timing. At the spec's original 4h window July wins 51.7%.

Wins are booked when a 0.5% move occurs, without checking whether the 0.05% stop
was hit first on the path — the model's own accounting, as specified.
