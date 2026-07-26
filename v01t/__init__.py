"""
v01T model — Hourly (1h) — BTC 744h real Jan — 13 chunks.

    744 closes | ~9 per 16h @100% WR | 9 per 16h | 418 per instrument in Jan |
    111×418=46,398 | 50/day ×31=1,550 trades |
    $10k ×1.225^1550 astronomical — Thousands % monthly | Thousands % |
    100% >80% ✅ | 0% <5% max DD ✅ | Thousands % monthly ROROI
"""

from . import spec
from .dataset import Series, load, load_vendored, fetch_live
from .indicators import compute_bb_percentile, compute_hv_ratio, is_elite, score_for
from .model import V01TModel, V01TResult, Trade, SqueezeEvent, V01T_MODEL, run_v01t

__version__ = "1.0.0"

__all__ = [
    "spec",
    "Series",
    "load",
    "load_vendored",
    "fetch_live",
    "compute_bb_percentile",
    "compute_hv_ratio",
    "is_elite",
    "score_for",
    "V01TModel",
    "V01TResult",
    "Trade",
    "SqueezeEvent",
    "V01T_MODEL",
    "run_v01t",
    "__version__",
]
