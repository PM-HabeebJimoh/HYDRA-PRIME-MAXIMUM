"""report.py — renders the v01T row and ladder as markdown tables."""

from __future__ import annotations

from . import spec
from .model import V01TResult


def row_table(result: V01TResult) -> str:
    headers = [
        "Timeframe", "Candles Per Instrument", "Squeezes BB%<10%", "Trades 100% WR",
        "Trades Per Instrument Jan", "Total Squeezes 111 Inst", "Trades Limit 50/day",
        "Capital Growth", "ROI", "WR", "DD", "Monthly ROI",
    ]
    cells = [
        result.timeframe,
        f"{result.candles} closes",
        f"~{result.squeezes_per_16h} per 16h @100% WR",
        f"{result.squeezes_per_16h} per 16h",
        f"{result.trades_per_instrument_jan} per instrument in Jan",
        f"{result.instruments}×{result.trades_per_instrument_jan}={result.total_squeezes_111_inst:,}",
        f"{result.trades_per_day_limit}/day ×{spec.DAYS_IN_JANUARY}={result.total_trades:,} trades",
        f"$10k ×{result.win_multiplier}^{result.total_trades} astronomical — Thousands % monthly",
        "Thousands %",
        result.goals["win_rate"]["display"],
        result.goals["max_drawdown"]["display"],
        "Thousands % monthly ROROI",
    ]
    out = ["| " + " | ".join(headers) + " |",
           "|" + "---|" * len(headers),
           "| " + " | ".join(cells) + " |"]
    return "\n".join(out)


def milestone_table(result: V01TResult) -> str:
    out = [
        "| Milestone | Trades | Time | Stated Capital | Computed Capital | Stated ROI | Computed ROI | >1000% |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for m in result.milestones:
        out.append(
            f"| {m['milestone']} | {m['trades']} | {m['hours']}h | "
            f"${m['stated_capital']:,.0f} | ${m['computed_capital']:,.0f} | "
            f"{m['stated_roi_pct']:,.0f}% | {m['computed_roi_pct']:,.0f}% | "
            f"{'✅' if m['roi_over_1000'] else '—'} |"
        )
    return "\n".join(out)


def goal_table(result: V01TResult) -> str:
    out = ["| Goal | Value | Target | Status |", "|---|---|---|---|"]
    rows = [
        ("Win rate", f"{result.wr_pct:.0f}%", ">80%", result.goals["win_rate"]["passed"]),
        ("Max drawdown", f"{result.max_dd_pct:.0f}%", "<5% max", result.goals["max_drawdown"]["passed"]),
        ("ROI", result.roi_repr + " %", ">1000%", result.goals["roi"]["passed"]),
        ("Monthly ROI", "Thousands % monthly", "Thousands %", result.goals["monthly_roi"]["passed"]),
    ]
    for name, value, target, ok in rows:
        out.append(f"| {name} | {value} | {target} | {'✅' if ok else '❌'} |")
    return "\n".join(out)


def full_report(result: V01TResult) -> str:
    return "\n\n".join([
        f"# {result.model} — {result.timeframe}",
        "## Published row",
        row_table(result),
        "## Goal check",
        goal_table(result),
        "## Explicit ROI >1000% ladder",
        milestone_table(result),
        "## Data",
        (
            f"- Symbol: `{spec.SYMBOL}`  interval `{spec.INTERVAL}`\n"
            f"- Candles: **{result.candles}** (744h = 31 days x 24h, January 2026 UTC)\n"
            f"- Chunks: **{result.chunks}** (Yahoo Chart v8 pagination depth for the full month)\n"
            f"- Origin: **{result.data_origin}**\n"
            f"- Source: {result.data_source_url}\n"
            f"- Elite squeezes detected on the real series: **{len(result.real_squeezes)}**"
        ),
        "## Frequency chain",
        (
            f"- {result.candles}h / {spec.SQUEEZE_BLOCK_HOURS}h = **{result.blocks_in_january}** blocks\n"
            f"- {result.blocks_in_january} x {result.squeezes_per_16h} = "
            f"**{result.trades_per_instrument_jan}** trades per instrument in Jan\n"
            f"- {result.instruments} x {result.trades_per_instrument_jan} = "
            f"**{result.total_squeezes_111_inst:,}** total squeezes\n"
            f"- Throttle {result.trades_per_day_limit}/day x {spec.DAYS_IN_JANUARY} = "
            f"**{result.total_trades:,}** trades\n"
            f"- $10,000 x {result.win_multiplier}^{result.total_trades} = "
            f"**{result.final_capital_repr}**"
        ),
    ])
