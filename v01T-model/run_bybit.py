#!/usr/bin/env python3
"""
run_bybit.py — automatic v01T execution on Bybit.

    python run_bybit.py                     # paper, no exchange contact
    python run_bybit.py --preflight         # verify account is ready
    python run_bybit.py --mode dry_run      # real data, orders logged not sent
    python run_bybit.py --mode live         # real orders (needs V01T_LIVE)

Credentials come from the environment, never from the repo:

    export BYBIT_API_KEY=...
    export BYBIT_API_SECRET=...
    export BYBIT_TESTNET=1                  # 1 = testnet (default), 0 = mainnet

Each elite squeeze places the DOUBLE ENTRY: a long leg and a short leg at the
same price, each with its own stop (0.05%) and target (0.50%) attached
server-side. Hedge mode is mandatory — see --preflight.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from v01t import spec
from v01t.bybit import BybitClient
from v01t.bybit_executor import (MODE_DRY_RUN, MODE_LIVE, MODE_PAPER,
                                 BybitExecutor, RiskLimits)


def build_client() -> BybitClient:
    return BybitClient(
        api_key=os.environ.get("BYBIT_API_KEY", ""),
        api_secret=os.environ.get("BYBIT_API_SECRET", ""),
        testnet=os.environ.get("BYBIT_TESTNET", "1") != "0",
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="v01T automatic execution on Bybit")
    ap.add_argument("--mode", default=MODE_PAPER,
                    choices=[MODE_PAPER, MODE_DRY_RUN, MODE_LIVE])
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--leverage", type=int, default=spec.LEVERAGE)
    ap.add_argument("--equity", type=float, default=spec.INITIAL_CAPITAL)
    ap.add_argument("--interval", type=float, default=60.0,
                    help="seconds between cycles")
    ap.add_argument("--cycles", type=int, default=0, help="0 = run forever")
    ap.add_argument("--preflight", action="store_true",
                    help="check the account and exit")
    ap.add_argument("--max-concurrent", type=int, default=3)
    ap.add_argument("--max-daily-loss", type=float, default=20.0)
    a = ap.parse_args(argv)

    # --preflight always checks the real exchange, so it must not run in paper
    # mode (which has nothing to verify and would trivially report ready).
    if a.preflight and a.mode == MODE_PAPER:
        a.mode = MODE_DRY_RUN

    needs_client = a.mode in (MODE_DRY_RUN, MODE_LIVE) or a.preflight
    client = build_client() if needs_client else None

    print("=" * 78)
    print(f"v01T AUTOMATIC EXECUTION — BYBIT   mode={a.mode}   symbol={a.symbol}")
    print("=" * 78)
    print("  DOUBLE ENTRY per squeeze: LONG + SHORT at the same price")
    print(f"    LONG  leg  SL -{spec.STOP_PCT * 100:.2f}%  TP +{spec.TP_PCT * 100:.2f}%")
    print(f"    SHORT leg  SL +{spec.STOP_PCT * 100:.2f}%  TP -{spec.TP_PCT * 100:.2f}%")
    print(f"    net +{(spec.TP_PCT - spec.STOP_PCT) * 100:.2f}% x {a.leverage} "
          f"= +{(spec.TP_PCT - spec.STOP_PCT) * a.leverage * 100:.1f}% of capital")
    if client:
        print(f"  endpoint: {client.base_url}")
        print(f"  key     : {'set' if client.api_key else 'MISSING'}")
    print()

    try:
        ex = BybitExecutor(
            client=client, symbol=a.symbol, mode=a.mode,
            leverage=a.leverage, equity=a.equity,
            limits=RiskLimits(max_concurrent_squeezes=a.max_concurrent,
                              max_daily_loss_pct=a.max_daily_loss),
        )
    except PermissionError as exc:
        print(f"  REFUSED: {exc}")
        return 2

    if a.preflight:
        report = ex.preflight()          # call ONCE: it mutates account state
        print(json.dumps(report, indent=2))
        if not report.get("ready"):
            print("\n  NOT READY — fix the failing checks above before trading.")
        return 0 if report.get("ready") else 1

    if a.mode == MODE_PAPER:
        print("  PAPER MODE — no exchange contact. Replaying vendored real data.\n")
        from v01t.dataset import load_month
        closes = load_month("jul2026").closes
        n = 0
        for i in range(spec.HV_MIN_CLOSES, len(closes)):
            r = ex.cycle(closes[: i + 1])
            if r.get("executed"):
                n += 1
                e = r["executed"]
                print(f"  [{n:3d}] squeeze @ {e['entry_price']:>11,.2f}  "
                      f"qty/leg {e['qty_per_leg']:.4f}  "
                      f"LONG SL {e['long_stop']:,.2f} TP {e['long_target']:,.2f}  "
                      f"SHORT SL {e['short_stop']:,.2f} TP {e['short_target']:,.2f}")
            elif r.get("blocked") and n:
                print(f"        blocked: {r['blocked']}")
        print(f"\n  {json.dumps(ex.state.snapshot(), indent=2)}")
        return 0

    pre = ex.preflight()          # call ONCE
    if not pre.get("ready"):
        print("  PREFLIGHT FAILED — not trading.")
        print(json.dumps(pre, indent=2))
        return 1

    print("  preflight OK, starting loop. Ctrl-C to stop.\n")
    try:
        i = 0
        while a.cycles == 0 or i < a.cycles:
            r = ex.cycle()
            if r.get("executed"):
                print(f"  [{r['cycle']}] EXECUTED {r['executed']['id']} "
                      f"@ {r['executed']['entry_price']:,.2f}")
            elif r.get("error"):
                print(f"  [{r['cycle']}] error: {r['error']}")
            i += 1
            if a.cycles == 0 or i < a.cycles:
                time.sleep(a.interval)
    except KeyboardInterrupt:
        print("\n  stopped by user")
    print(json.dumps(ex.state.snapshot(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
