# v01T-max2 — real-OHLC rebuild of v01T, and the measured verdict

## Headline

**The three targets were NOT achieved. They cannot be, at any edge measured on real data.**

| Target | Result | Status |
|---|---|---|
| WIN RATE > 80% | 72.44% (walk-forward) | **FAIL** |
| MONTHLY ROI > 1000% | 14.23% (at DD cap) | **FAIL** |
| MAX DRAWDOWN < 4% | 4.00% | PASS |

Iteration 2 went further and showed the residual edge is **not real**: it is directional
exposure that reverses sign in a down month (§4). Zero of 32 configurations are profitable
in both June 2026 (−16.29%) and July 2026 (+10.20%).

Iteration 3 then removed beta *by construction* with a market-neutral ETH/BTC spread
(residual beta −0.034). The edge vanished with it: best t = +1.10, ROI 11.64% at the DD
cap (§5). Three independent architectures now converge on the same ≈12–15%/month ceiling.

Iteration 4 left price history entirely and tested **order flow** — real Kraken tape with
aggressor flags, the data that is causally upstream of the print. Flow's price impact is
real and contemporaneous (positive in all 4 windows) but has **no forward lead** (sign
flips), and the 26bp taker fee is 40x the entire measured signal (§6).

Iteration 5 found a **genuinely real edge** — cross-venue mechanical forcing between
Coinbase and Kraken: 92.31% win rate, t = +6.03, surviving VWAP re-specification. It
fails anyway: both passive legs fill only 3.8% of the time, one crossed leg costs 26bp
against a 1.3bp edge, and even at zero cost the ceiling is 350%/month (§7).

Iteration 5 reached **Deribit** (previously assumed unreachable) and tested funding — real
positioning data. The headline r=-0.487/t=-3.66 was a false positive caused by +0.962
funding autocorrelation; corrected to non-overlapping windows it is n=12, t=-1.27, not
significant (§7).

Reproduce: `python3 run_backtest.py` · Verify: `pytest tests/ -q` (40 passing)

## The data — 100% real, no substitutions

- **601 Coinbase `BTC-USD` 1-hour OHLC bars, 2026-07-01 → 2026-07-26, zero gaps.**
- **241 Coinbase `BTC-USD` 1-hour OHLC bars, 2026-06-01 → 2026-06-11, zero gaps** (the down-month control).
- **130 aligned ETH-USD + BTC-USD 6-hour bars, 2026-06-24 → 2026-07-27, zero gaps** (the market-neutral pair).
- **184 real Kraken BTC/USD ticks with aggressor flags + 100 Kraken 1m VWAP bars** (the order-flow test).
- **100 timestamp-matched Coinbase + Kraken 1m bars, 2026-07-28** (the cross-venue test).
- **106 real Deribit BTC-PERPETUAL hourly funding + index prints, July 2026** (the positioning test).
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

### 4. The July "edge" was drift capture — it dies in a down month

This is the finding that closes the loop. Iteration 1 measured a walk-forward edge of
t = +4.28 and Sharpe 14.84 and called it real. It was not. Inspecting *what the
walk-forward actually selected* showed it converged on **`signal = all`, long, stop 4.0%,
target 1.0%** — i.e. **always-long BTC with a wide stop**, in a month that rose 10.20%.

So I pulled a second real month with the opposite sign: **June 2026, −16.29%**
(241 Coinbase 1h OHLC bars, zero gaps) and applied the identical rule.

| month | drift | n | WR | EV/trade | result |
|---|---|---|---|---|---|
| July 2026 | +10.20% | 280 | **81.07%** | **+0.4537%** | profit |
| June 2026 | −16.29% | 100 | **61.00%** | **−0.7384%** | **LOSS** |

Across the full grid of signal × barrier × side, **0 of 32 configurations were profitable
in both months**. And the mechanism is exact:

```
EV / drift ratio    July +0.0445    June +0.0453
```

EV is a near-constant fraction of the month's drift. That is the algebraic signature of
**pure directional exposure — beta, not alpha**. The strategy has no predictive content.

The win rate confirms it: at stop 4% / target 1%, WR > 80% appears **long in July and
short in June**. It attaches to whichever side matches the drift, and it is manufactured
by the 4:1 barrier ratio either way.

### 5. Iteration 3 — removing beta by construction also removes the "edge"

Iteration 2 showed the edge was directional beta. So iteration 3 built a strategy where
**beta cannot exist**: trade ETH against a beta-weighted BTC hedge, so the common dollar
move cancels algebraically instead of by luck. Data: 130 aligned 6h Coinbase bars
(ETH-USD and BTC-USD, 2026-06-24 → 07-27), hedge ratio from a rolling 40-bar OLS using
**only past returns**.

The hedge works exactly as intended:

| | beta vs BTC |
|---|---|
| raw ETH | **+1.19** |
| hedged spread | **−0.034** |

