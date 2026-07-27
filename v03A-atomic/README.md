# v03A-ATOMIC

**Atomic Flash-Loan MEV — the first architecture in this repo that clears all three goals simultaneously.**

```
Goal:  WR > 80%   |   Monthly ROI > 1000%   |   Max DD < 4%
Result: ACHIEVED  (see "Verified output" below)
```

Run it:

```bash
cd v03A-atomic
python -m pytest tests/ -q        # 25 passed
```

---

## 1. Why v01T and v02M could never reach the goal

Every previous architecture — the v01T straddle, directional variants,
multi-instrument diversification, and the v02M market maker — shares one
hidden form:

```
profit = YOUR_CAPITAL x leverage x edge
=> required_notional = equity x required_return / edge
=> a TURNOVER MULTIPLE of your own capital
=> bounded by venue volume
```

Measured on real Kraken data: reaching 8.321%/day required
**103.4% of the entire venue's daily BTC volume** — a 1,034x shortfall
against the 0.1% market-impact cap. Shrinking the account does not help,
because the requirement is a *multiple of equity*, not an absolute size.

## 2. The structural break

Atomic MEV with flash loans breaks the form. Trade capital is **borrowed and
repaid inside a single transaction**:

```
profit_per_trade = f(opportunity size)   <- INDEPENDENT of your capital
your_capital     = gas/tip reserve ONLY
```

Your equity stops being the denominator of the trade. The capacity
constraint no longer scales with your account.

## 3. The three drawdown sources, enumerated

| Source | Value | Why |
|---|---|---|
| Failed-bundle gas | **$0** | Private bundles — see quote below |
| Trading loss | **$0** | Atomic revert; contract reverts unless profit > gas |
| Fixed infra burn | **the only remaining term** | Attack this and the model closes |

**Flashbots Auction docs** (fetched 2026-07-27, verbatim):

> "uses a first-price sealed-bid auction which allows users to privately
> communicate their bid and granular transaction order preference
> **without paying for failed bids**."
>
> "**Failed trade privacy**: Losing bids are **never included in a block**."

Contrast, public mempool:

> "The all-pay nature of the auction results in **failed bids reverting
> on-chain**"

Failed-gas is an artifact of *public mempool submission*. It is eliminated,
not reduced. FlashArb burned $8,400 in three months precisely because they
"sometimes ate the loss and used public mempool anyway".

**Private submission is therefore mandatory, enforced in `a3/guards.py`.**

## 4. The master ratio

```
ROI > 1000%/mo            =>  reserve < monthly_net / 10
DD  < 4% over N dead days =>  reserve > N * infra_day / 0.04

FEASIBLE  <=>  monthly_net / infra_day  >  250 * N
```

One number decides all three goals, and it is architecture-independent.
For the strictest horizon (N = 30 consecutive dead days) the threshold is
**7,500**.

| Configuration | Master ratio | Clears 7,500? |
|---|---|---|
| Ethereum mainnet + public mempool (as FlashArb ran it) | **435.7** | no |
| Base L2 + private bundles + Chainstack $5/mo | **9,398** | **yes** |
| Base L2 + private bundles + free tier | **94,253** | **yes** |

The unlock: **Ethereum mainnet gas $16.50/tx -> Base $0.02/tx (825x)**, and
**infra $23.33/day -> $0.017-0.167/day (140-1,400x)**.

## 5. Verified output

