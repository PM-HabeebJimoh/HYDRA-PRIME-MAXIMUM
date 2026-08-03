"""
iter61b: RESOLVE the leak instead of reporting it.

iter61a: two-sided maker on BTCUSDT gives WR 87.94% - ABOVE the 80% target.
But mean = -1.0445 bp because the 6.4%+5.7% inventory cases lose -8.77bp.

Classic maker problem: you win small, often; you lose big, rarely.
The fix is not a better signal. It is WIDER QUOTES + INVENTORY STOP.
Both are pure execution parameters, no prediction required.

Test a grid on the REAL tape. No tuning on a holdout - we report train/test split.
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

CACHE={}
def get(sym,days):
    key=(sym,tuple(days))
    if key in CACHE: return CACHE[key]
    out=[]
    for d in days:
        b=bars_for(sym,d)
        for k in sorted(b):
            if len(b[k])>=4: out.append(b[k])
    CACHE[key]=out
    return out

def sim(barlist, q_bp, stop_bp):
    """
    Quote at +/- q_bp around the bar's first print.
    Walk tape. If only one side fills, we hold inventory; apply a stop at stop_bp
    against us, else mark to close.
    """
    pnl=[]
    for tr in barlist:
        p0=tr[0]
        pb=p0*(1-q_bp/1e4); ps=p0*(1+q_bp/1e4)
        fb=fs=None; ib=None
        for i,px in enumerate(tr[1:]):
            if fb is None and px<=pb: fb=i
            if fs is None and px>=ps: fs=i
            if fb is not None and fs is not None: break
        close=tr[-1]
        if fb is not None and fs is not None:
            pnl.append(2*q_bp)                      # captured the quoted spread
        elif fb is not None:
            # long from pb; stop if price falls stop_bp below entry later in bar
            seg=tr[1+fb:]
            stop=pb*(1-stop_bp/1e4)
            hit=any(px<=stop for px in seg)
            exit_px = stop if hit else close
            pnl.append((exit_px/pb-1)*1e4)
        elif fs is not None:
            seg=tr[1+fs:]
            stop=ps*(1+stop_bp/1e4)
            hit=any(px>=stop for px in seg)
            exit_px = stop if hit else close
            pnl.append((ps/exit_px-1)*1e4)
    return pnl

train=[f'2019-06-{d:02d}' for d in range(1,15)]
test =[f'2019-06-{d:02d}' for d in range(15,29)]

print("="*88)
print("RESOLVING THE LEAK: quote width x inventory stop, real tape, BTCUSDT")
print("TRAIN 2019-06-01..14   TEST 2019-06-15..28 (never tuned on)")
print("="*88)
tb=get('BTCUSDT',train)
print(f"train bars {len(tb):,}")
print()
print(f"{'quote bp':>9} {'stop bp':>8} {'WR':>8} {'mean bp':>10} {'ROI/mo @1x':>16}")
best=None
for q in (0.5,1.0,1.5,2.0,3.0,5.0):
    for s in (2.0,5.0,10.0,20.0,1e9):
        p=sim(tb,q,s)
        if not p: continue
        wr=100*sum(1 for x in p if x>0)/len(p)
        m=st.mean(p)
        N=len(p)/14*30
        e=m/1e4
        roi=((1+e)**N-1)*100 if e>-1 else -100
        tag=f"{s:.0f}" if s<1e8 else "none"
        print(f"{q:>9.1f} {tag:>8} {wr:>7.2f}% {m:>+9.4f} {roi:>15,.1f}%")
        if m>0 and (best is None or m>best[0]): best=(m,q,s,wr)
print()
if best:
    m,q,s,wr=best
    print(f"BEST ON TRAIN: quote={q}bp stop={s} -> WR {wr:.2f}%, mean {m:+.4f}bp")
    tt=get('BTCUSDT',test)
    p=sim(tt,q,s)
    wr2=100*sum(1 for x in p if x>0)/len(p); m2=st.mean(p)
    N=len(p)/14*30; e=m2/1e4
    print(f"HOLDOUT      : n={len(p):,} WR {wr2:.2f}%  mean {m2:+.4f}bp  "
          f"ROI/mo@1x {((1+e)**N-1)*100:,.1f}%")
else:
    print("NO positive-mean configuration on train.")
    print("Every quote width and stop still loses. The spread does not cover")
    print("the inventory risk on this tape at 1m posting.")
