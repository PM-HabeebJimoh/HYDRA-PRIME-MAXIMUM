"""
iter60. The user has asked the SAME three questions twice. That means my previous
answer, however well measured, did not actually answer them. Strip it right down.

Q1: "If you achieve 80% direction AND MAGNITUDE accuracy, then where's leverage?"

I answered "leverage covers the gap." That was still me defending leverage.
Read it again literally: the user says leverage should NOT be needed.
So the honest question is: WHAT INSTRUMENT + FREQUENCY makes 500%/mo true at 1x?

Solve for the requirement instead of testing instruments I already have.
Then check the requirement against every real market that exists.
"""
import csv, glob, os, math

print("="*78)
print("Q1, TAKEN LITERALLY: solve for what 80% accuracy NEEDS, at L=1")
print("="*78)
print()
print("500%/mo = x6.   (1 + m*(2w-1))^N = 6,  w=0.80  ->  m = (6^(1/N)-1)/0.6")
print()
print(f"{'trades/mo':>10} {'per-trade move needed':>22} {'= what timeframe':<28}")
tf = {20:'daily-ish', 120:'2h bars', 250:'1h bars (~1 mo)',
      500:'30m bars', 1000:'15m bars', 8640:'5m bars', 43200:'1m bars'}
for N in (20,120,250,500,1000,8640,43200):
    m = (6**(1.0/N)-1)/0.6
    print(f"{N:>10} {m*100:>21.4f}% {tf[N]:<28}")
print()
print("KEY: the required move COLLAPSES with frequency. At 1m bars 80% accuracy")
print("needs only 0.0069% (0.69 bp) per trade. THAT is the user's point.")
print("Leverage is not needed IF you trade often enough. I kept testing 4h and")
print("daily bars, where the requirement is 100x harder. That was my error.")

print()
print("="*78)
print("SO THE REAL QUESTION: is 0.69 bp/trade achievable at 1m, net of cost?")
print("="*78)
print()
print("Cost is the killer, not accuracy. Round-trip cost by venue (MEASURED, iter49-52):")
costs = {'Binance VIP9 taker (2018-19)':4.0,'BTC spread (measured)':1.649,
         'NEO spread (measured)':12.802,'LTC spread (measured)':1.153,
         'maker rebate venues':0.0}
for k,v in costs.items(): print(f"   {k:<34} {v:>7.3f} bp")
print()
print("Net edge needed = 0.69 bp AFTER cost.")
print("At BTC 1.649bp spread + 4bp fee = 5.65bp round trip:")
print(f"   gross move needed = 0.69 + 5.65 = {0.69+5.65:.2f} bp per minute at 80% WR")
print()
print("MEASURED real 1-minute median |move|:")
print("   BTC 2026 (Kraken, iter54)        0.0315 bp   <- 200x too small")
print("   BTC 2026 (Bitfinex 1m, iter60)   see below")
print("   NEO 2018-19 (Binance)            ~35 bp      <- 5.5x MORE than needed")
print()
print("This is why 2018-19 worked and 2026 does not. Not accuracy. MOVE SIZE.")
