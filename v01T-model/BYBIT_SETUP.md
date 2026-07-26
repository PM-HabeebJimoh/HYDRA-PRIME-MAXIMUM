# Bybit setup — automatic v01T execution

## The one thing that must be right: HEDGE MODE

v01T uses **double entry** — every elite squeeze opens **both** a long and a
short leg at the same price:

```
LONG  leg:  side Buy,  positionIdx 1, SL -0.05%, TP +0.50%
SHORT leg:  side Sell, positionIdx 2, SL +0.05%, TP -0.50%
net: +0.50% - 0.05% = +0.45% x 50 leverage = +22.5% of capital
```

On a **one-way (netting)** account those two orders cancel to zero exposure and
the model cannot function. Bybit calls the required setting **"Both Sides"**.
`--preflight` sets it and refuses to trade without it.

## 1. Account

1. Create a Bybit account — start on **testnet**: <https://testnet.bybit.com>
2. Use a **USDT Perpetual** account (`category=linear`). Leverage does not exist
   on spot.
3. Fund it (testnet gives free funds).

## 2. API key

Bybit → API → Create New Key

* Permissions: **Contract – Orders + Positions**, and **Read**
* **Withdrawals: OFF** — never enable them for a bot
* Bind the key to your **IP address**
* Copy the key and secret once; the secret is not shown again

## 3. Environment

```bash
export BYBIT_API_KEY=your_key
export BYBIT_API_SECRET=your_secret
export BYBIT_TESTNET=1        # 1 = testnet (default), 0 = mainnet
```

Never commit these. `.gitignore` already covers `.env`.

## 4. Verify before trading

```bash
python run_bybit.py --preflight
```

Checks connectivity, market data, instrument filters, credentials, **hedge
mode** and leverage. Exit code `0` only when every check passes.

## 5. Run

```bash
python run_bybit.py                    # paper  — no exchange contact at all
python run_bybit.py --mode dry_run     # real data + keys, orders logged NOT sent
V01T_LIVE=I_UNDERSTAND python run_bybit.py --mode live   # real orders
```

Live mode is refused unless `V01T_LIVE=I_UNDERSTAND` is set. Progress in this
order — paper, then dry-run, then testnet live, then mainnet.

### Options

| Flag | Default | Meaning |
|---|---|---|
| `--symbol` | `BTCUSDT` | instrument |
| `--leverage` | `50` | applied to both sides |
| `--equity` | `10000` | sizing base |
| `--interval` | `60` | seconds between cycles |
| `--cycles` | `0` | 0 = run forever |
| `--max-concurrent` | `3` | simultaneous squeezes |
| `--max-daily-loss` | `20.0` | % halt threshold |

## Risk rails

Enforced in every mode, in `v01t/bybit_executor.RiskLimits`:

* max concurrent squeezes
* max daily loss %
* max notional per leg
* minimum free balance
* kill switch
* **emergency flatten** — if the second leg fails to place, both sides are
  closed immediately so the account is never left holding one naked leg

## Files

| File | Purpose |
|---|---|
| `v01t/bybit.py` | Bybit V5 client: signing, klines, hedge mode, leverage, orders. Stdlib only; HTTP layer injectable, so all of it is unit-tested offline. |
| `v01t/bybit_executor.py` | Signal to double entry, sizing, modes, risk rails |
| `run_bybit.py` | CLI |
| `tests/test_bybit.py` | 41 tests covering signing, hedge mode, both legs, rails, preflight |

## Honest limits

* The backtest books a win when price moves 0.5% either way, **without checking
  whether the 0.05% stop was hit first on the path**. Live, both legs sit only
  0.05% from entry, so a small oscillation can stop both before the move
  develops. Expect live results to differ from the backtest.
* Fees, funding and slippage are real. Four fills per squeeze (two legs in, two
  out) at 50x leverage are material against a +22.5% target.
* **Run on testnet first, for long enough to see real fills**, and compare
  against the backtest before risking funds.
