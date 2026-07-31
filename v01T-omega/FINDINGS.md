# v01T-OMEGA — consolidated findings

All numbers below are measured on **real market data only**. No synthetic
series, no simulated prices, no assumed fills. Two independent archives, both
pulled in-session over `codeload.github.com`:

| archive | bytes | content |
|---|---|---|
| `Zombie-3000/Bitfinex-historical-data` | 535,697,080 | 1-minute OHLCV, 7 instruments, 2013-2019 |
| `Vitaly007/Bitfinex-...-CryptoCompare-...` | 264,523,225 | 1-minute OHLCV, 13 instruments, to 2021-03 |
| `Nucs/cryptocurrency-ticks-data` | 5,456,970,781 | Binance trade ticks with aggressor flags, 2018-04 to 2019-11 |

Roughly **9.4 M one-minute bars** and **12.4 M one-second bars** built from
real executed trades.

## The three goals

| goal | best honest result | status |
|---|---|---|
| Win rate > 80% | 88.83% (2018), 85.82% (2019), 87.54% (2020) | **achieved** |
| Max drawdown < 4% | 4.00% by construction, 0.5-1.2% at real leverage | **achieved** |
| Monthly ROI > 1000% | 9-78% at true cost | **not achieved** |

Win rate and drawdown are met simultaneously, out-of-sample, on causal data.
ROI is not, and I could not make it so without an artifact.

## Every mechanism tested, and its measured verdict

| # | mechanism | result | verdict |
|---|---|---|---|
| 1 | BTC→alt lead-lag, 1 m bars | skill +1.6 to +6.6 bp | real, below cost |
| 2 | Same, 1 s ticks | skill +2.3 to +14.5 bp | real, below cost |
| 3 | Straddle (original v01T) | 62% double-stopped | fails |
| 4 | Alt-own mean reversion | flips sign when traded | bid-ask bounce |
| 5 | Order-flow imbalance | corr −0.30, worth 0.04 bp | sub-tick |
| 6 | Cross-venue arbitrage | net −11 bp, t = −3.07 | fails at full sample |
| 7 | Maker execution | −254 bp adverse selection | structurally impossible |
| 8 | Wide-stop configs | random sign earns the same | barrier geometry |

## Five artifacts I found in my own work and removed

Each of these produced an apparent pass. Each was caught by me, on real data,
and is documented rather than shipped.

1. **Lookahead in signal timing.** `r[k]` needs `close[k+1]`, so entering at
   `open[k+1]` trades before the signal exists. Correcting it: WR 91.50% → 62.92%,
   EV +20.24 → −2.06 bp.
2. **A stop hit 0.42% of the time.** A 48σ stop is not a stop; it is an
   unbounded tail truncated by the horizon. A coin flip through the same
   barriers earned +27.82 bp against the signal's +32.19 bp.
3. **Exit-gate survivorship.** Requiring a fresh print at the exit second
   discarded 98.03% of events — precisely those where the move failed.
   EV +60.04 → +5.30 bp.
4. **Overlapping trades compounded on one capital slot**, and ROI annualised on
   bar count rather than calendar time (2019: 3,891%/mo → 64%/mo).
5. **Execution cost understated 6.7x.** I used 6 bp; Bitfinex taker is 20 bp
   per side, 40 bp round trip.

## The binding constraint, measured on both venues

```
                        Bitfinex 1 m bars    Binance 1 s ticks
control-verified skill   1.6 - 11.8 bp        2.3 - 14.5 bp
measured spread          3 - 16 bp            1.6 - 7.6 bp
fee round trip           40 bp                15 bp
net                      negative             negative
```

Independent data, independent venue, 10x finer resolution, 3x cheaper fees —
the same answer. The BTC→altcoin impulse is physically worth **4-14 bp**, and
that is smaller than the cost of taking it.

## What is genuinely real and reproducible

- A causal BTC→altcoin lead-lag edge, **t = +5 to +18** per instrument,
  positive in 2017, 2018, 2019 and 2020, stable across every barrier choice,
  confirmed by random-sign and inverted-sign controls.
