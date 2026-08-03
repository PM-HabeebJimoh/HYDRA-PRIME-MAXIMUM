"""
iter61d: The stop was the problem - it fired inside the noise and gapped.
REMOVE the stop entirely. Widen the quote instead, and let inventory
mean-revert. Pure two-sided maker, no prediction, no stop.

Charge everything honestly from the start this time:
  - stop: NONE (so nothing to gap through)
  - inventory marked to bar close (a real cost, unhedged)
  - maker fee applied both sides
  - queue rejection applied
Grid over quote width. TRAIN/TEST split preserved.
"""
import csv, io, zipfile, os, statistics as st, hashlib

def bars_for(sym, day):
    p=f'/tmp/ticks/cryptocurrency-ticks-data-master/data/{sym}/{sym}.{day}.csv.zip'
    if not os.path.exists(p): return {}
    z=zipfile.ZipFile(p); n=z.namelist()[0]
    bars={}
    with z.open(n) as fh:
        r=csv.reader(io.TextIOWrapper(fh,'utf-8')); next(r)
        for row in r:
            try: ts=float(row[1]); px=float(row[2])
            except: continue
            bars.setdefault(int(ts//60),[]).append(px)
    return bars

def get(sym,days):
    out=[]
    for d in days:
        b=bars_for(sym,d)
        for k in sorted(b):
            if len(b[k])>=4: out.append(b[k])
    return out

def sim(barlist,q_bp,maker_bp,queue_skip):
    pnl=[]
    for bi,tr in enumerate(barlist):
        p0=tr[0]
        pb=p0*(1-q_bp/1e4); ps=p0*(1+q_bp/1e4)
        fb=fs=None
        for i,px in enumerate(tr[1:]):
            if fb is None and px<=pb: fb=i
            if fs is None and px>=ps: fs=i
            if fb is not None and fs is not None: break
        if queue_skip>0:
            if int(hashlib.md5(str(bi).encode()).hexdigest()[:8],16)/0xffffffff<queue_skip: fb=None
            if int(hashlib.md5(('s'+str(bi)).encode()).hexdigest()[:8],16)/0xffffffff<queue_skip: fs=None
        close=tr[-1]
        if fb is not None and fs is not None: pnl.append(2*q_bp-2*maker_bp)
        elif fb is not None: pnl.append((close/pb-1)*1e4-maker_bp)
        elif fs is not None: pnl.append((ps/close-1)*1e4-maker_bp)
    return pnl

train=[f'2019-06-{d:02d}' for d in range(1,15)]
test =[f'2019-06-{d:02d}' for d in range(15,29)]
print("="*94)
print("NO STOP. Two-sided maker, inventory marked to close, maker fee + queue charged.")
print("="*94)
for sym in ('BTCUSDT','LTCBTC','NEOUSDT'):
    tb=get(sym,train)
    if not tb: continue
    print(f"\n--- {sym}  train bars {len(tb):,}")
    print(f"{'quote bp':>9} {'mkfee':>6} {'queue':>6} {'WR':>8} {'mean bp':>10} {'ROI/mo@1x':>14}")
    best=None
    for q in (1,2,3,5,8,12,20,30):
        for mk,qs in ((0.0,0.5),(-0.25,0.5),(1.0,0.5)):
            p=sim(tb,q,mk,qs)
            if len(p)<500: continue
            wr=100*sum(1 for x in p if x>0)/len(p); m=st.mean(p)
            N=len(p)/14*30; e=m/1e4
            roi=((1+e)**N-1)*100 if e>-1 else -100
            flag=" <<<" if m>0 else ""
            if m>0: print(f"{q:>9} {mk:>6.2f} {qs:>6.1f} {wr:>7.2f}% {m:>+9.4f} {roi:>13,.1f}%{flag}")
            if m>0 and (best is None or m>best[0]): best=(m,q,mk,qs,wr)
    if best is None:
        print("   no positive-mean quote width at any tested setting")
    else:
        m,q,mk,qs,wr=best
        tt=get(sym,test)
        p=sim(tt,q,mk,qs)
        wr2=100*sum(1 for x in p if x>0)/len(p); m2=st.mean(p)
        N=len(p)/14*30; e=m2/1e4
        print(f"   BEST train q={q}bp mk={mk} -> WR {wr:.2f}% mean {m:+.4f}")
        print(f"   HOLDOUT n={len(p):,} WR {wr2:.2f}% mean {m2:+.4f}bp "
              f"ROI/mo@1x {((1+e)**N-1)*100:,.1f}%")
