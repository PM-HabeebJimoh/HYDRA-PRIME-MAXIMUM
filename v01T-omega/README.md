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

---

# Iteration 2 — challenging the rules I had imposed on myself

The previous iteration hit a wall at 685%/mo. The wall was made of rules I had
invented and never questioned. Working genuinely back-to-front:

## The goals are not two constraints — they are ONE

ROI scales with leverage. Drawdown scales with leverage. Therefore **ROI/DD is
leverage-invariant**, and leverage is not a free parameter at all:

```
required  ROI/DD  =  1000 / 4  =  250
```

Measured ROI/DD at the end of iteration 1: 2017 = 15.3, 2018 = 171.3,
2019 = 25.4. The 2018 shortfall was only **1.46x**, not the 16.7x previously
claimed. And since `ROI/DD ~ sqrt(N) * (EV/sigma) / sqrt(clustering)`, a 1.46x
gap needs just 2.13x more independent trades.

## Rule I invented and then obeyed: "trades must not overlap"

That is not physics. It is an artifact of assuming a single capital slot. A
real book holds many simultaneous positions in different instruments. Removing
it took 2018 from 141 to **3,520 trades/month — a 25x increase**. `portfolio.py`
does real continuous-time accounting: margin is consumed on open, released on
close, drawdown marked on the equity curve.

Related discovery: the median position resolves in **1 minute**, not the 120
minutes I had reserved for it. I was blocking a capital slot for two hours on a
trade that finished in sixty seconds.

## Why parallel slots alone did NOT work — and the truth it exposed

ROI/DD stayed flat at ~5.0 from 8 slots to 128 slots. Measuring why:

```
legs per signal            5.80
single-leg sd             20.98 bp
group-mean sd if indep.    8.71 bp
group-mean sd ACTUAL      16.40 bp
=> effective independent legs = 1.64
```

**Six altcoins responding to one BTC impulse are 1.64 bets, not 6.** Adding
slots multiplies a position, it does not diversify it.

## The fundamental regime variable

Signal-mean return vs trailing BTC volatility: **r = +0.835**.

| vol quintile | mean sigma | WR | EV | EV/sigma |
|---|---|---|---|---|
| 1 | 2.1 bp | 38.6% | −2.31 bp | −1.12 |
| 2 | 4.1 bp | 77.4% | +2.21 bp | +0.53 |
| 3 | 6.1 bp | 79.3% | +6.70 bp | +1.09 |
| 4 | 9.2 bp | 82.3% | +14.28 bp | +1.55 |
| 5 | 16.6 bp | 84.8% | +32.60 bp | +1.97 |

Both the *unitless* win rate and the *scale-free* EV/sigma rise monotonically,
so this is not a mechanical artifact of vol-scaled barriers. Two real causes:
barriers scale with sigma while cost is a fixed 6 bp (in quintile 1 the barrier
is ~3 bp and the fee alone exceeds the whole move), and the alt book must
actually be re-quoting for a lead-lag to exist at all.

## The unit error that was costing the most

The impulse is detected in **BTC** space but the position is held in **ALT**
space. I had been sizing barriers with `sigma_BTC`. In 2017 the alts were 2-4x
more volatile than BTC, so a "1.5 sigma_btc" stop was a small fraction of one
alt sigma and was destroyed by ordinary alt noise before the impulse arrived.

Decomposing the pure signal, `E[alt_{t+1} | impulse] / sigma_alt`:

| year | mean | strongest leg |
|---|---|---|
| 2017 | **+0.399** | ETH +0.531 |
| 2018 | +0.280 | NEO +0.373 |
| 2019 | +0.264 | IOT +0.453 |

The signal was strongest in 2017 — the year that performed worst. The edge was
never missing; the yardstick was wrong. Fixing it (`altscaled.py`) raised 2017
EV from +10.3 to +22.4 bp.

## Barrier geometry: stop WIDER than target

To hit WR > 80% the near barrier must be the target. With alt-scaled barriers
at `stop = 6 sigma_alt, target = 2 sigma_alt`:

| year | WR | EV |
|---|---|---|
| 2017 | 85.1% | +17.92 bp |
| 2018 | 95.1% | +22.84 bp |
| 2019 | 91.6% | +14.89 bp |

### Controls prove this is signal, not geometry

| year | real | random sign | inverted | true edge |
|---|---|---|---|---|
| 2017 | +17.92 bp | −13.14 bp | −44.44 bp | **+31.06 bp** |
| 2018 | +22.84 bp | −16.36 bp | −55.06 bp | **+39.20 bp** |
| 2019 | +14.89 bp | −13.89 bp | −42.81 bp | **+28.78 bp** |

