# iter69 — what was structurally WRONG with every formula I built

## Error 1 — I predicted the sign of a quantity smaller than the noise floor

Target was `sign(close[i+1] − open[i+1])`, a **1-minute** move.
Measured: BTC median 1-minute move = **1.09 bp**. BTC spread = **1.649 bp**.

**The thing I was predicting is smaller than the cost of trading it.** Even a perfect
oracle on that target loses money. No formula can fix a target chosen below the noise floor.

## Error 2 — fixed-horizon sign is not a trade

"Will the next candle close up?" is not an order you can place. A real trade is:
enter, then **either a target or a stop is reached first**. The outcome is
**path-dependent**, and the path is exactly what I was throwing away by using
close-to-close (which is also what let bid-ask bounce fake an 87%).

## Error 3 — I forced a prediction on every bar

Every bar got a prediction, so accuracy was diluted by thousands of no-information bars.
A tradable system fires rarely and abstains by default.

## Error 4 — I never separated PAYOFF STRUCTURE from PREDICTIVE EDGE

This is the deepest one, and it is why "85%" was never going to arrive from tuning.

For a driftless random walk with target `+a·σ` and stop `−b·σ`:

        P(hit target first) = b / (a + b)

So **85% win rate requires no skill at all** — set `a = 0.5σ`, `b = 3σ`:

        P = 3 / 3.5 = 85.7%

…and expectancy is exactly zero: `0.857 × 0.5σ − 0.143 × 3σ = 0`.

**Any "85% accuracy" system that does not state its barrier ratio is reporting
geometry, not skill.** I could have hit 85% at any point by widening the stop, and it
would have been worthless. The only number that means anything is:

        EDGE = P_observed − b/(a+b)

## The corrected design — TRIPLE BARRIER, tradable by construction

1. **Entry** at the *next* bar's OPEN (never the signalling bar's close).
2. **Barriers** from trailing volatility σ (causal): target `+a·σ`, stop `−b·σ`.
3. **Resolution** by walking forward through subsequent bars' HIGH/LOW.
4. **Pessimistic tie-break**: if a bar touches both barriers, assume the **STOP** filled.
5. **Timeout** after N bars → exit at close.
6. **Costs** charged on entry and exit.
7. **Abstain** unless the signal is in its extreme tail.
8. **Report `P − b/(a+b)`**, never raw WR alone.

This is the correction: the outcome *is* the trade, the path is respected, bounce cannot
contaminate it, and skill is measured against the geometric baseline instead of hidden by it.