- Cross-venue convergence: **corr(z, Δz) = −0.409** at 15 minutes, with 30-44%
  of any dislocation recovered within 30 minutes.
- Both are real. Neither is larger than its execution cost.

---

# Iteration 10 — the assumption I had never questioned

Every previous iteration used **BTC as the only signal source**. That was never
tested; it was inherited from the original v01T spec and I carried it for nine
iterations without asking why.

With 13 instruments there are not 12 relationships but **156 directed pairs**.

## Measuring all of them

Source impulse (3σ, causal) → destination move, entry at the first observable
open, 2018, real Bitfinex 1-minute data:

| EV | t | src → dst | n |
|---|---|---|---|
| +22.85 bp | 12.46 | BTC → XLM | 1,118 |
| +21.66 bp | 12.00 | ETH → XLM | 1,119 |
| +21.52 bp | **25.21** | BTC → TRX | 3,899 |
| +18.45 bp | 22.35 | ETH → TRX | 4,220 |
| +17.94 bp | 18.76 | XRP → TRX | 3,546 |

**All 129 measurable pairs are positive.** And BTC is not the best leader:

| source | mean EV across destinations |
|---|---|
| LTC | **+11.40 bp** |
| ETH | +11.00 bp |
| BTC | +10.50 bp |
| EOS | +9.03 bp |
| ... | ... |
| BSV | +1.55 bp |

The effect is a market-wide propagation from liquid to illiquid, not a
BTC-specific phenomenon. My nine-iteration assumption was wrong — and
correcting it did not change the magnitude, only the explanation.

## Consensus across sources

Counting how many of the 12 sources fired in the same direction, then trading
the agreed direction in every destination:

| year | consensus ≥ 5 | consensus ≥ 8 |
|---|---|---|
| 2018 | +6.01 bp | **+8.94 bp** |
| 2019 | +4.36 bp | +7.72 bp |
| 2020 | +4.90 bp | +7.32 bp |

Stable in all three years and monotone in agreement — a genuine aggregation
effect.

### Another survivorship bias, caught

Restricting to the 118 signals where **all 12 destinations were simultaneously
liquid** gave a basket EV of **+45.84 bp**. That filter is the same class of
error as iteration 8: simultaneous liquidity across every instrument is itself
a market condition. Averaging instead over whatever destinations are actually
present (what a real desk does) collapses it:

| year | consensus ≥ 8, n | real EV | random EV | skill |
|---|---|---|---|---|
| 2018 | 2,181 | +7.57 bp | −1.33 bp | +8.90 bp |
| 2019 | 1,308 | +4.91 bp | +1.49 bp | +3.42 bp |
| 2020 | 2,101 | +4.45 bp | −1.04 bp | +5.49 bp |

Effective independent bets across 12 legs: **1.85**.

## Six independent routes, one number

| measurement | edge |
|---|---|
| BTC→alt, Bitfinex 1 m bars | 4.2 - 10.3 bp |
| BTC→alt, Binance 1 s ticks | 2.5 - 14.1 bp |
| All 129 directed pairs | 1.6 - 11.4 bp |
| Consensus of 12 sources | 2.4 - 7.6 bp |
| Cross-venue dislocation | 1.9 - 10.5 bp |
| Order-flow imbalance | 0.04 bp |

Different venues, different resolutions, different mechanisms, different
statistical methods. They all return **2-14 bp**. That is not a limitation of
my search; it is the measured size of the phenomenon.

## Solving backward from the goal — cost is NOT the constraint

I had been treating execution cost as the blocker. Solving the goal equation
backward says otherwise:

| assumed cost | net EV | max leverage at DD<4% | ROI/month |
|---|---|---|---|
| 15 bp (Binance real) | −7.4 bp | — | unprofitable |
| 5 bp | +2.6 bp | 1.08x | 5.2% |
| 0 bp (free) | +7.6 bp | 1.08x | 16.1% |
| **−2.5 bp (paid to trade)** | +10.1 bp | 1.08x | **21.9%** |

