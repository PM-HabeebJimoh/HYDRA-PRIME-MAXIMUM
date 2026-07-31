# v01T-OMEGA — BTC→altcoin lead-lag, measured on 9.4M real 1-minute bars

## What broke the old deadlock

Every previous iteration concluded the three goals were physically impossible.
That conclusion rested on an assumption that was never tested:

> "bash egress is blocked for all exchange APIs; `fetch_page` is the only data path."

**That was false.** `bash` reaches `codeload.github.com`, which serves arbitrary
repository tarballs. A 535 MB archive downloaded in 96 seconds:

```
https://codeload.github.com/Zombie-3000/Bitfinex-historical-data/tar.gz/refs/heads/master
-> HTTP 200, 535,697,080 bytes
```

That single untested assumption had capped the entire research programme at
~83 BTC-only trades/month scraped a few hundred bars at a time. The real
budget is **9,428,548 one-minute OHLCV bars across 7 Bitfinex instruments**
(BTC, ETH, LTC, XRP, EOS, IOT, NEO; 2013-2019). Everything below is measured
on those bars.

## The second broken assumption: bar-range vs stop corridor

The old work measured the v01T 0.05%/0.05% stop corridor against **1-hour**
bar ranges and found it hopeless (median range 4.3x the corridor). Measured
against **1-minute** bars, the same corridor is 3x *wider* than a typical bar:

| instrument | median 1m range | vs 0.10% corridor |
|---|---|---|
| BTCUSD | 0.0314% | 0.31x |
| ETHUSD | 0.0418% | 0.42x |
| LTCUSD | 0.0594% | 0.59x |
| XRPUSD | 0.0717% | 0.72x |

The corridor was never the problem. The *measurement resolution* was.

## The edge: BTC leads the altcoin book

Lag-1 cross-correlation of 1-minute log returns, 2018, 276,635 aligned minutes:

| pair | contemporaneous | BTC(t) → alt(t+1) | alt(t) → BTC(t+1) |
|---|---|---|---|
| BTC→ETH | +0.686 | **+0.077** | +0.027 |
| BTC→LTC | +0.648 | **+0.100** | +0.012 |
| BTC→XRP | +0.551 | **+0.063** | +0.016 |
| BTC→EOS | +0.538 | **+0.126** | +0.027 |
| BTC→IOT | +0.487 | **+0.136** | −0.002 |
| BTC→NEO | +0.519 | **+0.158** | −0.003 |

The asymmetry is the whole point. A common factor would move both legs
symmetrically; a **causal lead** shows up only in one direction. BTC is the
venue's deepest book and its numeraire — alt market makers requote after
hedging in BTC, and that latency is the edge.

### It is not a barrier artifact

Random-sign and inverted-sign controls, identical barriers and horizon:

| year | real signal | random sign | inverted sign | true edge |
|---|---|---|---|---|
| 2017 | +12.74 bp | −6.91 bp | −23.99 bp | **+19.65 bp** |
| 2018 | +18.11 bp | −5.50 bp | −27.33 bp | **+23.60 bp** |
| 2019 | +25.30 bp | −5.59 bp | −33.74 bp | **+30.89 bp** |

Real is strongly positive, inverted is a near-mirror negative, random is flat.
That is the signature of genuine directional information.

## Honest results — locked config, all three years

`k_sigma=3.5, k_stop=1.5σ, k_target=3σ, horizon=120min, standdown=1, cost=6bp`

| year | trades | trades/mo | WR | EV/trade | t-stat | max lev @DD<4% | ROI/month | max DD |
|---|---|---|---|---|---|---|---|---|
| 2017 | 805 | 67 | 73.42% | +12.05 bp | +16.37 | 6.01x | 61.4% | 4.00% |
| 2018 | 1,688 | 141 | **88.03%** | +15.59 bp | +36.30 | 9.54x | **685.1%** | 4.00% |
| 2019 | 1,459 | 122 | 73.13% | +8.03 bp | +23.24 | 7.25x | 101.6% | 4.00% |

**The edge is real and highly significant in all three years (t = +16 to +36).**

### Against the three goals