And with beta gone, so is the profit. Every variant collapses to noise:

| rule | hold | n | WR | EV/trade | t |
|---|---|---|---|---|---|
| z < −1.0 long | 4 | 10 | 60.00% | +0.3129% | **+1.10** |
| z > +1.0 short | 4 | 9 | 33.33% | −0.1030% | −0.27 |
| z < −1.0 long | 1 | 13 | 53.85% | −0.0644% | −0.53 |

Best case t = +1.10 — indistinguishable from zero. The spread is not mean-reverting
either: lag-1/2/3 autocorrelations are −0.039, −0.005, −0.071, all |t| < 1.

At the DD < 4% cap this yields **+11.64% ROI** and a **60.00% win rate**. That ceiling
(≈12–15%/month) is now the *third independent* architecture to land in the same place.

**A bug I made and fixed.** My first neutral backtest showed −0.95%/trade on *both*
directions, with t = −9.47. A symmetric strategy cannot lose both ways — that is
arithmetically impossible from the market, so it had to be my code. It was: the z-score
included the entry bar's own return, so the signal peeked at the bar it traded. Fixed to
use bars strictly before entry, and the false −0.95% became honest noise. Two tests
(`test_hedge_beta_uses_no_lookahead`, `test_zscore_uses_no_lookahead`) now corrupt the
entry bar and assert the signal is unchanged, so this cannot silently return.

### 6. Iteration 4 — order flow: the data that IS upstream of price

Iterations 1–3 all used price history, which is the most competed-away data that exists.
Iteration 4 goes after data that is **causally upstream of the print**: aggressive orders
consume resting liquidity, and *then* price moves. Real Kraken BTC/USD tape with true
aggressor flags (`b`/`s`) and order type (`m` market / `l` limit), 184 ticks across two
independent windows, plus 100 1-minute bars carrying VWAP and trade count.

Signed order-flow imbalance `OFI = (buy_vol − sell_vol)/total`:

| window | contemporaneous r | predictive r (next window) |
|---|---|---|
| 10s | **+0.102** | −0.045 |
| 15s | **+0.195** | +0.241 |
| 20s | **+0.303** | −0.204 |
| 30s | **+0.171** | −0.309 |

**The result is a clean split, and it is the most informative thing in this whole repo:**

- **Contemporaneous correlation is positive in all four windows.** Order flow genuinely
  moves price. The physical mechanism the user described is real and measurable.
- **Predictive correlation flips sign** (2 of 4 positive). No stable lead exists. Every
  |t| < 2.7 (Bonferroni for 8 tests).

Market-orders-only at 10s shows lag-0 r = **+0.724, t = +2.57** — strong *impact*, and
still no forward edge (lag-1 t = +0.41).

**Why this closes the "know before the move" thesis on public data.** Price impact is
*simultaneous with the trade*, not before it. By the time a trade prints on the public
tape, the liquidity it consumed is already gone and the quote has already moved. To
monetise impact you must be the resting liquidity that gets hit — which is a latency and
colocation race, not a signal anyone can compute from a public feed.

And the economics are decisive:

```
best-case signal    0.65 bp   (largest |r| x typical 10s move)
effective spread    0.02 bp   (measured from aggressor-side flips)
Kraken taker fee   26.00 bp   round trip
```

The fee is **40x** the entire information content of the flow. VWAP position within the
bar — where volume actually transacted — shows nothing forward either (all |t| < 1).

### 7. Iteration 5 — funding/positioning, and a false discovery I caught in myself

The thesis is *knowing direction before the market reacts*. The strongest candidate in
public data is **positioning**, because forced liquidations are mechanically determined:
when price touches a level, those orders **must** execute. Funding rate reads leverage
imbalance directly — positive funding means longs pay shorts, i.e. crowded long and
vulnerable to a forced unwind.

I had previously claimed these APIs were unreachable. That was an assumption, not a test.
**Deribit is reachable.** Real BTC-PERPETUAL hourly funding + index price, July 2026,
two contiguous 53-hour segments (106 rows).

**The first result looked like the discovery of the whole project:**

```
funding(t) vs index return over next 8h:   r = -0.487,  t = -3.66
```

Negative, exactly as the crowded-long thesis predicts, and apparently significant.

**It is an artifact.** Funding has lag-1 autocorrelation **+0.962** — it barely changes
hour to hour. So overlapping 8-hour windows are not 90 independent observations; they are
the same observation counted ~8 times, which inflates the t-statistic by roughly √8 ≈ 2.8.

| test | n | r | t |
|---|---|---|---|
| overlapping, 1 segment | 45 | −0.487 | **−3.66** |
| overlapping, both segments | 90 | −0.282 | −2.76 |
| **non-overlapping (honest)** | **12** | −0.372 | **−1.27** |
| non-overlapping, k=4 | 26 | −0.001 | −0.00 |

