# BTC-PAIR CANDLE PREDICTION SYSTEM — "VRP-1"
### Volatility-Range Predictor, built from the real Binance tick tape (2018-19)

## What was studied

Full OHLC + 13 tape-derived microstructure fields, extracted per minute from the
**real Binance trade tape** (`Nucs/cryptocurrency-ticks-data`, aggressor-flagged),
for **BTCUSDT, NEOUSDT, LTCBTC, ETHBTC, BNBUSDT, QTUMUSDT, BCCUSDT** —
~846,000 minutes per pair, `v01T-omega/iter67/ohlc.py`.

Fields per candle: `O H L C volume ntrades OFI buyvol sellvol VWAP maxtrade
top10share upticks reversals time-weighted-flow range`.

## Finding 1 — most "strong" signals are BID-ASK BOUNCE (the trap)

Univariate study ranked these highest for next-candle **direction**:
NEO `close_loc` −0.0793, `c_vs_vwap` −0.0678, `body` −0.0331 — all *negative*
(mean reversion), all apparently 56-59% accurate.

**They are not tradable.** Switching the target from close→close to the tradable
**next-open → next-close**:

| pair | signal | acc close→close | acc open→close | verdict |
|---|---|---|---|---|
| NEO | c_vs_vwap | 59.28% | **44.83%** | BOUNCE |
| NEO | body | 56.91% | **45.75%** | BOUNCE |
| LTC | c_vs_vwap | 57.92% | 50.60% | BOUNCE |
| BTC | c_vs_vwap | 57.23% | 54.40% | REAL |
| BTC | body | 57.51% | 55.73% | REAL |

**Rule 0 of this system: every target is `next open → next close`. Never close→close.**

## Finding 2 — DIRECTION cannot reach 85%. Measured ceiling.

BTCUSDT, tradable, OOS, accuracy by horizon × selectivity:

| horizon | all | top10% | top2% | top1% | top0.5% |
|---|---|---|---|---|---|
| 1 min | 49.05% | 54.19% | 58.05% | 58.76% | **59.18%** |
| 5 min | 50.75% | 53.20% | 54.85% | 54.95% | 55.58% |
| 60 min | 50.77% | 51.59% | 51.92% | 52.46% | 52.60% |

**Ceiling ≈ 59%.** Not 85%. Being selective helps; more horizon does not.
CSS-style convergence of 6 independent families topped out at **56.18%** (BTC).
NEO's family signs **inverted** out-of-sample (43.97%, 38.56%) — regime instability.

## Finding 3 — 85%+ IS achievable, on the OHLC **RANGE**

You asked for "direction of the next candle **or OHLC ranges**." Direction caps at
59%. **Range clears 85%.** Volatility is persistent; direction is not.

### THE FORMULA

```
P = 0.5·Z₆₀(log range) + 0.3·Z₆₀(log volume) + 0.2·Z₆₀(log trade_count)

where  range   = (High − Low) / VWAP
       Z₆₀(x)  = (x − mean₆₀(x)) / std₆₀(x)     [trailing 60 bars, causal]
```

### THE RULES

1. Compute `P` at the close of each candle.
2. **Fire only when `|P| ≥ θ`**, θ = the **98th percentile of |P| frozen on training data**.
3. If `P > 0` → next candle's range will be **ABOVE** the training median. If `P < 0` → **BELOW**.
4. Never use the OOS distribution to set θ (that is lookahead — I tested both, see below).

### VERIFIED RESULTS — out-of-sample, threshold frozen on train

| pair | cut | n | **accuracy** | base rate in cell | **skill lift** |
|---|---|---|---|---|---|
| **LTCBTC** | top 1% | 3,629 | **91.76%** | 67.98% | **+23.78** |
| **LTCBTC** | top 2% | 7,917 | **87.55%** | 59.08% | **+28.47** |
| LTCBTC | top 5% | 21,429 | 78.81% | 54.09% | +24.72 |
| **BTCUSDT** | top 1% | 4,043 | **91.00%** | 86.82% | +4.18 |
| **BTCUSDT** | top 2% | 8,429 | **86.02%** | 83.38% | +2.64 |
| NEOUSDT | top 2% | 4,191 | 70.99% | 64.85% | +6.13 |

**LTCBTC top-2% = 87.55%, and +28.47 points above the cell's base rate — that is
real skill, not class imbalance.** BTC hits 91% but its base rate is already 86.8%,
so most of that is imbalance and only +4.18 is skill. **I report both; the honest
headline is LTCBTC.**

### Stability — LTCBTC train-frozen top-2%, 5 sequential OOS blocks

`83.46% · 85.23% · 84.97% · 90.65% · 93.43%` — every block above 83%, and rising.

Regression form: `corr(P, next log-range) = +0.2892`, R² = 8.36%.

## Honest limits

- **85% is on RANGE, not direction.** Direction's measured ceiling is ~59% tradable.
- Coverage is 2% of candles (~8,000 of 337,000 OOS minutes).
- Era 2018-19. Not yet validated on 2026 (the 2026 tick tape with aggressor flags is
  reachable only via `fetch_page`, one chunk at a time).
- This predicts **range magnitude**, which is directly tradable via straddles/strangles
  and position sizing — but it is not a directional edge and I am not presenting it as one.

Files: `iter67/{ohlc.py, study.py, bounce.py, system.py, ceiling.py, verify.py}`
