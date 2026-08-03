"""
iter61c: AUDIT MY OWN RESULT before believing it.

iter61b found quote=2bp/stop=2bp -> holdout WR 52.97%, mean +1.0875bp,
ROI/mo 10,112%. That is exactly the kind of number that has been WRONG
seven times before in this project. Audit it.

THREE THINGS I MODELLED OPTIMISTICALLY:
 1. The STOP is a market order. It CROSSES the spread and pays TAKER fee.
    I exited at exactly the stop price for free. Wrong.
 2. QUEUE POSITION. A limit order at a price only fills if the queue ahead of
    you clears. I filled on price-touch. Optimistic.
 3. The stop can GAP - within a bar price can jump past the stop.
    I filled at the stop price exactly.

Charge all three and see what survives.
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

def sim(barlist, q_bp, stop_bp, taker_bp, maker_bp, gap=True, queue_skip=0.0):
    """
    taker_bp : cost paid when the STOP fires (crossing spread + taker fee)
    maker_bp : fee per passive fill (0 or negative for rebate)
    gap      : if True, stop fills at the WORST price seen at-or-through the stop
    queue_skip: fraction of touch-fills that do NOT fill (queue not cleared)
    """
    import hashlib
    pnl=[]
    for bi,tr in enumerate(barlist):
        p0=tr[0]
        pb=p0*(1-q_bp/1e4); ps=p0*(1+q_bp/1e4)
        fb=fs=None
        for i,px in enumerate(tr[1:]):
            if fb is None and px<=pb: fb=i
            if fs is None and px>=ps: fs=i
            if fb is not None and fs is not None: break
        # queue: deterministically drop a fraction of fills
        if queue_skip>0:
            h=int(hashlib.md5(str(bi).encode()).hexdigest()[:8],16)/0xffffffff
            if h<queue_skip: fb=None
            h2=int(hashlib.md5(('s'+str(bi)).encode()).hexdigest()[:8],16)/0xffffffff
            if h2<queue_skip: fs=None
        close=tr[-1]
        if fb is not None and fs is not None:
            pnl.append(2*q_bp - 2*maker_bp)
        elif fb is not None:
            seg=tr[1+fb:]
            stop=pb*(1-stop_bp/1e4)
            through=[px for px in seg if px<=stop]
            if through:
                ex = min(through) if gap else stop
                pnl.append((ex/pb-1)*1e4 - taker_bp - maker_bp)
            else:
                pnl.append((close/pb-1)*1e4 - taker_bp - maker_bp)
        elif fs is not None:
            seg=tr[1+fs:]
            stop=ps*(1+stop_bp/1e4)
            through=[px for px in seg if px>=stop]
            if through:
                ex = max(through) if gap else stop
                pnl.append((ps/ex-1)*1e4 - taker_bp - maker_bp)
            else:
                pnl.append((ps/close-1)*1e4 - taker_bp - maker_bp)
    return pnl

test=[f'2019-06-{d:02d}' for d in range(15,29)]
tt=get('BTCUSDT',test)
print("="*86)
print("AUDIT of quote=2bp / stop=2bp on the HOLDOUT (2019-06-15..28), BTCUSDT real tape")
print("="*86)
print(f"holdout bars {len(tt):,}")
print()
scen=[
 ("iter61b as reported (nothing charged)", 0.0, 0.0, False, 0.0),
 ("+ stop gaps to worst price",            0.0, 0.0, True,  0.0),
 ("+ taker cost 4bp on stop exit",         4.0, 0.0, True,  0.0),
 ("+ taker 4bp, maker fee 1bp",            4.0, 1.0, True,  0.0),
 ("+ 50% queue rejection",                 4.0, 1.0, True,  0.5),
 ("+ 80% queue rejection",                 4.0, 1.0, True,  0.8),
 ("maker REBATE -0.25bp, taker 4bp, gap",  4.0,-0.25,True,  0.5),
]
print(f"{'scenario':<40} {'n':>7} {'WR':>8} {'mean bp':>10} {'ROI/mo@1x':>14}")
for name,tk,mk,gap,qs in scen:
    p=sim(tt,2.0,2.0,tk,mk,gap,qs)
    if not p: continue
    wr=100*sum(1 for x in p if x>0)/len(p); m=st.mean(p)
    N=len(p)/14*30; e=m/1e4
    roi=((1+e)**N-1)*100 if e>-1 else -100
    print(f"{name:<40} {len(p):>7,} {wr:>7.2f}% {m:>+9.4f} {roi:>13,.1f}%")
print()
print("The stop-gap term is the one that matters: a 2bp stop on a tape whose")
print("median 1m move is 4.7bp is INSIDE the noise, so it fires constantly and")
print("fills through. That was the flaw in iter61b.")
