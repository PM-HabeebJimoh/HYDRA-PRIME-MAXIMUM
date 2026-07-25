"""cli.py — command line entry point.  `python -m v01t.cli [--live] [--json] [--trades N]`"""

from __future__ import annotations

import argparse
import json
import sys

from .model import V01TModel
from .report import full_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="v01t",
        description="v01T model — Hourly (1h) — BTC 744h real Jan — 13 chunks",
    )
    parser.add_argument("--live", action="store_true",
                        help="try a live Yahoo Chart v8 fetch before falling back to the vendored series")
    parser.add_argument("--json", action="store_true", help="emit the summary as JSON")
    parser.add_argument("--trades", type=int, default=None,
                        help="print the first N rows of the trade ledger")
    args = parser.parse_args(argv)

    result = V01TModel().run(live=args.live)

    if args.json:
        print(json.dumps(result.summary(), indent=2, default=str))
    else:
        print(full_report(result))

    if args.trades:
        print("\n## Trade ledger (first %d)\n" % args.trades)
        print("| # | Day | Capital after | ROI %|")
        print("|---|---|---|---|")
        for t in result.trades[: args.trades]:
            print(f"| {t.n} | {t.day} | {t.capital_after:,.2f} | {t.roi_pct:,.2f} |")

    return 0 if result.goal_achieved else 1


if __name__ == "__main__":
    sys.exit(main())
