"""
iter60 FINAL TEST. The chain has narrowed to exactly one question.

  fill rate      94.3%  -> NOT a blocker (measured)
  cost           0 bp at maker -> NOT a blocker (real fee schedules)
  frequency      43,200/mo -> NOT a blocker (1m bars exist)
  WR of a filled passive order, UNCONDITIONAL = 48.00%  <- THE BLOCKER

Everything now depends on: can order-flow (known BEFORE the bar completes,
i.e. "before the chart reacts") lift filled-maker WR from 48% toward 80%?

Signal = signed order-flow imbalance (OFI) over the PREVIOUS bar only.
Strictly causal: post at bar t using flow from bar t-1.
Real Binance tape, real IsBuyerMaker aggressor flags.
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
            b=int(ts//60)
            bars.setdefault(b,[]).append((px,qty,ibm))
    return bars

def run(sym, days, tick):
    recs=[]
    for day in days:
        bars=bars_for(sym,day)
        ks=sorted(bars)
        for i in range(1,len(ks)):
            if ks[i]!=ks[i-1]+1: continue
            prev=bars[ks[i-1]]; cur=bars[ks[i]]
            if len(cur)<3 or len(prev)<3: continue
            # OFI on PREVIOUS bar: IsBuyerMaker=True means the SELLER was aggressor
            buyvol=sum(q for _,q,m in prev if not m)
            selvol=sum(q for _,q,m in prev if m)
            tot=buyvol+selvol
            if tot<=0: continue
            ofi=(buyvol-selvol)/tot
            p0=cur[0][0]; pend=cur[-1][0]
            lo=min(x[0] for x in cur[1:]); hi=max(x[0] for x in cur[1:])
            # passive BUY below, passive SELL above
            pb=p0-tick; ps=p0+tick
            if lo<=pb: recs.append((ofi,+1,(pend/pb-1)*1e4))
            if hi>=ps: recs.append((ofi,-1,(ps/pend-1)*1e4*-1*-1))
    return recs

days=[f'2019-06-{d:02d}' for d in range(1,15)]
for sym,tick in (('BTCUSDT',0.01),('NEOUSDT',0.001)):
    recs=run(sym,days,tick)
    if not recs: continue
    buys=[r for r in recs if r[1]==1]
    print("="*78)
    print(f"{sym} | ERA 2018-19 | real tape | passive BUY fills, n={len(buys):,}")
    print("="*78)
    allr=[r[2] for r in buys]
    print(f"unconditional: WR={100*sum(1 for x in allr if x>0)/len(allr):.2f}%  "
          f"median={st.median(allr):+.3f}bp  mean={st.mean(allr):+.3f}bp")
    print()
    print("conditioned on PREVIOUS-bar order flow imbalance (causal):")
    print(f"{'OFI bucket':<18} {'n':>7} {'WR':>8} {'mean bp':>10}")
    ofis=sorted(r[0] for r in buys)
    def q(p): return ofis[int(p*(len(ofis)-1))]
    edges=[(-1.01,q(.1)),(q(.1),q(.25)),(q(.25),q(.5)),(q(.5),q(.75)),(q(.75),q(.9)),(q(.9),1.01)]
    best=None
    for lo,hi in edges:
        sub=[r[2] for r in buys if lo<=r[0]<hi]
        if len(sub)<50: continue
        wr=100*sum(1 for x in sub if x>0)/len(sub)
        mn=st.mean(sub)
        print(f"[{lo:+.3f},{hi:+.3f}) {len(sub):>7,} {wr:>7.2f}% {mn:>+9.3f}")
        if best is None or wr>best[0]: best=(wr,mn,len(sub),lo,hi)
    if best:
        wr,mn,n,lo,hi=best
        print()
        print(f"BEST bucket: WR={wr:.2f}% mean={mn:+.3f}bp n={n:,}")
        print(f"  target WR = 80%.  {'REACHED' if wr>=80 else f'SHORT BY {80-wr:.2f} points'}")
        if mn>0:
            import math
            e=mn/1e4
            N=n/14*30      # scale 14 days -> month
            print(f"  trades/mo in this bucket ~ {N:,.0f}")
            print(f"  monthly ROI @1x, maker, zero fee = {((1+e)**N-1)*100:,.2f}%")
    print()
