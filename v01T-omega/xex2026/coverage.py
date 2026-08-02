"""The cross-exchange model needs BOTH venues quoting the SAME minute.
Measure real 2026 coverage before attempting the model."""
import json
# Bitfinex tXLMUSD 1m, window 1785640000000 - 1785700000000 (1000 minutes)
BFX=[1785644100,1785644160,1785644640,1785644700,1785645180,1785645780,1785646440,1785646620,
1785647040,1785647100,1785647820,1785648300,1785650760,1785651000,1785651360,1785652740,
1785652920,1785652980,1785653280,1785653580,1785654000,1785654060,1785654120,1785654180,
1785657000,1785657120,1785657180,1785657840,1785657960,1785658080,1785658500,1785659580,
1785660600,1785660660,1785661440,1785666960,1785668340,1785668820,1785668880,1785673860,
1785674160,1785674280,1785674400,1785676680,1785680100,1785681660,1785681720,1785682440,1785682800]
lo,hi=1785640000,1785700000
span=(hi-lo)//60
print("WINDOW: %d minutes (2026-08-01 area)"%span)
print()
print("Bitfinex tXLMUSD spot 1m bars present: %d of %d = %.1f%%"%(len(BFX),span,100*len(BFX)/span))
gaps=[(BFX[i+1]-BFX[i])//60 for i in range(len(BFX)-1)]
import statistics as st
print("  median gap %d min, max gap %d min"%(st.median(gaps),max(gaps)))
print()
print("OKX XLM-USDT 1m bars in the same window: ~1000 of 1000 = ~100%")
print("  (OKX returns a bar every minute, incl. zero-volume placeholders)")
print()
print("OVERLAP available for a cross-exchange model = %d minutes"%len(BFX))
print()
print("The 2018-19 model used 226,270 overlapping NEO minutes.")
print("Here we get %d per 1000-minute window."%len(BFX))
print("To reach even 10,000 overlaps needs %d fetch_page calls."%(10000/len(BFX)))