Random-sign trading of these same barriers **loses 13-16 bp**. Only the real
signal wins, and the inverted signal loses roughly twice as much as random.

## Where it actually stands

In-sample 2018 (`ks 3.5, stop 4σ_alt, target 2.5σ_alt, H 30m, 32 slots, 6bp`):

| metric | value | goal |
|---|---|---|
| win rate | **89.1%** | >80% PASS |
| ROI/month | **1931.3%** | >1000% PASS |
| max drawdown | **4.00%** | <4% PASS |

Out-of-sample, same parameters, never refitted:

| year | trades/mo | WR | EV | ROI/mo | DD | goals |
|---|---|---|---|---|---|---|
| 2017 | 1,546 | 72.90% | +23.52 bp | 23.0% | 4.00% | FAIL/FAIL/PASS |
| 2019 | 1,868 | **83.38%** | +15.51 bp | 289.6% | 4.00% | PASS/FAIL/PASS |

**All three goals are met in-sample on 2018 and are NOT met out-of-sample.**
2019 now passes win rate and drawdown; ROI is 3.5x short. That is the honest
state and it is not a pass.

## What the remaining gap is made of

The binding constraint is no longer edge, trade count, or drawdown control — it
is **independence**. 3,520 trades/month that are really ~1.64 independent bets
per signal cannot compound like 3,520 bets. Closing a 3.5x ROI gap needs
roughly 12x more *independent* streams, which means genuinely uncorrelated
impulse sources, not more altcoins reacting to the same BTC print.


---

# Iteration 3 — dynamic control, venue reality, and the exact target

## The goal restated as one measurable number

`ROI/month` and `max DD` both scale with leverage, so the pair collapses to a
single leverage-free ratio. Expressed in quantities the backtest can measure
directly:

```
edge per month      = trades_per_month  x  EV_per_trade
worst unlevered DD  = deepest peak-to-trough of the cumulative return sum
REQUIRED            edge_per_month / worst_unlevered_DD  >=  62.5
```

Measured with the locked config:

| year | edge/month | worst unlev. DD | ratio | need |
|---|---|---|---|---|
| 2018 | 566.2% | 16.69% | **33.9** | 62.5 |
| 2019 | 184.4% | 7.57% | **24.4** | 62.5 |
| 2020 | 253.2% | 31.81% | **8.0** | 62.5 |

## Data: 13 instruments, and a fresh untouched year

Second archive pulled the same way (264 MB via codeload):
`Vitaly007/Bitfinex-historical-data-AND-CryptoCompare-historical-data` —
BTC, ETH, LTC, XRP, EOS, IOT, NEO, **ETC, XMR, TRX, XLM, XTZ, BSV** through
2021-03. This adds six instruments and gives **2020 as a completely fresh
out-of-sample year** never touched during any tuning.

Effective independent bets rose from 1.64 (6 alts) to 1.85-2.31 (12 alts).

## Instruments that did not exist yet

Coverage by month exposed a serious flaw in the earlier 2017 results:

```
EOSUSD  0% of all minutes before 2017-07   (pair not listed)
NEOUSD  0% of all minutes before 2017-09   (pair not listed)
ETHUSD  27% in 2017-01, reaching 100% only by 2017-09
```

Backtesting a pair before the venue listed it is not a result, it is an
artifact. `liquidity.py` adds a causal tradability gate: an instrument is
tradable only after a full trailing window of continuous quoting. This is why
2017 is now excluded from headline results rather than reported.

## Dynamic leverage — the strategy forecasts its own regime

With static sizing, the single worst cluster of the year sets the exposure for
every other minute. Two measured facts justify a causal controller:
per-trade P&L autocorrelation is +0.16 to +0.39, and realised edge tracks
trailing BTC volatility at r = +0.835.

`control.py` combines inverse-vol sizing with an edge-state throttle, both
built only from already-realised trades. Effect at fixed DD = 4%:

| year | fixed | vol-target | edge-state | both |
|---|---|---|---|---|
| 2017 | 23.0% | 22.5% | 50.9% | **71.7%** |
| 2018 | 1931% | 1460% | **4385%** | 2971% |
| 2019 | 289.6% | 232.3% | 253.4% | **509.3%** |

## Current standing — parameters fixed on 2018 only

`ks 3.5, stop 2.5σ_alt, target 1.75σ_alt, H 60m, min_cov 0.30, 12 slots, 6bp`

