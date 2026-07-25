"""
backtest_june_2026.py — full v01T backtest for June 2026 on real BTC-USD 1h data.

Runs both views:
  A. the SPEC model (published v01T row arithmetic, rescaled to June's 30 days)
  B. the REAL engine (bar-by-bar entries, stops, targets, fees, slippage, losses)

Usage:  python scripts/backtest_june_2026.py [--json]
"""

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from v01t import spec                                    # noqa: E402
from v01t.dataset import load_month                      # noqa: E402
from v01t.engine import V01TBacktestEngine               # noqa: E402

JUNE_DAYS = 30
JUNE_HOURS = JUNE_DAYS * 24  # 720


def spec_view() -> dict:
    """The published v01T arithmetic applied to June's 720 hours / 30 days."""
    blocks = JUNE_HOURS / spec.SQUEEZE_BLOCK_HOURS               # 45.0
    per_instrument = int(blocks * spec.SQUEEZES_PER_BLOCK)       # 405
    total_squeezes = spec.INSTRUMENTS * per_instrument           # 44,955
    total_trades = spec.TRADES_PER_DAY_LIMIT * JUNE_DAYS         # 1,500
    final = Decimal(str(spec.INITIAL_CAPITAL)) * Decimal(str(spec.WIN_MULTIPLIER)) ** total_trades
    roi = (final - Decimal(str(spec.INITIAL_CAPITAL))) / Decimal(str(spec.INITIAL_CAPITAL)) * 100
    return {
        "hours": JUNE_HOURS,
        "blocks": blocks,
        "trades_per_instrument": per_instrument,
        "total_squeezes_111_inst": total_squeezes,
        "total_trades": total_trades,
        "win_rate_pct": 100.0,
        "max_drawdown_pct": 0.0,
        "final_capital_repr": f"{final:.6E}",
        "roi_repr": f"{roi:.6E}",
    }


def main(argv: list[str]) -> int:
    series = load_month("jun2026")
    engine = V01TBacktestEngine()
    real = engine.run(series, label="v01T REAL backtest — BTC-USD 1h — June 2026")
    spec_out = spec_view()

    if "--json" in argv:
        print(json.dumps({"spec": spec_out, "real": real.summary()}, indent=2, default=str))
        return 0

    print("=" * 78)
    print("v01T MODEL — FULL BACKTEST — JUNE 2026 — BTC-USD 1h — REAL DATA")
    print("=" * 78)
    print(f"Period   : {real.period_start_utc} .. {real.period_end_utc}")
    print(f"Bars     : {real.bars} hourly closes (30 days x 24h)")
    print(f"Source   : {series.source_url}")
    print(f"Price    : {series.closes[0]:,.2f} -> {series.closes[-1]:,.2f} "
          f"({real.buy_and_hold_pct:+.2f}% buy & hold)")

    print("\n" + "-" * 78)
    print("A. SPEC VIEW — published v01T arithmetic rescaled to June (30 days)")
    print("-" * 78)
    print(f"  {JUNE_HOURS}h / 16h            = {spec_out['blocks']} blocks")
    print(f"  {spec_out['blocks']} x 9 squeezes      = {spec_out['trades_per_instrument']} trades per instrument")
    print(f"  111 x {spec_out['trades_per_instrument']}             = {spec_out['total_squeezes_111_inst']:,} total squeezes")
    print(f"  50/day x 30 days       = {spec_out['total_trades']:,} trades")
    print(f"  $10k x 1.225^{spec_out['total_trades']}     = {spec_out['final_capital_repr']}")
    print(f"  WR {spec_out['win_rate_pct']:.0f}%  DD {spec_out['max_drawdown_pct']:.0f}%  ROI {spec_out['roi_repr']} %")
    print("  NOTE: no loss branch exists in this view, so WR/DD are definitional.")

    print("\n" + "-" * 78)
    print("B. REAL ENGINE — bar-by-bar execution with stops, targets, fees, slippage")
    print("-" * 78)
    p = real.parameters
    print(f"  Filter    : BB% <{p['bb_low']} or >{p['bb_high']}, HV <{p['hv_max']}, score >={p['score_min']}")
    print(f"  Risk      : {p['risk_pct']*100:.1f}% equity | stop {p['stop_pct']*100:.2f}% | "
          f"TP {p['tp_pct']*100:.2f}% | {p['leverage']}x cap")
    print(f"  Costs     : fee {p['fee_pct']*100:.2f}%/side | slippage {p['slippage_pct']*100:.2f}%/fill")
    print(f"  Hold      : max {p['max_hold_bars']} bars | throttle {p['max_trades_per_day']}/day")
    print()
    print(f"  Squeezes detected .... {real.squeezes_detected}")
    print(f"  Trades taken ......... {real.trades}   (wins {real.wins} / losses {real.losses})")
    print(f"  Win rate ............. {real.win_rate_pct:.2f}%   target >80%  "
          f"{'PASS' if real.goals['win_rate']['passed'] else 'FAIL'}")
    print(f"  Max drawdown ......... {real.max_drawdown_pct:.2f}%   target <5%   "
          f"{'PASS' if real.goals['max_drawdown']['passed'] else 'FAIL'}")
    print(f"  ROI .................. {real.roi_pct:+.2f}%   target >1000% "
          f"{'PASS' if real.goals['roi']['passed'] else 'FAIL'}")
    print(f"  Capital .............. ${real.initial_capital:,.2f} -> ${real.final_capital:,.2f}")
    print(f"  Peak equity .......... ${real.peak_equity:,.2f}")
    print(f"  Gross P&L ............ ${real.gross_pnl:,.2f}")
    print(f"  Fees paid ............ ${real.total_fees:,.2f}")
    print(f"  Net P&L .............. ${real.net_pnl:,.2f}")
    print(f"  Profit factor ........ {real.profit_factor}")
    print(f"  Expectancy / trade ... ${real.expectancy:,.2f}")
    print(f"  Avg win / avg loss ... ${real.avg_win:,.2f} / ${real.avg_loss:,.2f}")
    print(f"  Largest win / loss ... ${real.largest_win:,.2f} / ${real.largest_loss:,.2f}")
    print(f"  Max consec. losses ... {real.max_consecutive_losses}")
    print(f"  Exit breakdown ....... {real.outcomes}")

    print("\n  Trade log:")
    print(f"  {'#':>3} {'dir':<6}{'entry':>11}{'exit':>11}{'bars':>5}{'BB%':>8}"
          f"{'HV':>7}{'net $':>11}{'equity':>12}  outcome")
    for t in real.trade_list:
        print(f"  {t.n:>3} {t.direction:<6}{t.entry_price:>11,.0f}{t.exit_price:>11,.0f}"
              f"{t.bars_held:>5}{t.bb_pct:>8.1f}{t.hv_ratio:>7.2f}{t.net_pnl:>11,.0f}"
              f"{t.equity_after:>12,.0f}  {t.outcome}")

    print("\n" + "=" * 78)
    print("VERDICT — June 2026")
    print("=" * 78)
    print(f"  Spec view : WR 100%, DD 0%, ROI {spec_out['roi_repr']} %  (arithmetic, no losses possible)")
    print(f"  Real view : WR {real.win_rate_pct:.2f}%, DD {real.max_drawdown_pct:.2f}%, "
          f"ROI {real.roi_pct:+.2f}%  (measured on 720 real bars)")
    print(f"  Goals achieved on real data: {real.goal_achieved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