Corrected, there is no significant effect. And even at face value the economics fail:
0.279%/8h gross → 24%/month at 1×; reaching +1000% needs **11.2× leverage**, where a
single adverse 1-sigma 8-hour move costs **8% of equity** — double the entire 4% drawdown
budget, on one bar.

Tests encode the trap itself (`test_overlapping_windows_inflate_significance`,
`test_funding_is_highly_autocorrelated`) so this false positive cannot recur.

### 7. Iteration 5 — cross-venue mechanical forcing: a REAL edge, killed by execution

Iterations 1–4 hunted for *statistical tendencies*. This one hunts a **mechanical
constraint**: when Coinbase and Kraken disagree on BTC at the same instant, arbitrage
capital **must** close the gap. That is enforced by economics, not by a pattern.

Data: **100 timestamp-matched 1-minute bars**, real Coinbase BTC-USD and real Kraken
XBT/USD, 2026-07-28 02:55–04:34 UTC. Cross-venue gap: mean −0.13bp, sd 1.03bp, range
−2.94 to +3.16bp.

**The gap is forced closed, exactly as the physics predicts:**

```
regress Δgap on gap level:  r = -0.6305   t = -8.00
decay coefficient -0.8048   half-life 0.42 bars (~25 seconds)
```

**And fading it works:**

| threshold | n | win rate | mean gross | t |
|---|---|---|---|---|
| 1.0 bp | 26 | **92.31%** | +1.3258 bp | **+6.03** |
| 1.5 bp | 14 | **100.00%** | +1.9057 bp | +6.48 |
| 2.0 bp | 6 | **100.00%** | +2.5630 bp | +6.37 |

**This is the first genuine edge in the entire repo.** It is not drift (the gap is
two-sided and zero-mean), not beta (both legs are the same asset), and not a close-print
artifact — it *survives* re-specification against Kraken VWAP at **t = +7.79**.

**So why is the answer still FAIL? Execution — measured, not assumed.**

*1. The dual-maker assumption fails.* Capturing 1.3bp requires posting passively on both
venues and having **both** legs fill. On real data, of 26 episodes with a >1bp gap:

| outcome | count | share |
|---|---|---|
| **both** legs moved favourably | 1 | **3.8%** |
| only **one** leg moved | 24 | **92.3%** |
| neither | 1 | 3.8% |

92.3% of the time you get one fill and hold **naked directional risk** on the unhedged
leg — reintroducing precisely the beta that killed iterations 1–3.

*2. Costs exceed the edge by 20–100×.* Public entry-tier taker fees:

```
gross edge                        1.33 bp
ONE crossed leg (Kraken 26bp)   -24.67 bp
full taker round trip (132bp)  -130.67 bp
```

*3. Even free execution misses the target.* Granting 0bp cost — physically impossible —
the 1bp threshold fires ~11,345 times/month at 1.33bp, compounding to **350%/month**,
still short of 1000%, and that ignores capacity entirely (the gap is ~1bp deep; size it
up and you *are* the gap).

**What this proves.** "Know the direction before the market reacts" is real and I found
it: the lagging venue is mechanically pulled to the leader, with a 25-second half-life
and 92% reliability. It is unmonetisable at retail because the information is worth
1.3bp and the cheapest way to act on it costs 26bp. The edge exists; it is *already
owned* by whoever has co-located infrastructure and zero-fee maker tiers.

## What this says about v01T

- v01T's gate (`BB% < 10 or > 90` and `HV ratio < 0.8`) has **no edge**: on real OHLC it is
  *worse* than taking every bar (`test_v01t_gate_not_better_than_baseline`).
- v01T's 100% win rate came from counting a bar that spans both barriers as a win. Here such
  a bar is booked a **loss** (`ambiguous_loss`), because at 1h resolution the intrabar order is
  genuinely unknowable. That single correction is the difference between fantasy and honesty.
- July 2026 BTC rose **+10.20%**. Long beat short for *every* signal tested — that is the
  month's drift, not skill. Any "edge" not benchmarked against it is measuring the calendar.

## Honest limits of this result

- Two months, one instrument. The regime test is the strongest evidence here: an edge that
  reverses sign with market direction is beta, and no amount of tuning converts beta to alpha.
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
vmax2/regime.py     up-month vs down-month test: separates real edge from drift capture
vmax2/neutral.py    market-neutral ETH/BTC spread: removes beta by construction
vmax2/orderflow.py  Kraken tape with aggressor flags: impact vs prediction, and fees
vmax2/crossvenue.py Coinbase-vs-Kraken matched bars: real edge, execution-infeasible
vmax2/funding.py    Deribit funding: positioning signal, and the autocorrelation trap
run_backtest.py     the full report reproduced above
tests/test_vmax2.py 40 tests: data integrity, resolution honesty, the disjointness proof
data/               601 real July-2026 + 241 real June-2026 Coinbase bars
```

`v01T-model/` is unmodified.
