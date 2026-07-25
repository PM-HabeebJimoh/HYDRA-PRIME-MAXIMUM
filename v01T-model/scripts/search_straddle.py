import sys, itertools
sys.path.insert(0,'.')
from v01t.straddle import StraddleEngine
from v01t.costs import DEFAULT_COSTS, ZERO_COSTS
from v01t.dataset import load_month
jan=load_month("jan2026"); jun=load_month("jun2026")
rows=[]
stops=[0.0005,0.002,0.005,0.02]
tps=[0.005,0.02,0.05]
holds=[4,24,168]
levs=[20,50,100]
bbs=[(10,90),(20,80),(30,70)]
hvs=[0.8,99]
for st,tp,hold,lev,(bl,bh),hv in itertools.product(stops,tps,holds,levs,bbs,hvs):
    if tp<=st: continue
    e=StraddleEngine(leverage=lev,stop_pct=st,tp_pct=tp,max_hold_bars=hold,costs=DEFAULT_COSTS)
    a=e.run(jan.closes,jan.timestamps,hv_max=hv,bb_low=bl,bb_high=bh)
    if len(a.trades)<8: continue
    b=e.run(jun.closes,jun.timestamps,hv_max=hv,bb_low=bl,bb_high=bh)
    if len(b.trades)<8: continue
    rows.append((min(a.win_rate_pct,b.win_rate_pct),min(a.roi_pct,b.roi_pct),
                 max(a.max_drawdown_pct,b.max_drawdown_pct),
                 dict(stop=st,tp=tp,hold=hold,lev=lev,bb=bl,hv=hv),a,b))
print("evaluated",len(rows),"straddle configs on BOTH real months\n")
g=[r for r in rows if r[0]>80 and r[1]>1000 and r[2]<5]
print("meeting ALL THREE (WR>80, ROI>1000%, DD<5%) in BOTH months:",len(g))
for w,ro,d,c,a,b in g[:10]: print("  ",c,f"WR{w:.1f} ROI{ro:.0f} DD{d:.2f}")
print()
rows.sort(key=lambda x:-x[0])
print("=== best worst-case WIN RATE ===")
for w,ro,d,c,a,b in rows[:8]:
    print(f"  WRmin {w:5.1f}  ROImin {ro:9.1f}%  DDmax {d:6.2f}%  {c}")
print()
p=[r for r in rows if r[1]>0]; p.sort(key=lambda x:-x[1])
print("=== best worst-case ROI (profitable both months) ===")
for w,ro,d,c,a,b in p[:8]:
    print(f"  WRmin {w:5.1f}  ROImin {ro:9.1f}%  DDmax {d:6.2f}%  jan{a.roi_pct:.0f}/jun{b.roi_pct:.0f}  {c}")
print()
w80=[r for r in rows if r[0]>80]
print("WR>80% both months:",len(w80))
if w80:
    w80.sort(key=lambda x:-x[1])
    print("=== WR>80% ranked by worst-case ROI ===")
    for w,ro,d,c,a,b in w80[:8]:
        print(f"  WRmin {w:5.1f}  ROImin {ro:9.1f}%  DDmax {d:6.2f}%  {c}")
print("WR>80 AND ROI>1000 both:",len([r for r in rows if r[0]>80 and r[1]>1000]))
