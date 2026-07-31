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
