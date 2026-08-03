"""
iter61: I found a REAL FLAW IN MY OWN iter60 TEST. Fixing it, not reporting it.

iter60 measured: post passive BUY -> exit at BAR CLOSE.
That is a DIRECTIONAL bet with a passive entry. Of course it wins ~48%: the
close is a coin flip.

That is NOT what a market maker does. A market maker posts BOTH sides and earns
the SPREAD. Entry passive AND exit passive. The P&L is not "did price go up",
it is "did I capture the spread before price ran".

This is the "different angle" - I was measuring a direction bet and calling it
a maker strategy. Re-measure properly.

Real Binance tape, IsBuyerMaker aggressor flags, 2019-06.
"""
import csv, io, zipfile, os, statistics as st

def bars_for(sym, day):
    p=f'/tmp/ticks/cryptocurrency-ticks-data-master/data/{sym}/{sym}.{day}.csv.zip'
    if not os.path.exists(p): return {}
    z=zipfile.ZipFile(p); n=z.namelist()[0]
    bars={}
    with z.open(n) as fh:
        r=csv.reader(io.TextIOWrapper(fh,'utf-8')); next(r)
        for row in r:
            try:
                ts=float(row[1]); px=float(row[2]); qty=float(row[3]); ibm=row[4]=='True'
            except: continue
            bars.setdefault(int(ts//60),[]).append((ts,px,qty,ibm))
    return bars

def run(sym, days, tick):
    """
    Within each 1m bar, post BUY at p0-tick and SELL at p0+tick simultaneously.
    Walk the tape in order. Outcomes:
      BOTH fill  -> captured the round trip = +2*tick (the spread). WIN.
      ONE fills  -> left holding inventory; mark to the bar close. That is the risk.
      NEITHER    -> no trade.
    Strictly sequential, no lookahead: we walk trades in timestamp order.
    """
    both=0; onlyb=0; onlys=0; none=0
    pnl=[]           # bp per posted bar
    inv_pnl=[]       # bp on the inventory-only cases
    for day in days:
        bars=bars_for(sym,day)
        for k in sorted(bars):
            tr=bars[k]
            if len(tr)<4: continue
            p0=tr[0][1]
            pb=p0-tick; ps=p0+tick
            fb=fs=None
            for ts,px,q,ibm in tr[1:]:
                if fb is None and px<=pb: fb=px
                if fs is None and px>=ps: fs=px
                if fb is not None and fs is not None: break
            close=tr[-1][1]
            spread_bp=(2*tick/p0)*1e4
            if fb is not None and fs is not None:
                both+=1; pnl.append(spread_bp)
            elif fb is not None:
                onlyb+=1
                r=(close/pb-1)*1e4; pnl.append(r); inv_pnl.append(r)
            elif fs is not None:
                onlys+=1
                r=(ps/close-1)*1e4; pnl.append(r); inv_pnl.append(r)
            else:
                none+=1
    return both,onlyb,onlys,none,pnl,inv_pnl

days=[f'2019-06-{d:02d}' for d in range(1,15)]
print("="*80)
print("iter61: TWO-SIDED MAKER (post both sides, capture spread) - the correct test")
print("ERA 2018-19 | real Binance tape | IsBuyerMaker flags")
print("="*80)
for sym,tick in (('BTCUSDT',0.01),('NEOUSDT',0.001),('LTCBTC',0.000001)):
    try:
        both,ob,os_,none,pnl,inv=run(sym,days,tick)
    except Exception as e:
        print(sym,"ERR",e); continue
    tot=both+ob+os_+none
    if not pnl: continue
    n=len(pnl)
    wr=100*sum(1 for x in pnl if x>0)/n
    mean=st.mean(pnl)
    print()
    print(f"{sym}: bars={tot:,}")
    print(f"   BOTH sides filled (spread captured) {both:>7,}  {both/tot*100:>5.1f}%")
    print(f"   only BUY filled  (long inventory)   {ob:>7,}  {ob/tot*100:>5.1f}%")
    print(f"   only SELL filled (short inventory)  {os_:>7,}  {os_/tot*100:>5.1f}%")
    print(f"   neither                             {none:>7,}  {none/tot*100:>5.1f}%")
    print(f"   --> WR over all trades = {wr:.2f}%   mean = {mean:+.4f} bp")
    if inv: print(f"   inventory-only cases mean = {st.mean(inv):+.4f} bp  (this is the leak)")
    if mean>0:
        N=n/14*30
        e=mean/1e4
        print(f"   trades/mo ~{N:,.0f} -> monthly ROI @1x = {((1+e)**N-1)*100:,.1f}%")
