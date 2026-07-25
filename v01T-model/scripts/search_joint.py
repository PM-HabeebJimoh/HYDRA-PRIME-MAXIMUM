import sys, os, itertools, json
sys.path.insert(0,'.')
from scripts.search import precompute, backtest, meets_goal, TARGET_WR, TARGET_MONTHLY_PCT, TARGET_DD
from v01t.costs import DEFAULT_COSTS, ZERO_COSTS
from v01t.dataset import load_month

jan=load_month("jan2026").closes; jun=load_month("jun2026").closes
jb,jh=precompute(jan); ub,uh=precompute(jun)

bb_lows=[2,5,10,15,20,25,30,40]; hvs=[0.5,0.8,1.0,1.5,99]
tps=[0.001,0.002,0.005,0.01,0.02,0.05,0.10,0.20]
stops=[0.002,0.005,0.01,0.02,0.05,0.10,0.20]
holds=[2,4,8,24,48,168]; levs=[1,3,5,10,20,50]; risks=[0.02,0.05,0.10,0.25]

best=[]; both=[]
for (bb,hv,tp,st,hold,lev,risk) in itertools.product(bb_lows,hvs,tps,stops,holds,levs,risks):
    for rev in (True,False):
        a=backtest(jan,jb,jh,bb,100-bb,hv,tp,st,hold,lev,risk,DEFAULT_COSTS,rev)
        if a["trades"]<8: continue
        b=backtest(jun,ub,uh,bb,100-bb,hv,tp,st,hold,lev,risk,DEFAULT_COSTS,rev)
        if b["trades"]<8: continue
        cfg=dict(bb=bb,hv=hv,tp=tp,stop=st,hold=hold,lev=lev,risk=risk,rev=rev)
        # goal on BOTH months
        if meets_goal(a,8) and meets_goal(b,8): both.append((cfg,a,b))
        # track best combined: min WR, min ROI, max DD
        best.append((min(a["wr"],b["wr"]), min(a["roi"],b["roi"]), max(a["max_dd"],b["max_dd"]), cfg,a,b))

print("configs meeting ALL THREE targets in BOTH months:", len(both))
print()
# best worst-case WR
best.sort(key=lambda x:-x[0])
print("=== best WORST-CASE win rate across both months ===")
for w,r,d,c,a,b in best[:6]:
    print(f"  WRmin {w:5.1f}  ROImin {r:9.1f}  DDmax {d:6.2f}  {c}")
print()
bp=[x for x in best if x[1]>0]
bp.sort(key=lambda x:-x[1])
print("=== best WORST-CASE ROI (profitable both months) ===")
for w,r,d,c,a,b in bp[:6]:
    print(f"  WRmin {w:5.1f}  ROImin {r:9.1f}  DDmax {d:6.2f}  jan{a['roi']:.0f}%/jun{b['roi']:.0f}%  {c}")
print()
print("profitable in BOTH months:", len(bp), "of", len(best))
# any with WR>80 both?
w80=[x for x in best if x[0]>80]
print("WR>80% in BOTH months:", len(w80))
w80r=[x for x in w80 if x[1]>1000]
print("WR>80% AND ROI>1000% in BOTH:", len(w80r))