| year | trades | WR | EV | ROI/month | DD | goals |
|---|---|---|---|---|---|---|
| 2018 (IS) | 33,425 | 91.50% | +20.24 bp | **12,591.9%** | 4.00% | PASS/PASS/PASS |
| 2019 (OOS) | 15,416 | **86.42%** | +14.30 bp | 403.0% | 4.00% | PASS/FAIL/PASS |
| 2020 (OOS) | 16,053 | **88.24%** | +18.83 bp | 162.4% | 4.00% | PASS/FAIL/PASS |

**Win rate and drawdown now PASS out-of-sample in every year.** ROI passes only
in-sample. The three goals are still not simultaneously met out-of-sample.

## The executable-leverage problem, stated plainly

The DD-constrained solver returns 26x-63x leverage, which implies gross
notional of ~25x equity. Bitfinex allowed roughly 3.3x on altcoin margin in
this period. Capping gross notional at real venue limits:

| gross cap | 2018 | 2019 | 2020 | DD range |
|---|---|---|---|---|
| 3.3x (real) | 80.4% | 22.9% | 30.2% | 0.51-1.18% |
| 5x | 144.2% | 36.6% | 49.0% | 0.77-1.78% |
| 10x | 493.6% | 86.3% | 121.5% | 1.54-3.55% |

At genuinely executable leverage the drawdown is far *inside* budget (0.5-1.2%
against a 4% allowance) and ROI is 23-80%/month. **Both statements are true and
must be reported together:** the strategy is much safer than required, and it
is well short of 1000%/month once leverage is constrained to what a venue
actually offered.

## The concentration failure, found and diagnosed

2020's entire 31.8% unlevered drawdown occurred in **under four hours** on
2020-11-24, across 62 trades, while BTC ran +3.33% at 2.2x normal volatility.
In that window the book opened **12 positions in a single minute — one in every
listed alt**. Twelve legs of one BTC impulse is one bet held twelve times.

Tested fix: share notional across the legs of each signal so one impulse equals
one unit of risk. **It made things worse** (2018: 12,592% to 431.8%), because
the legs are correlated but not identical — around 2.1 effective independent
bets, not 1.0. Full per-leg sizing is genuinely better. Reported as a negative
result rather than quietly dropped.

The drawdown governor was likewise tested and did **not** beat plain dynamic
sizing (5,290% vs 5,407% on 2018): throttling during recoveries costs more than
it saves.

## Honest status

| goal | 2018 (IS) | 2019 (OOS) | 2020 (OOS) |
|---|---|---|---|
| WR > 80% | PASS 91.50% | **PASS 86.42%** | **PASS 88.24%** |
| DD < 4% | PASS | **PASS** | **PASS** |
| ROI > 1000%/mo | PASS | FAIL 403% | FAIL 162% |

Two of three goals hold out-of-sample across two independent years. ROI remains
short by 2.5x-6x out-of-sample, and by far more at executable leverage.

The binding constraint is measured and specific: **~2.1 effective independent
bets per impulse.** Every altcoin on the venue reacts to the same BTC print, so
adding instruments raises trade count without raising independence. Closing the
remaining gap requires impulse sources that are genuinely uncorrelated with
each other, not more instruments reacting to one source.


---

# Iteration 4 — RETRACTION: I found a lookahead bug in my own engine

## What was wrong

`emit3.py` (and `emit.py`, `allsignals.py`, `altscaled.py` before it) computed

```python
r = np.diff(np.log(btc_close))     # r[k] = close[k+1] / close[k]
idx = np.flatnonzero(|r| > k*sigma)
st  = i + 1                        # entry at open[i+1]
```

`r[k]` needs `close[k+1]`. It is therefore **not observable until bar k+1 has
closed**. But `open[k+1]` occurs *before* `close[k+1]`. Every trade was entered
one bar before its own signal existed.

The earliest honest entry is `open[k+2]`. `emit4.py` implements that, and two
regression tests now pin the invariant so it cannot silently return.

## What it cost — measured, not estimated

Same parameters, same data, 2018, only the entry timing corrected:

| engine | trades | WR | EV/trade |
|---|---|---|---|
| `emit3` (lookahead) | 33,537 | 91.50% | **+20.24 bp** |
| `emit4` (causal) | 33,030 | 62.92% | **−2.06 bp** |

A cross-asset variant of the same signal showed the identical pattern:
+36.86 bp (t = +80.84) with lookahead, +5.10 bp (t = +12.08) causal.

**Every headline number in iterations 1-3 of this file is invalidated.** The
win rates of 86-91%, the ROI figures of 400-12,000%/month, and the claim that
"WR and DD now pass out-of-sample" were all produced by this bug. I am
retracting them rather than leaving them to stand.

## What is actually real

The lead-lag edge itself survives, and it is genuine. Entering at the first
observable open (`i+2`), 2018, per-instrument:

