"""CHALLENGE THE CAPACITY BLOCKER.

iter42 said: NEO edge is real but the market is $1,490/min, so +440%/mo
runs on $14 of capital = $46/month. I then STOPPED. That was lazy.

Three things I never questioned:

1. I used ONE venue pair (Binance->Bitfinex) on ONE asset (NEO).
   The MECHANISM is 'venue A leads venue B'. That exists on every
   (asset x venue-pair) combination. Capacity is the SUM, not one instance.

2. I applied a FLAT 8bp fee to every asset. But fees and spreads differ
   enormously by asset. BTC trades at 1-2bp spread; NEO at 15bp. I may have
   killed BTC with a fee assumption borrowed from an altcoin.

3. I measured capacity as 'volume that traded in the next minute'.
   That is TRADED volume, not available DEPTH, and it ignores that a
   1-minute holding period lets the SAME capital recycle across
   non-overlapping opportunities in other markets.

Test 2 first - it is the one that could change the answer.
"""
print(__doc__)
print("="*74)
print("THE ARITHMETIC THAT MATTERS")
print("="*74)
# from iter42 measurements
rows=[("NEO",87.01,35.28,1490),("LTC",81.34,20.47,2935),("BTC",73.73,6.81,22407)]
print("%-6s %8s %10s %14s %10s"%("asset","acc%","gross bp","notional/min","gross $/trade @10%"))
for a,acc,g,n in rows:
    print("%-6s %7.2f%% %+9.2f %13s %13s"%(a,acc,g,"${:,}".format(n),"${:,.2f}".format(n*0.10*g*1e-4)))
print()
print("iter42 applied a FLAT 8bp fee to all three. Realistic round-trip taker:")
fees={"NEO":16.0,"LTC":12.0,"BTC":4.0}   # bp round trip, VIP tier, asset-appropriate
print("%-6s %10s %10s %12s %16s"%("asset","gross bp","fee bp","net bp","net $/trade @10%"))
for a,acc,g,n in rows:
    f=fees[a]; net=g-f
    print("%-6s %+9.2f %10.1f %+11.2f %15s  %s"%(a,g,f,net,
        "${:,.2f}".format(n*0.10*net*1e-4), "PROFIT" if net>0 else "loss"))
