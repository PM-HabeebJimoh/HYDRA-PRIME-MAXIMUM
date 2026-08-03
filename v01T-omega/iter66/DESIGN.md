# iter66 — CSS v10.0 METHODOLOGY applied to DIRECTION prediction

## The lesson I missed twice

CSS v10.0 is not a bankruptcy dataset. It is a **METHOD**:

1. **Enumerate INDEPENDENT signal families.** CSS has Sovereign / Credit /
   Operational / Absence. They come from *different institutions* — IRS, banks,
   labour dept, GitHub. An error in one cannot cause an error in another.
2. **Score each family separately**, with an explicit weight and a lead time.
3. **REQUIRE CONVERGENCE.** 3+ independent absences, or 1 traditional + 2
   absences. One signal alone is NEVER enough — that is the whole trick.
4. **PERSISTENCE CHECK.** The state must hold N days before firing.
5. **CONTRADICTION CHECK.** Emergency funding detected → nullify.

**Why this beats a single model:** if each family is only 60% right but they are
*independent*, requiring 3 to agree gives far higher precision. CSS gets 92%
precision from signals that are individually weak. That is Bayes, not magic.

## What I did wrong in iter1-65

My "15-feature" model had **15 features all computed from PRICE**:
`disloc10/30/60`, `disloc_z`, `binance_ret`, `bfx_ret`, `btc_ret`, `sig`, `zvol`...
Those are not 15 signals. They are **one signal (price) measured 15 ways.**
Correlated errors → no convergence benefit → 54.74% WR.

CSS would call that a single Tier. I never built Tiers 2, 3, 4.

## The CSS-style architecture for DIRECTION

Target: **sign of the next N-minute return**, but only when families CONVERGE.

| Tier | Family | Institution / origin | Independent of price? |
|---|---|---|---|
| **T1 SOVEREIGN** | Cross-venue dislocation | *other exchange's* matching engine | partly |
| **T2 CREDIT** | Order-flow imbalance (aggressor) | *traders' urgency*, from tick tape | **YES** — flow ≠ price |
| **T3 OPERATIONAL** | Cross-asset lead (BTC hub) | *a different asset entirely* | **YES** |
| **T4 ABSENCE** | Liquidity/quote absence | *market makers withdrawing* | **YES** — the CSS innovation |

**Tier 4 is the one I never built.** CSS's core insight is that the *absence* of a
mandatory flow is the strongest predictor. For a 1-minute bar the mandatory flows are:
- trades must print (a live market trades) → **trade-count collapse**
- both sides must quote → **one-sided flow** (all buys, no sells)
- volume must be non-zero → **volume drought**

A minute where liquidity has withdrawn is a minute where the next move is LARGE
and DIRECTIONAL, because there is nothing to absorb the next order.

## Convergence rule (mirrors CSS Path B)

```
absences = [T2_extreme, T3_extreme, T4_absence, T1_extreme]
if count(absences) >= 3 and persistence >= 2 bars and not contradiction:
    fire
```

## The honest test

- Walk-forward, train on past only.
- Report per-signal precision AND convergence precision.
- **The prediction CSS makes:** convergence precision >> any single signal.
  If that is false on real data, the method does not transfer and I say so.