| alt | n | EV | t-stat |
|---|---|---|---|
| ETH | 7,086 | +4.60 bp | +11.74 |
| LTC | 6,135 | +4.70 bp | +10.45 |
| XRP | 6,935 | +4.19 bp | +5.06 |
| EOS | 6,718 | +4.70 bp | +9.88 |
| IOT | 6,202 | +9.62 bp | +15.75 |
| NEO | 5,719 | +10.33 bp | +18.24 |

Real, highly significant, and roughly **5x smaller** than the buggy version.

The consequence is decisive: a 4-10 bp edge against a 6 bp round-trip cost
leaves almost nothing. The best causal configurations found on 2018 reach
**WR ~72% and EV +15 bp**, and no configuration reaches WR > 80%.

## Also rejected this iteration

**Alt-own mean reversion** looked extremely strong — XLM −0.94σ, BSV −0.93σ,
TRX −0.53σ following their own impulses, firing at times 67-91% independent of
BTC impulses, which is exactly the uncorrelated source the strategy needs.

It is bid-ask bounce. Measured close-to-close it reverts; measured the only way
it can actually be traded (enter next open, exit the following open) the sign
**flips and becomes strongly negative**:

| alt | close→close | tradeable | ratio |
|---|---|---|---|
| XLM | +0.94 | −1.94 | −2.06 |
| BSV | +0.93 | −1.80 | −1.93 |
| IOT | +0.23 | −2.95 | −13.00 |
| NEO | +0.13 | −2.40 | −18.61 |

Rejected.

## Honest status after the fix

| goal | best causal result |
|---|---|
| WR > 80% | **FAIL** — ceiling ~72% |
| ROI > 1000%/mo | **FAIL** |
| DD < 4% | PASS (easily) |

The three goals are not met. The edge is real (t = +5 to +18, three years,
survives random-sign and inverted-sign controls) but at 4-10 bp it is of the
same order as the execution cost, which is exactly the wall found in earlier
work — now located precisely rather than argued.


---

# Iteration 5 — a causal configuration that clears WR > 80% out-of-sample

After removing the lookahead, the honest question became: can win rate exceed
80% while EV stays positive, using only observable information?

## Fair odds — the benchmark that makes WR meaningful

A random walk hitting a stop at `S` before a target at `T` wins with
probability `S/(S+T)`. So a high win rate proves nothing on its own; only the
excess over `R/(1+R)` is evidence of skill. Pooling all three years:

| stop/target R | fair WR | measured WR | edge | t |
|---|---|---|---|---|
| 2.0 | 66.67% | 71.10% | **+4.43 pp** | 4.55 |
| 3.0 | 75.00% | 76.61% | +1.61 pp | 1.80 |
| 4.0 | 80.00% | 80.63% | +0.63 pp | 0.77 |
| 5.0 | 83.33% | 83.28% | −0.05 pp | −0.06 |
| 6.0 | 85.71% | 84.40% | −1.32 pp | −1.82 |

At short horizons the edge decays to zero exactly where WR reaches 80%. That
looked like a wall. It was a horizon artifact: with `H = 60` minutes and very
wide stops, many positions never resolve.

## Timeouts, and why the reported WR is conservative

Classifying by gross outcome instead of net P&L:

| config | gross wins | gross losses | timeouts | resolved WR | fair |
|---|---|---|---|---|---|
| kst16 ktg1.5 | 83.2% | 3.8% | 13.1% | **95.68%** | 91.43% |
| kst16 ktg2.0 | 80.2% | 5.2% | 14.6% | **93.91%** | 88.89% |
| kst16 ktg1.0 | 87.9% | 2.6% | 9.6% | **97.14%** | 94.12% |

A timeout returns 0 gross and is therefore a small **loss** after the 6 bp
cost. The headline win rate counts every timeout as a loss, which is the
conservative choice and is kept.

## Result — parameters fixed on 2018, applied unchanged

`k_sigma 3.0, stop 16σ_alt, target 1.5σ_alt, H 60m, min_edge 3x cost, 12 slots, 6 bp`

| year | trades | trades/mo | WR | resolved WR | fair | edge | EV | ROI/mo | DD | goals |
|---|---|---|---|---|---|---|---|---|---|---|
| 2018 (IS) | 44,444 | 3,707 | **84.70%** | 96.57% | 91.43% | **+5.15 pp** | +11.43 bp | 78.3% | 4.00% | PASS/FAIL/PASS |
| 2019 (OOS) | 17,205 | 1,435 | **80.94%** | 95.49% | 91.43% | **+4.06 pp** | +6.24 bp | 19.3% | 4.00% | PASS/FAIL/PASS |
| 2020 (OOS) | 19,110 | 1,589 | **81.62%** | 93.75% | 91.43% | **+2.33 pp** | +4.05 bp | 9.3% | 4.00% | PASS/FAIL/PASS |

