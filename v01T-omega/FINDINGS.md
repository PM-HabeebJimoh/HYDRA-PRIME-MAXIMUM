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
