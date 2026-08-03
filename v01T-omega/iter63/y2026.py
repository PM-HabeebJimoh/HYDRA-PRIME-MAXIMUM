"""
iter63b: "Have you run backtesting for 2026?" - answer with a table, per month,
WR / DD / ROI, for every 2026 series I can reach.

Two honest caveats stated up front:
 1. The 2018-19 engine needs TWO venues' 1-minute ticks with aggressor flags.
    For 2026 I have bars, not a synchronised two-venue tick tape, so this is
    the walk-forward DIRECTION model on bars (iter59), not the identical system.
 2. Costs charged. Enter next bar OPEN, exit its CLOSE. Strictly causal.
"""
import csv, glob, os, math, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/iter59')
from wf2026 import load, run, DIR

COST_BP=5.0
print("="*92)
print("2026 BACKTEST | real bars | walk-forward direction model | 5bp cost | per MONTH")
print("="*92)
summary=[]
for f in sorted(glob.glob(f'{DIR}/*_4h.csv'))+sorted(glob.glob(f'{DIR}/*_1d.csv')):
    base=os.path.basename(f)
    name=base.replace('.csv','')
    tf='4h' if '_4h' in base else '1d'
    d=load(f)
    if tf=='1d': d=[x for x in d if x[0][:4] in ('2025','2026')]
    if len(d)<200: continue
    tr=run(name,d,train=120 if tf=='4h' else 150,tf=tf)
    if not tr: continue
    tr=[t for t in tr if t[3][:4]=='2026']
    if len(tr)<20: continue
    bym={}
    for _,sig,r,dt_ in tr: bym.setdefault(dt_[:7],[]).append(r-COST_BP/1e4)
    print()
    print(f"--- {name} ({tf}) ---")
    print(f"{'month':<9} {'n':>4} {'WR%':>8} {'DD%':>8} {'ROI':>12} {'>=500%?':>8}")
    n500=0; nm=0
    for m in sorted(bym):
        rr=bym[m]; eq=1.0;peak=1.0;dd=0.0
        for x in rr:
            eq*=(1+x); peak=max(peak,eq); dd=max(dd,(peak-eq)/peak)
        roi=(eq-1)*100; wr=100*sum(1 for x in rr if x>0)/len(rr)
        nm+=1; n500 += roi>=500
        print(f"{m:<9} {len(rr):>4} {wr:>7.2f}% {dd*100:>7.2f}% {roi:>11.2f}% {'YES' if roi>=500 else 'no':>8}")
    summary.append((name,n500,nm))
print()
print("="*92)
print("2026 SUMMARY: months clearing >=500% ROI")
print("="*92)
for name,n500,nm in summary:
    print(f"  {name:<12} {n500}/{nm} months >=500%")
tot=sum(s[1] for s in summary); tm=sum(s[2] for s in summary)
print(f"  TOTAL        {tot}/{tm} month-instrument observations >=500%")