**Win rate above 80% and drawdown below 4% in all three years, including two
fully out-of-sample years, with strictly causal timing and a real edge over
fair odds.** This is the first configuration in this repository for which those
two goals hold without a lookahead bug.

## What still fails, and why

ROI is 9-78%/month against a 1000% target. The reason is arithmetic and is not
fixable by tuning: EV per trade is 4-11 bp, and the stop is 16σ_alt wide. One
loss erases roughly ten wins, so the drawdown constraint forces low leverage
even though losses are rare. High win rate and high ROI are in direct tension
here — the win rate is purchased with a very wide stop, and that same wide stop
caps the leverage.

`edge_per_month / worst_unlevered_DD` remains the single number to beat; it is
still well under the required 62.5.


## Iteration 5b — stand-down filter, and the exact arithmetic of the gap

Adding the causal stand-down (skip trades after 1 consecutive loss, resume
after a win) to the WR>80% configuration:

| year | trades/mo | WR | worst streak | ROI/mo | DD | goals |
|---|---|---|---|---|---|---|
| 2018 (IS) | 3,139 | **88.83%** | 7 | 173.4% | 4.00% | PASS/FAIL/PASS |
| 2019 (OOS) | 1,161 | **85.82%** | 7 | 31.7% | 4.00% | PASS/FAIL/PASS |
| 2020 (OOS) | 1,297 | **87.54%** | 7 | 27.0% | 4.00% | PASS/FAIL/PASS |

Worst losing streak drops from 11-16 to 7 in every year, win rate rises 4-6 pp,
and ROI roughly triples. **This is the best honest configuration found: WR and
DD pass in all three years, two of them fully out-of-sample.**

### Why ROI still cannot reach 1000%

The arithmetic is closed-form and leaves no room for interpretation.

To compound 11x in a month over `N` trades, each trade must add `f` to equity:

| trades/month | required f |
|---|---|
| 1,000 | 24.01 bp |
| 2,000 | 12.00 bp |
| 3,707 | 6.47 bp |
| 10,000 | 2.40 bp |

The drawdown cap sets a ceiling on that same `f`. With a worst losing run of
`L` trades at stop/target ratio `R`, survival requires `L * f * R <= 4%`:

| L | R | f_max |
|---|---|---|
| 5 | 10.7 | 7.48 bp |
| 10 | 10.7 | 3.74 bp |
| 20 | 10.7 | 1.87 bp |
| 5 | 2.0 | 40.00 bp |
| 10 | 2.0 | 20.00 bp |

The two requirements collide. `R = 10.7` is what buys WR > 80%; at the measured
streak of `L = 7` that allows `f_max ≈ 5.3 bp`, while `N = 3,139` trades/month
needs `f ≈ 7.6 bp`. Short by ~1.4x. Dropping to `R = 2` would allow a much
larger `f`, but then the win rate falls to ~67% and goal 1 fails.

**WR > 80% and ROI > 1000% at DD < 4% are in direct structural conflict for
this edge.** A high win rate is bought with a wide stop; a wide stop caps
leverage; capped leverage caps ROI. The measured ratio
`edge_per_month / worst_unlevered_DD` peaks at **1.59** against the **62.5**
required — a 39x gap, and it is largest precisely at the R that gives WR > 80%.


---

# Iteration 6 — a configuration that passed all three goals, and why I rejected it

## The result that looked like success

Pushing the stop far wider and adding the stand-down filter produced, at
strictly causal timing and executable leverage (3-6.8x):

`k_sigma 2.0, stop 48σ_alt, target 3σ_alt, H 120m, standdown 1, 16 slots, 6bp`

| year | trades/mo | WR | leverage | ROI/month | DD | goals |
|---|---|---|---|---|---|---|
| 2018 (IS) | 13,424 | 86.03% | 3.95x | 19,354% | 4.00% | PASS/PASS/PASS |
| 2019 (OOS) | 7,350 | 83.58% | 6.45x | 1,823% | 4.00% | PASS/PASS/PASS |
| 2020 (OOS) | 7,712 | 85.52% | 4.97x | 1,364% | 4.00% | PASS/PASS/PASS |

All three goals, all three years, two of them fully out-of-sample. I did not
report this as an achievement, because it fails the control.

## Why it is not real

Random-sign control on the identical barriers:

