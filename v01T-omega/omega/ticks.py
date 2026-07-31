"""Real Binance trade ticks with aggressor flags.

Columns: Id, time (epoch seconds, ms precision), Price, Quantity,
IsBuyerMaker, BuyerOrderId, SellerOrderId, IsBestPriceMatch.

IsBuyerMaker == False  -> the BUYER was the aggressor (lifted the ask)
IsBuyerMaker == True   -> the SELLER was the aggressor (hit the bid)

That flag is what makes these ticks valuable: the effective half-spread can be
MEASURED from real executions rather than assumed, because aggressor-buy prints
occur at the ask and aggressor-sell prints at the bid.
"""
import zipfile, csv, io
import numpy as np


def load_day(path):
    z = zipfile.ZipFile(path)
    name = z.namelist()[0]
    ts, px, qty, sellagg = [], [], [], []
    with z.open(name) as fh:
        rd = csv.reader(io.TextIOWrapper(fh, "utf-8"))
        next(rd, None)
        for row in rd:
            if len(row) < 5:
                continue
            try:
                ts.append(float(row[1])); px.append(float(row[2]))
                qty.append(float(row[3]))
            except ValueError:
                continue
            sellagg.append(row[4].strip().lower() == "true")
    a = np.argsort(np.array(ts))
    return dict(ts=np.array(ts)[a], px=np.array(px)[a],
                qty=np.array(qty)[a], sell_agg=np.array(sellagg)[a])


def effective_spread_bp(d):
    """Mean(ask prints) - mean(bid prints), as bp of mid. Measured, not assumed."""
    buy = d["px"][~d["sell_agg"]]
    sell = d["px"][d["sell_agg"]]
    if len(buy) < 100 or len(sell) < 100:
        return float("nan")
    mid = 0.5 * (buy.mean() + sell.mean())
    return (buy.mean() - sell.mean()) / mid * 1e4


def to_bars(d, seconds):
    """Aggregate ticks into OHLCV bars. Real trades only, no interpolation."""
    b = (d["ts"] // seconds).astype(np.int64)
    uniq, start = np.unique(b, return_index=True)
    end = np.append(start[1:], len(b))
    return dict(ts=(uniq * seconds).astype(np.int64),
                open=d["px"][start], close=d["px"][end - 1],
                high=np.maximum.reduceat(d["px"], start),
                low=np.minimum.reduceat(d["px"], start),
                vol=np.add.reduceat(d["qty"], start),
                ntrades=(end - start))
