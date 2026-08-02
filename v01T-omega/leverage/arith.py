"""THE LEVERAGE QUESTION, ANSWERED WITH ARITHMETIC.

You asked: 86.98% accuracy, so WHERE IS LEVERAGE?
Fair. I never applied it. Here is what happens when I do."""
print("="*74)
print("THE DIRECTION MODEL (iter39, NEO, top 0.5% confidence)")
print("="*74)
acc=86.98; gross=35.28; cost=40.0
print("  accuracy        %.2f%%"%acc)
print("  gross edge      %+.2f bp per trade"%gross)
print("  taker cost      %.2f bp round trip"%cost)
print("  NET             %+.2f bp per trade"%(gross-cost))
print()
print("="*74)
print("APPLY LEVERAGE TO IT")
print("="*74)
print("%-10s %14s %14s"%("leverage","net bp/trade","verdict"))
for L in (1,5,10,25,50,100):
    net=(gross-cost)*L
    print("%-10s %+14.2f %14s"%("%dx"%L,net,"LOSS" if net<0 else "PROFIT"))
print()
print("  Leverage is a MULTIPLIER, not a sign-changer.")
print("  L x (-4.72) is negative for every L > 0.")
print("  100x leverage on a -4.72bp edge = -472bp per trade = account death.")
print()
print("="*74)
print("SO WHY DID I NOT LEVERAGE? Because leverage amplifies what EXISTS.")
print("="*74)
print("  The 86.98%% accuracy is REAL.")
print("  The +35.28bp gross is REAL.")
print("  But the fee is 40bp, and 35.28 - 40 = -4.72.")
print("  There is nothing to amplify. That is the whole answer.")
print()
print("="*74)
print("NOW THE REAL QUESTION: WHAT DOES IT TAKE TO MAKE IT POSITIVE?")
print("="*74)
print("  breakeven fee = %.2f bp (we need fee BELOW gross)"%gross)
print("  current taker = %.2f bp"%cost)
print("  shortfall     = %.2f bp = need fee %.0f%% lower"%(cost-gross,100*(1-gross/cost)))
print()
for fee,lbl in ((40.0,'Bitfinex taker (measured)'),(20.0,'Binance taker 0.10%x2'),
                (8.0,'Binance VIP taker 0.04%x2'),(4.0,'VIP9 taker 0.02%x2'),
                (0.0,'maker at touch')):
    net=gross-fee
    print("  fee %5.1fbp (%-26s) -> net %+7.2f bp  %s"%(fee,lbl,net,"PROFIT" if net>0 else "loss"))
print()
print("="*74)
print("AND *THEN* LEVERAGE, ON THE POSITIVE VERSIONS")
print("="*74)
print("%-28s %10s %12s %14s"%("fee scenario","net bp","x10 lev","x25 lev"))
for fee,lbl in ((8.0,'Binance VIP 0.04%'),(4.0,'VIP9 0.02%'),(0.0,'maker')):
    net=gross-fee
    print("%-28s %+10.2f %+12.2f %+14.2f"%(lbl,net,net*10,net*25))
