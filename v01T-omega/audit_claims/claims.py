"""WHICH CLAIM WAS 'BEST', AND WHAT WAS IT ACTUALLY TESTED ON?
The user is right that these do not add up. Lay it out."""
rows=[
 ("iter52 'BEST'","cross-exchange DIRECTION","Binance->Bitfinex 1-MIN ticks","Nov2018-Nov2019","LTC 10% slice @10x","11/11 months >=500%"),
 ("iter56/57","volatility STRADDLE","Yahoo DAILY bars","Jan-Aug 2026","full allocation","-100% / -0.70%@DD4"),
]
print("="*100)
print("THE TWO CLAIMS ARE DIFFERENT MODELS ON DIFFERENT DATA")
print("="*100)
print("%-14s %-26s %-30s %-16s %-20s"%("iteration","MODEL","DATA","PERIOD","RESULT"))
for a,b,c,d,e,f in rows:
    print("%-14s %-26s %-30s %-16s %s"%(a,b,c,d,f))
print()
print("The '+1234%/mo' and 'LTC 10% slice @10x = 11/11 months >=500%' results are")
print("the CROSS-EXCHANGE DIRECTION model on 2018-19 MINUTE data.")
print()
print("The '-100%' results are the VOLATILITY STRADDLE model on 2026 DAILY data.")
print()
print("These share NOTHING except the word LTC. Different signal, different")
print("timeframe, different era, different mechanism.")
print()
print("="*100)
print("SO WHY WASN'T THE 'BEST' MODEL TESTED ON 2026?")
print("="*100)
print("  It requires TWO venues quoting the SAME asset in the SAME minute.")
print("  Measured, iteration 48 and 53:")
print("    Binance API 2026            : HTTP 451 geo-blocked")
print("    Bitfinex tXLMF0 perp 1m 2026: 10 bars per 1000 min = 1.0% coverage")
print("    Bitfinex tXLMUSD spot 1m    : 49 bars per 1000 min = 4.9% coverage")
print("    OKX + Kraken 2026           : ~100% coverage  <- WORKS")
print()
print("  iteration 53 DID test it on OKX->Kraken 2026 and found:")
print("    leader->follower corr +0.4408, asymmetry 26.7x, accuracy 80.00%")
print("    BUT n=86 observations = 1.5 hours. Not a month.")