| year | real EV | **random-sign EV** | inverted EV |
|---|---|---|---|
| 2018 | +32.19 bp | **+27.82 bp** | +24.49 bp |
| 2019 | +18.92 bp | **+16.91 bp** | +15.16 bp |
| 2020 | +22.20 bp | **+20.59 bp** | +19.19 bp |

Trading a **coin flip** through these barriers earns +27.82 bp. Almost the
entire return is barrier geometry, not signal.

The mechanism, measured directly — how often each barrier is actually reached:

| config | target hit | **stop hit** | timeout |
|---|---|---|---|
| stop 48σ, target 3σ | 80.7% | **0.42%** | 18.9% |
| stop 16σ, target 1.5σ | 90.4% | 4.32% | 5.2% |
| stop 4σ, target 2σ | 73.4% | 26.53% | 0.1% |

A 48σ stop is hit 4 times in 1,000. It is not a stop — it is an unbounded tail
that the 120-bar horizon happens to truncate inside this sample. The strategy
is a short-volatility lottery: it collects a small target ~80% of the time and
the ruinous loss simply never appeared in three years. Sizing it at 4-6x
leverage against a 4% drawdown cap is a claim about a tail that has not been
observed, not a measurement.

**Rejected.** Passing the three stated goals while a coin flip passes them too
is not a solution.

## The honest alpha, isolated

Defining skill as `real EV − random-sign EV` on identical barriers removes the
geometry entirely and leaves only tradable information:

| stop/target | 2018 | 2019 | 2020 |
|---|---|---|---|
| 48σ / 3σ | +4.37 bp | +2.01 bp | +1.61 bp |
| 16σ / 1.5σ | +6.55 bp | +2.53 bp | +3.00 bp |
| 8σ / 2σ | +6.62 bp | +2.12 bp | +3.67 bp |
| 4σ / 2σ | +5.84 bp | +1.95 bp | +3.76 bp |
| 2σ / 2σ | +4.97 bp | +1.86 bp | +2.93 bp |
| 2σ / 1σ | +6.10 bp | +2.12 bp | +3.42 bp |

**Skill is +1.6 to +6.6 bp, positive in every configuration and every year.**
It is remarkably stable across barrier choices, which is what a genuine
information edge looks like — the signal is worth a fixed amount regardless of
how the position is wrapped.

The underlying physics is also stable, not decaying: pure causal lead-lag
strength `E[alt | BTC impulse] / σ_alt` measures 0.269 (2018), 0.217 (2019),
0.278 (2020).

## The wall, stated exactly

Real, causal, control-verified alpha: **+1.6 to +6.6 bp per trade.**
Round-trip execution cost on this venue: **6 bp** (20 bp taker, ~2 bp maker
only for rebate-tier participants who do not cross the spread).

A lead-lag strategy must cross the spread — it is reacting to information — so
it pays taker. The edge and the cost are the same order of magnitude. Every
configuration that appears to clear 1000%/month does so by taking unbounded
tail risk that a random signal exploits equally well.


---

# Iteration 7 — the cost assumption was wrong, and it is decisive

## I had been using 6 bp. The real number is 40 bp.

Bitfinex's published schedule for this period is **0.10% maker / 0.20% taker**,
with maker reaching 0.00% only above $7.5M of 30-day volume and taker never
falling below 0.055% (>$30B). Source: Bitfinex fee schedule as documented at
cryptototem.com/bitfinex-review and blockchaincenter.net.

Taker is therefore **20 bp per side = 40 bp round trip**, not the 6 bp I had
assumed throughout iterations 1-6. My cost assumption was **6.7x too
optimistic**, in the direction that flatters the strategy.

This is not a detail. The control-verified alpha is 1.6-6.6 bp per trade.

## Effective spread, measured from the data itself

Roll's estimator `s = 2*sqrt(-cov(dP_t, dP_{t-1}))` on real 1-minute closes,
2018:

| instrument | effective spread |
|---|---|
| EOS | 3.16 bp |
| LTC | 5.72 bp |
| IOT | 12.94 bp |
| NEO | 13.94 bp |
| XRP | 15.64 bp |
| ETH | n/a (positive autocovariance) |

So even before fees, crossing the spread costs 3-16 bp on these pairs. Adding
40 bp of taker fee puts total round-trip cost at roughly **43-56 bp**.

## The result at true cost

Same configuration, strictly causal, with the real 40 bp taker cost:

| year | trades/mo | WR | real EV | random EV | skill | ROI/mo | DD |
|---|---|---|---|---|---|---|---|
| 2018 | 713 | 90.13% | **+2.80 bp** | −9.01 bp | +11.81 bp | 9.2% | 4.00% |
| 2019 | 99 | 83.24% | **−6.32 bp** | −4.62 bp | −1.70 bp | 0.0% | 4.00% |
| 2020 | 311 | 89.64% | **−15.23 bp** | −26.45 bp | +11.22 bp | 1.6% | 4.00% |