**Even being paid 2.5 bp per trade, the ceiling is ~22%/month** — and at the
highest-frequency variant, ~68%/month. Removing cost entirely does not reach
1000%.

## The actual binding constraint

```
information ratio per trade = EV / sd
consensus>=8 : 7.6 / 74  = 0.1027  -> monthly Sharpe 1.39, annualised 4.80
consensus>=5 : 4.8 / 100 = 0.0480  -> monthly Sharpe 1.43, annualised 4.95
BTC->alt 1s  : 14.1 / 120 = 0.1175 -> monthly Sharpe 4.55, annualised 15.76
```

ROI > 1000%/month at DD < 4% requires a return/drawdown ratio of 250, which
demands an annualised Sharpe of roughly **60-100**.

| strategy | annualised Sharpe |
|---|---|
| S&P 500 | ~0.4 |
| Renaissance Medallion | ~2.0 |
| Elite HFT market maker | ~8.0 |
| **measured here** | **4.8 - 15.8** |
| **required for the goal** | **~60-100** |

The measured Sharpe of 4.8-15.8 is genuinely good — better than Medallion,
comparable to elite HFT at the 1-second variant. It is 4-20x short of what the
stated goal requires, and the shortfall is in the **signal-to-noise ratio of
the underlying market physics**, not in cost, leverage, trade count, or
execution.

---

# Iteration 11 — I derived the goal exactly, and my previous claim was wrong

## Correcting myself

In iteration 10 I asserted the goal "requires annualised Sharpe ~60-100". That
number came from a hand-waved proportionality, not a derivation. **It was
wrong.** Here is the exact result.

For log-equity as a drifted random walk with per-trade drift `m` and dispersion
`s`, the maximum-drawdown law is `P(maxDD > d) = exp(-2md/s²)`, so
`E[maxDD] = s²/(2m)`. With leverage `L` on a trade of net edge `e` and
dispersion `v`: `m = Le`, `s = Lv`, hence `E[maxDD] = Lv²/(2e)`.

A drawdown cap `D` therefore permits `L = 2De/v²`, and total log return over
`N` trades is `N·L·e = 2D·N·(e/v)² = 2D·Sharpe²`. So:

```
        ln(1 + ROI) = 2 · D · Sharpe²
```

That single line **is** the goal. At `D = 0.04`:

| target ROI/month | required monthly Sharpe | annualised |
|---|---|---|
| 100% | 2.94 | 10.20 |
| 300% | 4.16 | 14.42 |
| **1000%** | **5.47** | **18.97** |

The requirement is **annualised Sharpe 19.0**, not 60-100. I overstated the
difficulty by 3-5x.

## Measured against it

18,482,807 real 1-second BTC bars over 296 days, all directed pairs, entry at
the first observable second (t+2), random-sign control on every row:

| src → dst | h | N/month | EV | sd | IR | random |
|---|---|---|---|---|---|---|
| BTC → QTUM | 60 s | 3,086 | +4.64 bp | 44.6 | **0.1040** | −0.21 |
| BTC → NEO | 60 s | 4,835 | +3.74 bp | 42.6 | 0.0877 | +0.34 |
| BTC → QTUM | 60 s | 8,271 | +3.18 bp | 40.1 | 0.0792 | −0.11 |
| BTC → NEO | 60 s | 14,160 | +2.48 bp | 37.7 | 0.0657 | +0.11 |

Applying the exact law at **zero cost**:

| src → dst | N/month | IR | monthly Sharpe | implied ROI |
|---|---|---|---|---|
| BTC → QTUM | 3,086 | 0.1040 | 5.78 | **1,343%** |
| BTC → NEO | 4,835 | 0.0877 | 6.10 | **1,860%** |
| BTC → QTUM | 8,271 | 0.0792 | 7.20 | **6,240%** |
| BTC → NEO | 14,160 | 0.0657 | 7.82 | **13,188%** |

**At zero execution cost the goal is comfortably exceeded.** The physics of the
signal is sufficient. Everything now reduces to one question: what does it cost
to trade?

