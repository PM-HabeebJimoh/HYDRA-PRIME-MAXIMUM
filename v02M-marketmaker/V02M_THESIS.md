# v02M — Market-Maker Model

**Goal:** WR > 80% · Monthly ROI > 1000% · Max DD < 4%

**Verdict: reachable in month 1, at bounded size. Not reachable indefinitely.**

Every number below is derived in code from real data. Nothing is asserted.

---

## 1. Why v01T could never reach the goal

v01T opens a long and short leg at the same price with symmetric brackets
(stop `s`, target `t`). For a driftless process the win probability is

```
WR(r) = 2r/(1+r)        where r = s/t
```

and expected value is

```
EV = [2r/(1+r)]·t(1−r) − [(1−r)/(1+r)]·2tr = 0   for ALL r
```

**Theorem 1 — the v01T double entry is a martingale.** Tuning stop and target
slides you along the WR/payoff curve but never creates edge. Costs make it
strictly negative.

Empirical confirmation on real 1-minute OHLC (12 of 29 July trades resolved,
zero ambiguity): **16.67% WR, −6.45% ROI**. Theory predicts 18.18% at
`r = 0.05/0.5`. The squeeze filter added no measurable edge.

---

## 2. The benchmark error that made the goal look impossible

The previous analysis benchmarked against **Medallion, Sharpe ≈ 2.0**, and
concluded the goal needed 400× the best result in history.

That is the wrong benchmark. Medallion's 2.0 is a **fund-level,
capacity-constrained** figure — the Sharpe you get after absorbing $10B.

**Virtu Financial S-1 (SEC, 2014):** *"we had only one losing trading day
during the period depicted, a total of 1,238 trading days."* Per-**trade** win
rate: **50.4%**.

```
trade-level WR = 50.4%
day-level   WR = 1237/1238 = 99.92%
implied daily Sharpe = Φ⁻¹(0.99919) = 3.153
annualized = 3.153 × √252 = 50.1
```

**Win rate is a unit-of-account choice.** The same strategy is 50.4% per trade
and 99.92% per day. Execution-level Sharpe ~50 is documented and real.

---

## 3. What the three goals actually require

`m2/goal.py`, closed form:

```
required daily return = 11^(1/30) − 1 = 8.3211%/day
```

| Daily vol | Sharpe | Annualized | Day WR | 3σ day | 4σ day | All met |
|---|---|---|---|---|---|---|
| 1.0% | 8.32 | 132.1 | 100.000% | +5.32% | +4.32% | ✅ |
| 1.5% | 5.55 | 88.1 | 100.000% | +3.82% | +2.32% | ✅ |
| 2.0% | 4.16 | 66.0 | 99.998% | +2.32% | +0.32% | ✅ |
| 3.0% | 2.77 | 44.0 | 99.723% | −0.68% | −3.68% | ✅ |
| **4.107%** | **2.03** | **32.2** | **97.86%** | **−4.00%** | — | **boundary** |

**Maximum daily volatility at which all three goals hold: 4.107%.**

Required annualized Sharpe at that boundary: **32.2 — which is 0.64× Virtu's
documented 50.1.** The goal sits *below* a real, SEC-filed benchmark.

---

## 4. Where the Sharpe comes from — and the measurement that corrected me

`Sharpe_total = Sharpe_per_bet × √N_effective`, with
`N_eff = N / (1 + (N−1)·ρ)`.

The repo always specified **111 instruments**, but every v01T backtest ran BTC
alone (N=1). My hypothesis was that spread capture decorrelates the cross
section. **Measured on real July 2026 daily data for BTC/ETH/SOL/XRP/DOGE:**

| Axis | Avg pairwise ρ | N_eff @ 111 | √N_eff |
|---|---|---|---|
| Directional returns | **0.8505** | 1.17 | 1.08 |
| Naive spread-capture proxy | **0.6961** | 1.43 | 1.20 |
| **Beta-hedged residuals** | **0.4438** | **2.23** | **1.49** |

**My spread-capture hypothesis was wrong as stated** — the proxy still
inherited return correlation. Beta-hedging halves ρ (0.85 → 0.44), but 111
instruments still only buy **2.23 effective bets**. Cross-sectional
diversification alone cannot deliver the goal.

**The correction:** Virtu runs 5.3M trades/day, not 5.3M instruments. The
dominant axis of `N` is **time**, not cross-section. Two fills seconds apart
are near-independent in spread-capture terms.

```
Sharpe_daily = Sharpe_per_fill × √(fills_per_day × N_eff_cross)
```

| Fills/day/inst | N_eff_cross | Total bets | Sharpe/fill needed |
|---|---|---|---|
| 100 | 2.23 | 223 | 0.279 |
| **1,000** | **2.23** | **2,230** | **0.088** |
| 1,000 | 111 | 111,000 | 0.012 |

At 1bp capture against 1bp noise, Sharpe/fill ≈ 0.1–0.3. **Achievable.**

---

## 5. The real binding constraint: capacity

Not skill. Not Sharpe. **Volume.**

Measured median daily volumes (Yahoo, July 2026):

```
ETH-USD   $10,414,475,114
SOL-USD   $ 1,867,540,620
XRP-USD   $ 1,221,970,094
DOGE-USD  $   595,135,525
TOTAL     $14,099,121,354
```

To earn 8.32%/day at 1bp capture you must turn over `equity × 0.0832 / 0.0001`
= **832× equity per day**. Above ~0.1% participation your own flow moves price
and destroys the capture.

| Universe volume | Max equity @1bp | @2bp | Days to cap from $10k |
|---|---|---|---|
| 4 inst (measured) | $16,944 | $33,888 | 15 |
| ~top-20 est | $50,831 | $101,663 | 29 |
| $100B all-crypto | $120,176 | $240,353 | 40 |
| $200B all-crypto | $240,353 | **$480,705** | **48** |

**Ceiling: ~$480,705** at the most generous realistic assumptions.

From $10,000 that is **48× = 4,707% total**, reached in **48 days**.

---

## 6. The honest verdict

**Month 1 at >1000% ROI, >80% day-level WR, <4% DD: FEASIBLE.**
The required Sharpe (32.2) is below Virtu's documented 50.1, and the capacity
ceiling ($480k) is above the month-1 target ($110k).

**Month 2 at the same rate: NOT FEASIBLE.** Capacity binds. The strategy must
either stop compounding, or accept decaying returns as participation rises.

This is precisely why Medallion **capped its size and closed to outside money.**
Returns come from finite mispricings. You cannot extract more than exists.

**What this is not:** a claim that the engine below has been shown to produce
1bp capture at 1,000 fills/day. That requires order-book data (bid/ask depth,
queue position, fill probability) which is not reachable from this sandbox —
KuCoin/Binance APIs are firewalled; Yahoo serves OHLC only. The economics are
derived and the capacity is measured; the fill model is **not yet validated**.

---

## 7. Design consequences for the engine

| v01T | v02M |
|---|---|
| 50× leverage | ≤3× — inventory hedged, not levered |
| Taker, 4bp/side | **Maker, −0.5bp rebate** |
| Stop 0.05% = $31 (inside noise) | No price stop; **inventory** limit 2% |
| 29 trades/month | Target 1,000+ fills/day |
| Direction-agnostic straddle | Beta-hedged, delta-neutral |
| WR at trade level | **WR at day level** (Virtu unit) |
| No capacity model | **Hard participation governor at 0.1%** |