**Net EV is negative in two of three years.** The win rate still reads 83-90%,
which is exactly why win rate alone is a misleading target: the strategy wins
often and loses more than it makes when it loses.

Note the skill column remains positive (+11.2 to +11.8 bp in 2018 and 2020) —
the *information* is real and survives at any cost level, because cost affects
the real and random arms identically. What does not survive is the *net*, and
only the net can be compounded.

## Where this leaves the three goals

| goal | status at true cost |
|---|---|
| WR > 80% | PASS (83-90%) |
| DD < 4% | PASS |
| ROI > 1000%/month | **FAIL** (0-9%) |

The binding constraint, measured rather than argued:

```
control-verified alpha    :  1.6 - 11.8 bp per trade
true round-trip cost      : 43 - 56 bp  (40 bp taker + 3-16 bp spread)
```

The edge is real, causal, stable across three years and every barrier
configuration, and confirmed by random-sign and inverted-sign controls. It is
also **roughly 5x smaller than the cost of executing it** on the only venue for
which this data exists.

Every configuration in this repository that appeared to reach 1000%/month did
so through one of four mechanisms, each identified and rejected in turn:
lookahead in the signal timing (iter 4), a stop so wide it is never hit
(iter 6), sizing that ignores concurrency, or an understated execution cost
(this iteration).


## Iteration 7b — maker execution tested and structurally ruled out

If taker cost (40 bp) is 5x the alpha, the obvious move is to stop paying it:
post passive limit orders and earn the maker rate instead.

Modelled honestly — post a limit `d*sigma` against our direction at the first
observable bar, fill only if price actually reaches it, unfilled means no trade:

| offset d | orders | fill rate | WR | EV (20 bp maker) |
|---|---|---|---|---|
| 0.5σ | 207,748 | 90.7% | 57.86% | **−22.53 bp** |
| 1.0σ | 200,044 | 87.4% | 57.72% | **−21.96 bp** |
| 2.0σ | 183,861 | 80.3% | 57.00% | **−21.35 bp** |
| 3.0σ | 168,149 | 73.4% | 56.38% | **−20.28 bp** |

Win rate collapses from ~88% to ~57% and EV is deeply negative at every offset.

### The reason, measured directly

Comparing the forward move of orders that **filled** against those that did not:

```
FILLED   orders : n = 136,172   mean forward move  -18.88 bp
UNFILLED orders : n =  19,591   mean forward move +235.36 bp
adverse selection penalty       =  254.24 bp
```

The passive order fills **only when the market comes back to it**, which is
precisely when the lead-lag move is not going to happen. When the signal is
correct the price runs away and the order never fills. We are systematically
picked off by the very information move we were trying to trade.

This is not a tuning problem. A signal that predicts imminent directional
movement **cannot** be executed passively, because the counterparty who fills
you is the one who knows the move is not coming. Lead-lag is intrinsically a
liquidity-taking strategy, and it must pay the taker fee.

**Both execution paths are therefore closed:**
- taker: 40 bp fee + 3-16 bp spread vs 1.6-11.8 bp alpha
- maker: 254 bp of adverse selection


---

# Iteration 8 — second-resolution real ticks, a cheaper venue, and a bias I caught in my own filter

## New real data: 5.46 GB of Binance trade ticks

`Nucs/cryptocurrency-ticks-data`, pulled through the same codeload path
(5,456,970,781 bytes). 591 daily files per symbol for BTC, NEO, BNB, QTUM,
ETH/BTC, LTC/BTC, spanning **2018-04-07 to 2019-11-18**.

Every row is a real executed trade:
`Id, time (ms), Price, Quantity, IsBuyerMaker, BuyerOrderId, SellerOrderId, IsBestPriceMatch`

The aggressor flag matters: it lets the effective spread be **measured from
real executions** instead of assumed. Built **12,360,326 one-second BTC bars**
across 197 days sampled evenly over the full span.

## Measured spread — my earlier assumption was too pessimistic here

Median touch spread from consecutive opposite-aggressor prints within 1 second:

| symbol | measured spread |
|---|---|
| BTCUSDT | **1.62 bp** |
| BNBUSDT | 3.53 bp |
| NEOUSDT | 4.83 bp |
| QTUMUSDT | 7.61 bp |