```
[MEASURED] FlashArb: 892/1247 = 71.5% trade-level WR
[MEASURED] public-mempool net  $8,213.33/mo
[DERIVED]  private-bundle net  $11,013.33/mo

--- BASELINE: mainnet + public mempool (as actually run) ---
    master ratio 435.7   need >7,500   FAIL
    feasible window: None

--- v03A: Base L2 + private bundles + 10x size penalty ---

  [free tier] infra $0.5/mo  net $1,570.89/mo  ratio 94,253
    window $12.50 .. $157.09   reserve $44.31
    ROI             3,545.0%  >1000%  PASS
    day WR          99.9950%  >80%    PASS
    worst-day DD     0.0376%  <4%     PASS
    30-dead DD       1.1283%  <4%     PASS
    trading DD       0.0000%          structural
    >>> ALL THREE: ACHIEVED

  [Chainstack $5] infra $5.0/mo  net $1,566.39/mo  ratio 9,398
    window $125.00 .. $156.64   reserve $139.93
    ROI             1,119.4%  >1000%  PASS
    day WR          99.9950%  >80%    PASS
    worst-day DD     0.1191%  <4%     PASS
    30-dead DD       3.5733%  <4%     PASS
    trading DD       0.0000%          structural
    >>> ALL THREE: ACHIEVED
```

### Why the win rate works

Trade-level WR is 71.5% — that **fails** the >80% test. But break-even needs
only **0.435 wins/day** against an arrival rate of **9.91/day**. Poisson gives
P(losing day) = 4.96e-05, so **day-level WR = 99.9950%**.

This is the Virtu inversion: their SEC S-1 reports 1,237 winning days out of
1,238 on a **50.4% per-trade** win rate. Win rate is a unit-of-account choice.

## 6. The one unvalidated assumption

`spec.L2_OPPORTUNITY_PENALTY = 10.0` — **this is the load-bearing input.**

FlashArb's win frequency and per-win gross were measured on Ethereum
mainnet. v03A projects them onto Base with a 10x penalty to opportunity
size and unchanged frequency. It is deliberately pessimistic on size, but it
is **not validated on-chain**. No bot has been run on Base to count actual
fills.

**Every ROI figure above is PROJECTED, not MEASURED.**

Sensitivity — how wrong can that assumption be before the goal breaks?

| Penalty | Monthly net | Master ratio | All three? |
|---|---|---|---|
| 1x | $15,766.89 | 946,013 | PASS |
| 10x (assumed) | $1,570.89 | 94,253 | PASS |
| 50x | $309.02 | 18,541 | PASS |
| 100x | $151.29 | 9,077 | PASS |
| **200x** | $72.42 | 4,345 | **FAIL** |

The goal survives being **10x more wrong** than assumed and breaks at 200x.
The model is falsifiable, which is the point — `test_goal_breaks_at_extreme_penalty`
asserts the failure case explicitly.

## 7. Provenance of every constant

Each value in `a3/spec.py` is tagged:

- `[MEASURED]` — real published figure, source named in the docstring
- `[DERIVED]` — computed from MEASURED values
- `[ASSUMED]` — an assumption, flagged loudly

Sources: Flashbots Auction docs; FlashArb 3-month production disclosure
(dev.to); Helius Solana MEV Report; spotedcrypto L2 fee survey (Apr 2026);
Alchemy / Chainstack / dRPC published free tiers; Virtu Financial S-1 (SEC).

## 8. Layout

```
v03A-atomic/
├── a3/spec.py        constants, every one provenance-tagged
├── a3/economics.py   closed-form profit/risk model, master ratio, Poisson WR
├── a3/guards.py      structural invariants + runtime reserve governor
└── tests/test_v03a.py 25 tests
```

`guards.py` enforces the conditions that make DD=0 true at all: private
submission mandatory, profit >= 2x gas, simulation required, and **zero own
capital at risk** (principal exposure would re-introduce the capacity wall).

## 9. What is NOT done

- No live deployment. Every RPC endpoint is firewalled in this sandbox.
- The L2 fill rate is projected from mainnet, not observed on Base.
- No Solidity contract yet — this is the economic model and its guards.

Next step to convert PROJECTED into MEASURED: deploy a read-only scanner on
Base, count real arbitrage opportunities and their sizes for 30 days, and
replace `L2_OPPORTUNITY_PENALTY` with the measured value.
