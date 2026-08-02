"""IS THE 87% REAL, OR IS IT STALE PRICES?

My model predicts Bitfinex's NEXT-MINUTE close from Binance's CURRENT price.
If Bitfinex NEO trades rarely, its "close" is just the last trade - possibly
minutes old. Then "predicting" it is only predicting when a stale quote
catches up. That is not tradable: there is no liquidity to trade against,
and the fill you assume never existed.

This is the single assumption my >500% rests on. Test it."""
import numpy as np, sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from load import load_1m
for nm in ('NEO','LTC','BTC'):
    a=load_1m(nm)
    if a is None: continue
    t=(a[:,0]/1000.0).astype(np.int64); c=a[:,2]; v=a[:,5]
    print("=== Bitfinex %s ==="%nm)
    print("  1m bars present: %d over %.0f days"%(len(t),(t.max()-t.min())/86400))
    span_min=(t.max()-t.min())/60
    print("  coverage: %.1f%% of all minutes have a bar"%(100*len(t)/span_min))
    gaps=np.diff(t)/60.0
    print("  gap between bars: median %.0f min, p90 %.0f min, max %.0f min"%(
        np.median(gaps),np.percentile(gaps,90),gaps.max()))
    print("  volume per bar: median %.2f  p10 %.4f"%(np.median(v),np.percentile(v,10)))
    # repeated closes = no new information
    rep=(np.diff(c)==0).mean()
    print("  UNCHANGED close vs prior bar: %.1f%%  <-- staleness indicator"%(100*rep))
    print()
