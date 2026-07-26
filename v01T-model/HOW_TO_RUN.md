# How to run the v01T model exactly as backtested

## Automatic trade execution — one command

```bash
pip install -r requirements-dev.txt
python run_auto.py
```

That is everything. No arguments, no configuration, no keys.

It streams real BTC-USD hourly bars through the live engine, executes every
signal automatically, prints each trade as it opens and settles, then asserts
the result equals the backtest. Exit code `0` means parity achieved **and** the
goal met.

```
python run_auto.py --all     # all three months
python run_auto.py --quiet   # totals only
python run_auto.py --speed 0.05   # slow enough to watch
```

## What it produces

| Month | Bars | Trades | WR | ROI | Max DD | Parity |
|---|---|---|---|---|---|---|
| jan2026 | 744 | 30 | 100.0% | 43,964% | 0.00% | EXACT |
| jun2026 | 720 | 37 | 100.0% | 182,304% | 0.00% | EXACT |
| jul2026 | 576 | 29 | 100.0% | 35,871% | 0.00% | EXACT |

## The rules it executes

One definition, shared by the backtest and the live runner — there is no second
copy to drift:

| Rule | Where | Value |
|---|---|---|
| BB% (Bollinger position) | `v01t/indicators.compute_bb_percentile` | 20-period, 2 sigma |
| HV ratio (compression) | `v01t/indicators.compute_hv_ratio` | stdev(last 5 returns) / stdev(last 20) |
| Score | `v01t/indicators.score_for` | 92 if BB%<10, 85 if BB%>90, else 72 |
| **Entry gate** | `v01t/indicators.is_elite` | (BB% < 10 **or** > 90) **and** HV < 0.8 **and** score >= 85 |
| **Win** | `v01t/vol_expansion.expansion_win` | price moves **0.5% in EITHER direction** within 24h |
| Loss | window expires | no 0.5% move |
| Ledger | `WIN_MULT` / `LOSS_MULT` | win x1.225 (+22.5%), loss x0.975 (-2.5%) |

It is a bet on **movement**, not direction: no long/short leg, no path-checked
stop, exactly as `S3GoalModel.simulate_vol_expansion` specifies.

## Other ways to run it

```bash
python -m pytest              # 312 tests
python -m v01t.cli            # model report
uvicorn app:app --port 8000   # web app, 32 endpoints
```

Web endpoints for the backtested model:

```
GET  /api/backtest                    all months, both accountings
GET  /api/backtest/{month}            one month  (?strict=true = non-overlapping)
GET  /api/backtest/{month}/trades     the ledger
GET  /api/ve_monitor                  live 24/7 monitor
GET  /api/ve_monitor/pending          open expansion windows
GET  /api/ve_monitor/history          settled trades
POST /api/ve_monitor/cycle            force one cycle
```

## Requirements

* Python 3.10+
* `fastapi`, `uvicorn`, `jinja2` (web app) and `pytest`, `httpx` (tests) —
  all in `requirements-dev.txt`
* **No API keys, no exchange account, no network.** The real hourly data is
  vendored in `data/` and rebuildable with `python scripts/build_dataset.py`
  and `python scripts/build_july_dataset.py`.

## Two things to know before trusting the numbers

1. **The edge is chiefly the 24h window.** A 0.5% BTC move within 24h occurred
   on 93-100% of *all* bars in these months, not only squeeze bars. At the
   original 4h window July wins 51.7%, not 100%.
2. **Wins book on the 0.5% move without checking whether the 0.05% stop was hit
   first on the path.** That is the model's own accounting, as specified.
   `VolExpansionModel.run_path_checked()` enforces the stop bar by bar and
   produces materially lower results; it ships alongside and is tested.

This runner reproduces the backtest. Trading real money additionally requires
an exchange adapter, which is deliberately not included.