## The exact cost budget

Solving backward for the maximum cost that still yields Sharpe 5.475:

| src → dst | N/month | EV | required net | **max affordable cost** |
|---|---|---|---|---|
| BTC → QTUM | 3,086 | 4.64 bp | 4.40 bp | **0.24 bp** |
| BTC → NEO | 4,835 | 3.74 bp | 3.36 bp | **0.38 bp** |
| BTC → QTUM | 8,271 | 3.18 bp | 2.42 bp | **0.76 bp** |
| BTC → NEO | 14,160 | 2.48 bp | 1.73 bp | **0.74 bp** |

The goal is reachable if and only if round-trip execution costs **under about
0.24 to 0.76 bp**.

## The hard floor, measured from real executions

Touch spread from consecutive opposite-aggressor prints within 1 second,
median across six sample days:

| instrument | touch spread = taker round-trip floor |
|---|---|
| BTCUSDT | **1.52 bp** |
| BNBUSDT | 3.62 bp |
| NEOUSDT | 4.39 bp |
| QTUMUSDT | 5.30 bp |

**Even with a zero exchange fee**, a liquidity taker pays the half-spread on
entry and again on exit. The cheapest instrument floor is 1.52 bp against a
budget of 0.24-0.76 bp — short by 2-6x.

## Where this actually lands

The blocker is now identified precisely, and it is neither the signal nor the
leverage nor the trade count:

```
signal physics at zero cost  : 1,343% - 13,188% / month   GOAL EXCEEDED
budget for execution         : 0.24 - 0.76 bp round trip
cheapest taker floor (real)  : 1.52 bp  (BTC touch spread)
shortfall                    : 2 - 6x, in the spread alone
```

A taker cannot reach it. The only remaining path is to **earn** the spread
rather than pay it — i.e. post passively and be a maker. Iteration 7b measured
that path and found −254 bp of adverse selection when posting on the signal
side, because the counterparty who fills you is the one who knows the move is
not coming.

So the honest statement is sharper than before: **the goal is achievable on the
measured signal physics, and is blocked entirely by a 1.52 bp spread against a
0.76 bp budget.**

## Iteration 11b — asymmetric execution tested

If the spread is the entire blocker, the natural move is to pay it only once:
enter as a taker (the signal is urgent, so crossing is unavoidable) but exit
passively as a maker, earning the half-spread back.

Measured honestly — post the exit limit and check whether real prices actually
reach it, counting unfilled positions at their true mark:

| dst | h | n | exit fill rate | EV on filled | **EV on all** |
|---|---|---|---|---|---|
| QTUM | 60 s | 30,012 | 71.0% | +2.09 bp | **−4.19 bp** |
| QTUM | 300 s | 30,012 | 86.1% | +2.04 bp | **−5.42 bp** |
| NEO | 60 s | 47,013 | 79.1% | +1.93 bp | **−3.16 bp** |
| NEO | 300 s | 47,013 | 90.2% | +1.90 bp | **−3.63 bp** |
| BNB | 300 s | 56,757 | 91.1% | +1.83 bp | **−2.11 bp** |

The passive exit fills 71-91% of the time and looks profitable on those fills.
But the 9-29% that do not fill are precisely the cases where price moved
against the position, and they carry losses large enough to make the full
sample negative. This is the same adverse-selection asymmetry measured in
iteration 7b (−254 bp), now quantified on the exit leg: **selection into fills
is not free, and conditioning on fills is the survivorship error again.**

## Final position

```
required monthly Sharpe (derived exactly)   : 5.475
measured monthly Sharpe (real 1s data)      : 5.78 - 7.82     GOAL MET on physics
implied ROI at zero cost                    : 1,343% - 13,188% / month
cost budget to preserve that                : 0.24 - 0.76 bp round trip
cheapest measured taker floor (BTC spread)  : 1.52 bp
maker alternative                           : negative after adverse selection
```

The signal is strong enough. The arithmetic of drawdown and leverage is
satisfied. The trade count is sufficient. The single unresolved term is a
**1.52 bp spread against a 0.76 bp budget** — a factor of 2, in the one
quantity that is a property of the market's microstructure rather than of the
strategy.

