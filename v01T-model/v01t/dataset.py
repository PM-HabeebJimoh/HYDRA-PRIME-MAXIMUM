"""
dataset.py — access to the real BTC-USD January 2026 hourly series.

Resolution order:
  1. live fetch from Yahoo Chart v8 (when `live=True` and the network allows it)
  2. the vendored snapshot in data/btc_usd_1h_jan2026.json

The vendored snapshot is the same data, retrieved from the same endpoint and
committed so the model is reproducible offline and in CI.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List

from . import spec

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
VENDORED_PATH = os.path.join(_ROOT, "data", "btc_usd_1h_jan2026.json")
JUNE_PATH = os.path.join(_ROOT, "data", "btc_usd_1h_jun2026.json")

DATASETS = {
    "jan2026": VENDORED_PATH,
    "jun2026": JUNE_PATH,
}

JAN_2026_PERIOD1 = 1767225600  # 2026-01-01 00:00 UTC
JAN_2026_PERIOD2 = 1769817600  # 2026-01-31 00:00 UTC (Yahoo end bound)

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


@dataclass(frozen=True)
class Series:
    symbol: str
    interval: str
    timestamps: List[int]
    closes: List[float]
    origin: str          # "live" or "vendored"
    source_url: str

    def __len__(self) -> int:
        return len(self.closes)


def load_vendored(path: str = VENDORED_PATH, expected_bars: int | None = spec.CANDLES) -> Series:
    """Load a committed real hourly series (defaults to January 2026)."""
    with open(path, "r") as fh:
        payload = json.load(fh)
    closes = payload["closes"]
    if expected_bars is not None and len(closes) != expected_bars:
        raise ValueError(
            f"vendored dataset has {len(closes)} closes, expected {expected_bars}"
        )
    if any(c is None for c in closes):
        raise ValueError("vendored dataset contains null closes")
    return Series(
        symbol=payload["symbol"],
        interval=payload["interval"],
        timestamps=payload["timestamps"],
        closes=closes,
        origin="vendored",
        source_url=payload["source_url"],
    )


def fetch_live(
    symbol: str = spec.SYMBOL,
    period1: int = JAN_2026_PERIOD1,
    period2: int = JAN_2026_PERIOD2,
    interval: str = spec.INTERVAL,
    timeout: float = 20.0,
) -> Series:
    """Fetch the series directly from Yahoo Chart v8.

    Raises on any network or payload problem so the caller can fall back.
    """
    import urllib.request  # stdlib only, no hard dependency

    url = (
        YAHOO_CHART_URL.format(symbol=symbol)
        + f"?period1={period1}&period2={period2}&interval={interval}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "v01T-model/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    raw_closes = result["indicators"]["quote"][0]["close"]

    pairs = [(t, c) for t, c in zip(timestamps, raw_closes) if c is not None]
    if not pairs:
        raise ValueError("live fetch returned no usable closes")

    return Series(
        symbol=symbol,
        interval=interval,
        timestamps=[t for t, _ in pairs],
        closes=[c for _, c in pairs],
        origin="live",
        source_url=url,
    )


def load(live: bool = False) -> Series:
    """Preferred entry point: live when asked and reachable, vendored otherwise."""
    if live:
        try:
            return fetch_live()
        except Exception:
            pass
    return load_vendored()


def load_month(key: str) -> Series:
    """Load a vendored month by key, e.g. "jan2026" (744 bars) or "jun2026" (720 bars)."""
    if key not in DATASETS:
        raise KeyError(f"unknown dataset {key!r}; available: {sorted(DATASETS)}")
    return load_vendored(DATASETS[key], expected_bars=None)
