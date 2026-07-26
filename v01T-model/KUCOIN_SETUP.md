# KuCoin Futures setup — automatic v01T execution

## Why KuCoin

v01T needs three things at once, and KuCoin is the only widely-accessible
option for Nigerian users that has all three:

| Requirement | KuCoin |
|---|---|
| Perpetual futures with leverage | yes |
| Working trading API | yes |
| **Hedge mode (dual-side)** | yes — **switchable over the API**, not UI-only |

MEXC is often recommended for Nigeria, but **its futures API has been disabled
since July 2022**, so no bot can trade there. Binance ended naira services in
March 2024 and is in litigation with the Nigerian government.

## The one thing that must be right: HEDGE MODE

v01T uses **double entry** — every elite squeeze opens **both** a long and a
short leg at the same price:

```
LONG  leg:  side buy,  positionSide long,  SL -0.05%, TP +0.50%
SHORT leg:  side sell, positionSide short, SL +0.05%, TP -0.50%
net: +0.50% - 0.05% = +0.45% x 50 leverage = +22.5% of capital
```

In **one-way mode** those two orders net to zero exposure and the model cannot
function. `--preflight` sets hedge mode and refuses to trade without it.

## 1. Account

1. Create a KuCoin account and complete KYC with your Nigerian ID.
2. Open a **Futures** account and transfer USDT into it.
3. Start on the **sandbox** if you want a dry environment first.

## 2. API key

KuCoin → API Management → Create API

* Permissions: **General** + **Futures Trading**
* **Withdrawals: OFF** — never enable them for a bot
* Bind the key to your **IP address**
* KuCoin requires **three** secrets, not two: key, secret **and passphrase**
* API key version **2** (the default for new keys)

## 3. Environment

```bash
export KUCOIN_API_KEY=your_key
export KUCOIN_API_SECRET=your_secret
export KUCOIN_API_PASSPHRASE=your_passphrase
export KUCOIN_SANDBOX=1        # 1 = sandbox (default), 0 = live
```

Never commit these. `.gitignore` already covers `.env`.

## 4. Verify before trading

```bash
python run_kucoin.py --preflight
```

Checks connectivity, market data, contract specs, credentials, **hedge mode**
and leverage. Exit code `0` only when every check passes.

## 5. Run

```bash
python run_kucoin.py                    # paper  — no exchange contact
python run_kucoin.py --mode dry_run     # real data + keys, orders logged NOT sent
V01T_LIVE=I_UNDERSTAND python run_kucoin.py --mode live
```

Progress in this order: paper, dry-run, sandbox live, then mainnet.

## Sizing: contracts, not coins

KuCoin futures trade in **integer contracts**. For `XBTUSDTM` one contract is
`multiplier` BTC (0.001 by default):

```
contracts = floor( notional / price / multiplier )
```

Sub-contract precision is impossible, so a small account can round to zero. The
executor **refuses** in that case rather than sending a malformed order.

## Risk rails

Enforced in every mode (`v01t/kucoin_executor.RiskLimits`):

* max concurrent squeezes
* max daily loss %
* max notional per leg
* minimum free balance
* kill switch
* **emergency flatten** — if the second leg fails to place, both sides are
  closed immediately so the account never holds one naked leg

## Files

| File | Purpose |
|---|---|
| `v01t/kucoin.py` | KuCoin Futures V1/V2 client: base64 HMAC signing, klines, hedge mode, leverage, bracketed orders. Stdlib only; HTTP layer injectable |
| `v01t/kucoin_executor.py` | Signal to double entry, contract sizing, modes, risk rails |
| `run_kucoin.py` | CLI |
| `tests/test_kucoin.py` | 37 tests: signing, hedge mode, both legs, contract sizing, rails, preflight |

## Nigeria — read this

* Nigeria's **Investments and Securities Act 2025** classifies digital assets
  as securities under SEC oversight; platforms serving Nigerian users are
  expected to be **SEC-licensed**. Only Quidax and Busha hold provisional
  licences, and neither offers futures — so they cannot run v01T.
* KuCoin is **not** SEC-licensed in Nigeria. Using it carries regulatory risk:
  possible banking friction, domain blocks, and no local legal recourse.
* **Crypto gains became taxable in Nigeria in 2026.** Keep records from the
  first trade.

## Honest limits

* The backtest books a win when price moves 0.5% either way **without checking
  whether the 0.05% stop was hit first on the path**. Live, both legs sit only
  0.05% from entry, so a small oscillation can stop both before the move
  develops. Expect live results to differ from the backtest.
* Four fills per squeeze (two legs in, two out) at 50x leverage is a material
  cost against a +22.5% target.
* **Run sandbox/paper long enough to see real fills** and compare with the
  backtest before risking funds.