Binance 2019 spot fee was 0.10%/side, 0.075% with BNB. Total realistic
round-trip cost on this venue is roughly **15 bp**, against 43-56 bp on
Bitfinex. This is the cheapest execution available in any real data I can
reach, so it is the fairest possible test of the edge.

## A survivorship bias I introduced, found, and removed

Measuring the response at h = 1800 s, I required the exit second to have a
recent real print. That filter looked innocuous. It was not:

```
events passing ENTRY gate only          : 31,942
events also passing EXIT gate           :    630
exit gate discards                      :  98.03% of events
```

The discarded 98% are exactly the episodes where the alt stopped printing —
which correlates with the move failing. Effect on the measured edge:

| method | EV |
|---|---|
| with exit gate (what I first reported) | **+60.04 bp** |
| unbiased, exit at last real price | **+5.30 bp** |

An 11x overstatement. The +47 to +102 bp "skill" figures I had just produced
were this artifact. Corrected before drawing any conclusion from them.

## Unbiased result on real second-resolution ticks

All entry-gated events, exit at the last genuinely traded price in the window,
random-sign control on identical events:

| alt | k_sigma | H | n | real EV | random EV | skill | net after 15 bp |
|---|---|---|---|---|---|---|---|
| NEO | 4 | 300 s | 31,952 | +4.50 | −0.04 | +4.54 | **−10.50** |
| NEO | 6 | 1800 s | 6,639 | +10.35 | −4.15 | +14.51 | **−4.65** |
| BNB | 4 | 300 s | 38,298 | +2.46 | +0.02 | +2.44 | **−12.54** |
| BNB | 6 | 1800 s | 7,309 | +6.82 | −1.72 | +8.54 | **−8.18** |
| QTUM | 4 | 300 s | 20,489 | +6.07 | −0.24 | +6.31 | **−8.93** |
| QTUM | 6 | 1800 s | 4,792 | +14.14 | +1.67 | +12.47 | **−0.86** |

**Skill is real and positive everywhere (+2.3 to +14.5 bp), and net EV is
negative at every single setting.** The random-sign control is flat, confirming
the information is genuine rather than geometric.

## Two independent datasets, two venues, one answer

| measurement | Bitfinex 1-minute bars | Binance 1-second ticks |
|---|---|---|
| control-verified skill | 1.6 - 11.8 bp | 2.3 - 14.5 bp |
| true round-trip cost | 43 - 56 bp | ~15 bp |
| net | negative | negative |

Independent data, independent venue, 10x finer time resolution, 3x cheaper
execution — and the same conclusion, which is what makes it a measurement
rather than a fitting artifact.

Cutting cost by 3x did not rescue it because the signal shrinks with the
horizon needed to earn it: the BTC to altcoin impulse is worth roughly
**4-14 bp**, full stop. That is the physical size of the effect.


## Iteration 8b — order flow imbalance, tested at tick level and rejected

The tick data carries real aggressor flags, so order-flow imbalance (a
different signal from lead-lag) can be tested directly:

```
OFI_t = sum(signed_qty) / sum(qty)   over each 1-second bucket
        +1 = buyer aggressor (lifted the ask), -1 = seller aggressor (hit the bid)
```

Correlation of OFI with forward returns on real BTC ticks is consistently
**negative** at 1 second — aggressive flow mean-reverts:

| day | h=1s | h=5s | h=30s |
|---|---|---|---|
| 2019-02-15 | −0.277 | −0.198 | −0.067 |
| 2018-12-15 | −0.220 | −0.124 | −0.054 |
| 2019-10-15 | −0.142 | −0.053 | −0.014 |

### It is not bid-ask bounce

Recomputing against a bounce-free mid (mean of ask-prints and bid-prints within
each second, so the spread cancels) the effect **survives**: −0.303, −0.229,
−0.074 at h=1s. The correlation is genuine.

### But it is economically nil

Converting to basis points — trading against extreme OFI (|imbalance| >= 0.8),
entering the next second, exiting on mid:

| day | n | gross | net after 15 bp |
|---|---|---|---|
| 2019-02-15 | 44,146 | **−0.036 bp** | −15.04 |
| 2018-12-15 | 42,416 | **−0.073 bp** | −15.07 |
| 2019-05-15 | 49,823 | **−0.221 bp** | −15.22 |
| 2019-08-15 | 52,262 | **−0.149 bp** | −15.15 |
| 2019-10-15 | 51,171 | **−0.072 bp** | −15.07 |

A correlation of −0.30 that is worth **0.04 bp** is the clearest possible
demonstration that statistical significance and economic significance are
different things. With ~50,000 observations per day, a tiny mean is enormously
significant and still worth nothing. The reversion is real, sub-tick, and
entirely inside the spread.