---

# Iteration 12 — the extreme tail: where fixed cost stops mattering

I had stopped at "the spread is 2x the budget" without testing the obvious
consequence of cost being **fixed per trade**: if the edge grows with impulse
size, a big enough impulse makes 11.52 bp irrelevant.

Processed **all 591 days** of real Binance ticks by streaming (the full panel
exhausts memory), extracting **1,549,072 impulse events** with impulse sizes
from 3σ to **140.8σ**.

## Edge does scale with impulse size

Real cost applied throughout: 1.52 bp measured spread + 10 bp Binance
round-trip fee = **11.52 bp**.

| impulse z | h | n | gross | **net after 11.52 bp** |
|---|---|---|---|---|
| 3-4 | 300 s | 509,510 | +1.65 bp | −9.87 |
| 4-6 | 300 s | 206,186 | +3.06 bp | −8.46 |
| 6-10 | 300 s | 44,701 | +5.54 bp | −5.98 |
| 10-20 | 300 s | 6,592 | +8.06 bp | −3.46 |
| **20-40** | 300 s | 863 | **+29.03 bp** | **+17.51** |
| **40+** | 300 s | 169 | **+22.33 bp** | **+10.81** |

The edge is roughly **linear in impulse size**, and above z≈20 it clears the
fixed cost decisively. This is the first genuinely profitable configuration
found on real data with fully honest costs.

## It survives every test I could apply

| test | result |
|---|---|
| significance at z>=20, h=300 | net +16.42 bp, **t = 5.11** |
| random-sign control | +1.09 bp (flat) |
| NEO independently | +20.64 bp, t = 3.83 |
| QTUM independently | +19.79 bp, t = 3.22 |
| BNB independently | +9.34 bp, t = 1.79 |
| **first half of sample** | **+16.66 bp, t = 3.74** |
| **second half of sample** | **+16.17 bp, t = 3.50** |

Two chronological halves give +16.66 and +16.17 bp — almost identical. This is
a real, stable, out-of-sample profitable edge after real costs.

## And it still does not reach the goal

Applying the exact law `ln(1+ROI) = 2·D·Sharpe²`:

| z >= | h | N/month | net | IR | monthly Sharpe | ROI/month |
|---|---|---|---|---|---|---|
| 15 | 300 s | 116 | +7.03 bp | 0.0710 | 0.76 | 4.8% |
| **20** | 300 s | 53 | **+16.42 bp** | **0.1591** | 1.16 | **11.4%** |
| 25 | 300 s | 30 | +14.14 bp | 0.1395 | 0.77 | 4.8% |
| 30 | 300 s | 19 | +14.27 bp | 0.1401 | 0.61 | 3.0% |

Scanning **every** threshold from 3σ to 40σ at both horizons, the maximum
achievable monthly Sharpe is:

```
OPTIMUM: z >= 22.5, h = 60 s
  790 events, 41 trades/month, net +11.45 bp, IR 0.2080
  monthly Sharpe 1.33  ->  ROI 15.12% / month
  required for the goal: Sharpe 5.475
```

## The exact tradeoff, stated as a law

`Sharpe = IR · √N`. Raising the threshold raises IR (0.048 → 0.208, a 4.3x
improvement — the best information ratio measured anywhere in this project) but
collapses N (1,549,072 → 790 events, a 2,000x reduction). √N falls faster than
IR rises.

```
edge quality   : IR 0.208 at z>=22.5   (excellent - Medallion-class per trade)
edge frequency : 41 trades/month       (the binding constraint)
product        : Sharpe 1.33
required       : Sharpe 5.475
shortfall      : 4.1x in Sharpe = 17x more trades at the same quality
```

To reach 1000%/month I would need **~700 trades/month at IR 0.208**. The real
market supplies 41. Extreme dislocations of 20+ sigma are rare by definition —
that rarity is what makes them profitable after fixed costs, and simultaneously
what prevents them from compounding to the target.
