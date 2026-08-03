# iter64 — FIRST PRINCIPLES: what actually causes a price to move

The user is right that I was fitting a temporary pattern. XEX-D's edge (Binance
leads Bitfinex by ~1 minute) is a LATENCY ARBITRAGE. Latency gaps close as
infrastructure improves. That is why it worked in 2018-19 and is dead in 2026 —
it was never a permanent cause, it was a temporary plumbing defect.

## Step 1: what is a price?

A price is the last point where a buyer and a seller agreed. It moves when
someone must transact at a worse price than the current one. So:

    PRICE MOVES <=> SOMEONE IS FORCED TO TRADE WITHOUT REGARD TO PRICE

Not "when news is good". News that everyone can price causes no move — it is
already in the book. The move comes from FORCED, PRICE-INSENSITIVE FLOW.

## Step 2: who is ever forced to trade, and why?

This is the real question. Every one of these is a PERMANENT feature of market
structure, not a temporary anomaly. They exist because of law, contract, or
mandate — they cannot be arbitraged away.

| # | Forced actor | What forces them | Is it knowable IN ADVANCE? |
|---|---|---|---|
| 1 | Leveraged longs/shorts | Liquidation engine hits maintenance margin | **YES** — open interest + funding + the liquidation price is a published formula |
| 2 | Index funds | Index reconstitution — must own the new weight at the close | **YES** — index rules are public, announced days ahead |
| 3 | ETF issuers | Creation/redemption to track NAV | **YES** — daily flows published |
| 4 | Options market makers | Delta-hedging a gamma position as spot moves | **YES** — full option chain OI is public |
| 5 | Futures holders | Contract expiry / roll | **YES** — calendar is fixed years ahead |
| 6 | Miners / validators | Must sell to pay energy costs in fiat | **YES** — on-chain flows to exchanges are visible |
| 7 | Token unlocks | Vesting cliff — contractual | **YES** — vesting schedules are in the contract |
| 8 | Margin/collateral calls | Cross-asset stress forces sales of the LIQUID asset | Partly |
| 9 | Month/quarter-end rebalance | Pension mandate: restore 60/40 | **YES** — calendar |
| 10 | Stablecoin issuers | Mint/burn to hold peg | **YES** — on-chain |

## Step 3: the key insight

Items 1-7 and 9-10 share one property: **the FORCING EVENT IS PUBLISHED BEFORE
IT HAPPENS**, but the RESULTING FLOW is not yet in the price, because the forced
party cannot act early without revealing itself or breaching mandate.

That is a PERMANENT, STRUCTURAL gap. It does not decay with technology, because
it is created by law and contract, not by latency.

The temporary version I was chasing: "who moved first?"
The permanent version:            "who MUST move next, and when, and how much?"

## Step 4: strongest single candidate — #1, LIQUIDATION CASCADES

Why this one first:
 - The trigger price is DETERMINISTIC and computable: a position at leverage L
   opened at P is liquidated at P*(1 - 1/L) (long). Not a forecast — arithmetic.
 - The forced flow is MARKET orders (liquidation engines do not post limits).
 - It is SELF-REINFORCING: each liquidation pushes price into the next cluster.
 - The inputs are PUBLIC and free: open interest, funding rate, long/short ratio,
   and the exchange's own published liquidation feed.
 - It happens in crypto CONTINUOUSLY (24/7 perpetuals, 100x leverage available).

## Step 5: what data would prove or kill it — the full list

ON-CHART / MARKET:
  - 1m OHLCV                                    (have: Bitfinex, Kraken, mirror repo)
  - open interest per instrument, 1m/5m         (Bitfinex derivatives status endpoint)
  - funding rate, 8h + predicted                (Bitfinex, OKX)
  - long/short account ratio                    (Binance - geo-blocked; OKX)
  - **actual liquidation prints**               (Bitfinex /v2/liquidations/hist - PUBLIC)
  - order book depth / bid-ask                  (Kraken, Bitfinex)

OFF-CHART / OUTSIDE THE MARKET ENTIRELY (the user's point):
  - token unlock calendars                      (vesting contracts, public)
  - index reconstitution schedules              (index provider announcements)
  - futures expiry calendar                     (CME/Deribit, fixed)
  - miner treasury flows                        (on-chain, public nodes)
  - stablecoin mint/burn                        (on-chain)
  - macro release calendar                      (central bank sites)
  - energy prices (miner cost basis)            (EIA)
  - grid/weather events affecting mining        (NOAA)

## Step 6: the ONE testable claim

  Liquidation clusters are computable in advance from public open interest and
  leverage data. Price is ATTRACTED to them, and the move THROUGH a cluster is
  larger and more directional than a normal move.

If true: a permanent, structural, non-decaying edge, knowable before it happens.
If false: kill it and move to candidate #4 (options gamma).

NEXT: check which of these endpoints is actually reachable, then test the claim.