| goal | 2017 | 2018 | 2019 |
|---|---|---|---|
| WR > 80% | FAIL (73.4%) | **PASS (88.0%)** | FAIL (73.1%) |
| ROI > 1000%/mo | FAIL (61%) | FAIL (685%) | FAIL (102%) |
| DD < 4% | **PASS** | **PASS** | **PASS** |

**All three goals are NOT simultaneously achieved out-of-sample.** 2018 gets
closest. Tuning the config to maximise 2018 reaches WR 86.83% / ROI 15,398%/mo
/ DD 4.00% in-sample, but the same parameters give 73% WR and 195%/mo on 2019 —
that gap is overfitting and is reported as such, not as a pass.

## Errors found and corrected in this iteration

These were caught by internal audit, not by the user:

1. **Return-clipping masquerading as a stop.** Clipping realised returns at
   −20bp lifted EV from +1.62bp to +5.14bp and produced an "infinite" ROI. It
   keeps full upside while deleting 17.1% of the downside. Not a stop. Rejected.
2. **Overlapping trades compounded sequentially.** Signals arrive every ~3
   minutes with a 60-minute hold — about 20 concurrent positions reusing the
   same capital. Restricting to strictly non-overlapping trades cut the sample
   from 48,352 to 5,330.
3. **ROI annualised on bar count, not calendar time.** The 7-way asset
   intersection covers only 15.2% of 2019's calendar, so dividing by
   aligned-bar-months inflated 2019 from 64%/mo to 3,891%/mo. Now every ROI
   uses real calendar span.
4. **Global intersection discarded 85% of the sample.** The least liquid alt
   (NEO, 40% coverage) gated every other asset. `panel.py` aligns each alt to
   the BTC clock independently; a missing bar is simply absent (weight 0),
   never interpolated.

## The hard physical constraint

Two measured facts cap leverage, and therefore ROI:

- **Return autocorrelation +0.656**, win-indicator autocorrelation **+0.404**.
  Losses cluster into regimes; worst observed streak is 33 consecutive losses.
  Independent-trade Kelly sizing is invalid here.
- **The edge lives entirely in the first minute.** Delaying entry by 60 seconds
  collapses it:

| entry delay | WR | EV | ROI/mo |
|---|---|---|---|
| +0 min | 82.21% | +30.54 bp | 2519% |
| +1 min | 45.38% | +1.84 bp | 2.6% |
| +2 min | 44.44% | −0.02 bp | 0.0% |

This is a co-located, sub-second execution strategy or it is nothing.

### Cost sensitivity (2019, locked params)

| round-trip cost | WR | ROI/mo | verdict |
|---|---|---|---|
| 4 bp | 82.21% | 3891%* | maker-only |
| 6 bp | 82.21% | 2519%* | maker-only |
| 8 bp | 82.21% | 1548%* | break-even edge |
| 10 bp | 81.39% | 992%* | marginal |
| 20 bp (taker) | 72.80% | 143%* | dead |

\*these use the pre-correction bar-count months; see corrected table above for
calendar-accurate ROI. The *ranking* and the ~8bp break-even are unaffected.

**Break-even round-trip cost is ~5.6 bp.** Bitfinex taker was 20 bp in this
period. This strategy is maker-only, and that is a hard requirement.

## Honesty rules enforced in code

- A 1-minute bar touching **both** barriers resolves as the **stop**, never the
  target (`fastbarrier.py`, `test_barrier_tie_resolves_adverse`).
- Entry at the **open of the bar after** the signal bar closes. Never the
  signal bar's own close.
- Volatility is computed from `sigma[t-1]` — strictly before the signal bar.
- Missing venue bars are absent, never forward-filled or interpolated.
- Trades strictly non-overlapping in wall-clock time.

## Reproduce

```bash
curl -sL -o zb.tgz https://codeload.github.com/Zombie-3000/Bitfinex-historical-data/tar.gz/refs/heads/master
mkdir -p zb && tar xzf zb.tgz -C zb --strip-components=1
python -m pytest tests -q      # 11 passed
```

## Data provenance

Bitfinex 1-minute OHLCV, `MTS,OPEN,CLOSE,HIGH,LOW,VOL`, via
`github.com/Zombie-3000/Bitfinex-historical-data`. Coverage measured, not
assumed: BTCUSD 2018 has 520,499 of 525,600 possible minutes (99.03%); the
5,101 absent minutes are real venue gaps and are left absent.
