import sys, itertools
sys.path.insert(0,'.')
from scripts.search import precompute, backtest
from v01t.costs import DEFAULT_COSTS
from v01t.dataset import load_month
jan=load_month("jan2026").closes; jun=load_month("jun2026").closes
jb,jh=precompute(jan); ub,uh=precompute(jun)
rows=[]
for (bb,hv,tp,st,hold,lev,risk) in itertools.product([2,5,10,15,20,25,30,40],[0.5,0.8,1.0,1.5,99],
        [0.001,0.002,0.005,0.01,0.02,0.05,0.10,0.20],[0.002,0.005,0.01,0.02,0.05,0.10,0.20],
        [2,4,8,24,48,168],[1,3,5,10,20,50],[0.02,0.05,0.10,0.25]):
    for rev in (True,False):
        a=backtest(jan,jb,jh,bb,100-bb,hv,tp,st,hold,lev,risk,DEFAULT_COSTS,rev)
        if a["trades"]<8: continue
        b=backtest(jun,ub,uh,bb,100-bb,hv,tp,st,hold,lev,risk,DEFAULT_COSTS,rev)
        if b["trades"]<8: continue
        rows.append((min(a["wr"],b["wr"]),min(a["roi"],b["roi"]),max(a["max_dd"],b["max_dd"]),
                     dict(bb=bb,hv=hv,tp=tp,stop=st,hold=hold,lev=lev,risk=risk,rev=rev),a,b))
print("=== EFFICIENT FRONTIER: max worst-case monthly ROI at each WR floor (both months) ===")
print(f"{'WR floor':>9} {'best ROI%':>11} {'DD%':>7}  config")
for floor in [0,50,60,70,75,80,85,90,95,100]:
    c=[r for r in rows if r[0]>=floor]
    if not c: print(f"{floor:>8}% {'none':>11}"); continue
    b=max(c,key=lambda r:r[1])
    print(f"{floor:>8}% {b[1]:11.1f} {b[2]:7.2f}  tp={b[3]['tp']} stop={b[3]['stop']} lev={b[3]['lev']} hold={b[3]['hold']} {'rev' if b[3]['rev'] else 'con'}")
print()
print("=== max worst-case ROI at each DD ceiling, requiring WR>80 ===")
w=[r for r in rows if r[0]>80]
for cap in [5,10,20,30,50,100]:
    c=[r for r in w if r[2]<cap]
    if not c: print(f"  DD<{cap}%: none"); continue
    b=max(c,key=lambda r:r[1])
    print(f"  DD<{cap:3d}%: ROI {b[1]:9.1f}%  WR {b[0]:5.1f}  DD {b[2]:5.2f}  {b[3]}")
print()
best=max(w,key=lambda r:r[1])
print("BEST WR>80% BOTH MONTHS:", f"WRmin={best[0]:.1f} ROImin={best[1]:.1f}% DDmax={best[2]:.2f}%")
print("  cfg:",best[3]); print("  jan:",{k:round(v,2) for k,v in best[4].items()}); print("  jun:",{k:round(v,2) for k,v in best[5].items()})
