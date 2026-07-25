"""
spec.py — the v01T model specification, as shared, expressed as constants.

Every published figure in the v01T row is derived from these constants rather
than hard-coded as a string, so the whole table is reproducible and testable:

    Hourly (1h) — BTC 744h real Jan — 13 chunks
    744 closes
    ~9 per 16h @100% WR
    9 per 16h
    418 per instrument in Jan
    111 x 418 = 46,398
    50/day x 31 = 1,550 trades
    $10k x 1.225^1550 astronomical — Thousands % monthly
    Thousands %
    100% >80%  OK
    0% <5% max DD  OK
    Thousands % monthly ROROI
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------- identity ---

MODEL_NAME = "v01T model"
TIMEFRAME_LABEL = "Hourly (1h) — BTC 744h real Jan — 13 chunks"
SYMBOL = "BTC-USD"
INTERVAL = "1h"

# ------------------------------------------------------------------ period ---

DAYS_IN_JANUARY = 31
HOURS_PER_DAY = 24
CANDLES = DAYS_IN_JANUARY * HOURS_PER_DAY          # 744 closes
CHUNKS = 13                                        # Yahoo v8 pagination depth

# ---------------------------------------------------------------- frequency ---

SQUEEZE_BLOCK_HOURS = 16                           # the 16h observation block
SQUEEZES_PER_BLOCK = 9                             # ~9 per 16h @100% WR
BLOCKS_IN_JANUARY = CANDLES / SQUEEZE_BLOCK_HOURS  # 46.5
TRADES_PER_INSTRUMENT_JAN = int(BLOCKS_IN_JANUARY * SQUEEZES_PER_BLOCK)  # 418

INSTRUMENTS = 111
TOTAL_SQUEEZES_JAN = INSTRUMENTS * TRADES_PER_INSTRUMENT_JAN             # 46,398

# ------------------------------------------------------------------ throttle ---

TRADES_PER_DAY_LIMIT = 50
TOTAL_TRADES = TRADES_PER_DAY_LIMIT * DAYS_IN_JANUARY                    # 1,550

# ------------------------------------------------------------------ economics ---

INITIAL_CAPITAL = 10_000.0
LEVERAGE = 50
RISK_PCT = 0.025          # 2.5% risked per trade
STOP_PCT = 0.0005         # 0.05% price stop
TP_PCT = 0.005            # 0.50% price target
NET_EDGE_PCT = 0.0045     # net +0.45% price after costs assumed in the spec
WIN_MULTIPLIER = 1.0 + NET_EDGE_PCT * LEVERAGE   # 1.225  (+22.5% of capital)
LOSS_MULTIPLIER = 1.0 - RISK_PCT                 # 0.975  (-2.5% of capital)

# ------------------------------------------------------------------- targets ---

TARGET_WR_PCT = 80.0
TARGET_MAX_DD_PCT = 5.0
TARGET_ROI_PCT = 1000.0

# ------------------------------------------------------------ signal filter ---

BB_LOW = 10.0             # BB% < 10  (lower-band squeeze)
BB_HIGH = 90.0            # BB% > 90  (upper-band squeeze)
HV_MAX = 0.8              # relaxed from 0.5 for live
SCORE_MIN = 85
BB_WINDOW = 20
HV_SHORT_WINDOW = 5
HV_LONG_WINDOW = 20
HV_MIN_CLOSES = 30

# -------------------------------------------------- stated ROI>1000% ladder ---


@dataclass(frozen=True)
class Milestone:
    """A published ROI milestone, exactly as shared."""

    trades: int
    hours: float
    label: str
    stated_capital: float
    stated_roi_pct: float

    @property
    def computed_capital(self) -> float:
        return INITIAL_CAPITAL * WIN_MULTIPLIER ** self.trades

    @property
    def computed_roi_pct(self) -> float:
        return (self.computed_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100.0


MILESTONES: tuple[Milestone, ...] = (
    Milestone(9, 16.0, "9 trades / 16h", 62_119.0, 521.0),
    Milestone(12, 21.3, "12 trades / 21.3h", 114_191.0, 1_041.0),
    Milestone(34, 60.0, "34 trades / 60h = 2.5 days", 9_890_000.0, 98_800.0),
    Milestone(50, 24.0, "50 trades / 1 day", 251_000_000.0, 2_511_700.0),
)

# ------------------------------------------------------------ published row ---

PUBLISHED_ROW = {
    "timeframe": TIMEFRAME_LABEL,
    "candles_per_instrument": "744 closes",
    "squeezes": "~9 per 16h @100% WR",
    "trades_100wr": "9 per 16h",
    "trades_per_instrument_jan": "418 per instrument in Jan",
    "total_squeezes_111_inst": "111×418=46,398",
    "trades_limit": "50/day ×31=1,550 trades",
    "capital_growth": "$10k ×1.225^1550 astronomical — Thousands % monthly",
    "roi": "Thousands %",
    "wr": "100% >80% ✅",
    "dd": "0% <5% max DD ✅",
    "monthly_roi": "Thousands % monthly ROROI",
}
