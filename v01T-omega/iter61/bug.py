"""
iter61e: 6,583,117,346% is not a result, it is a BUG. Find it.

Hypothesis: when queue_skip drops ONE side, the bar is counted as a
one-sided inventory trade even though the OTHER side also touched. In a
trending bar the surviving side is the profitable one, so dropping fills
at random SELECTS winners. That is lookahead through the rejection filter.

Also: 'BOTH filled -> +2*q_bp' assumes both fills happen and we are flat.
If the buy fills at minute-start and the sell at minute-end, we held risk.
But the bigger tell is the queue interaction. Test directly.
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
            if px>0: bars.setdefault(int(ts//60),[]).append(px)
    return bars

def get(sym,days):
    out=[]
    for d in days:
        b=bars_for(sym,d)
        for k in sorted(b):
            if len(b[k])>=4 and b[k][0]>0 and b[k][-1]>0: out.append(b[k])
    return out

train=[f'2019-06-{d:02d}' for d in range(1,15)]
tb=get('BTCUSDT',train)

def sim(barlist,q_bp,queue_skip,count_all):
    """count_all=True: a bar where BOTH sides touched is ALWAYS scored as
    both-filled (spread captured), regardless of queue. Queue only removes
    the trade entirely - it cannot convert a two-sided bar into a
    one-sided directional winner."""
    pnl=[]
    for bi,tr in enumerate(barlist):
        p0=tr[0]
        pb=p0*(1-q_bp/1e4); ps=p0*(1+q_bp/1e4)
        tb_=ts_=False
        for px in tr[1:]:
            if px<=pb: tb_=True
            if px>=ps: ts_=True
        close=tr[-1]
        skip = queue_skip>0 and int(hashlib.md5(str(bi).encode()).hexdigest()[:8],16)/0xffffffff<queue_skip
        if skip: continue
        if tb_ and ts_: pnl.append(2*q_bp)
        elif tb_: pnl.append((close/pb-1)*1e4)
        elif ts_: pnl.append((ps/close-1)*1e4)
    return pnl

print("="*82)
print("BUG HUNT: does per-side random rejection manufacture the edge?")
print("="*82)
print(f"{'quote':>6} {'queue mode':<28} {'n':>7} {'WR':>8} {'mean bp':>10}")
for q in (1,2,3):
    p=sim(tb,q,0.0,True)
    wr=100*sum(1 for x in p if x>0)/len(p)
    print(f"{q:>6} {'no rejection':<28} {len(p):>7,} {wr:>7.2f}% {st.mean(p):>+9.4f}")
    p=sim(tb,q,0.5,True)
    wr=100*sum(1 for x in p if x>0)/len(p)
    print(f"{q:>6} {'whole-bar rejection 50%':<28} {len(p):>7,} {wr:>7.2f}% {st.mean(p):>+9.4f}")
print()
print("Now the iter61d version, which rejects each SIDE independently:")
def sim_bad(barlist,q_bp,queue_skip):
    pnl=[]
    for bi,tr in enumerate(barlist):
        p0=tr[0]; pb=p0*(1-q_bp/1e4); ps=p0*(1+q_bp/1e4)
        fb=fs=None
        for i,px in enumerate(tr[1:]):
            if fb is None and px<=pb: fb=i
            if fs is None and px>=ps: fs=i
        if queue_skip>0:
            if int(hashlib.md5(str(bi).encode()).hexdigest()[:8],16)/0xffffffff<queue_skip: fb=None
            if int(hashlib.md5(('s'+str(bi)).encode()).hexdigest()[:8],16)/0xffffffff<queue_skip: fs=None
        close=tr[-1]
        if fb is not None and fs is not None: pnl.append(2*q_bp)
        elif fb is not None: pnl.append((close/pb-1)*1e4)
        elif fs is not None: pnl.append((ps/close-1)*1e4)
    return pnl
for q in (1,2,3):
    p=sim_bad(tb,q,0.5)
    wr=100*sum(1 for x in p if x>0)/len(p)
    print(f"{q:>6} {'per-SIDE rejection 50%':<28} {len(p):>7,} {wr:>7.2f}% {st.mean(p):>+9.4f}")
print()
print("If per-side rejection shows a large positive mean while whole-bar")
print("rejection does not, the edge was manufactured by the filter. CONFIRMED BUG.")
