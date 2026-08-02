"""
iter59: TSLA_1d was the ONE series of 12 to survive Bonferroni (p=0.019).
Test it properly: 2026-only holdout, real costs, real liquidation check at each L.
ERA 2026 | TSLA 1d real bars | walk-forward, strictly causal | NO tuning on the holdout.
"""
import sys, csv, math
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/iter59')
from wf2026 import load, run, DIR

d_all = load(f'{DIR}/TSLA_1d.csv')
d = [x for x in d_all if x[0][:4] in ('2025','2026')]
trades = run('TSLA', d, train=150, tf='1d')

# split: everything dated 2026 is the holdout
oos = [t for t in trades if t[3][:4]=='2026']
ins = [t for t in trades if t[3][:4] < '2026']

def stats(ts, label, cost_bp=0.0, L=1):
    if not ts: print(f"{label}: none"); return
    rets=[t[2]-cost_bp/10000 for t in ts]
    wr=100*sum(1 for r in rets if r>0)/len(rets)
    liq=sum(1 for r in rets if r <= -1.0/L)
    eq=1.0;peak=1.0;dd=0.0;blown=False
    for r in rets:
        eq*=(1+r*L)
        if eq<=0: blown=True; eq=1e-12; break
        peak=max(peak,eq); dd=max(dd,(peak-eq)/peak)
    months=len(ts)/20.3
    mo=((eq)**(1/months)-1)*100 if eq>0 and months>0 else -100
    print(f"{label:<34} n={len(ts):>4} WR={wr:>5.2f}% DD={dd*100:>6.2f}% "
          f"ROI/mo={mo:>11,.2f}% liq_breaches={liq}{'  ACCOUNT BLOWN' if blown else ''}")

print("="*96)
print("TSLA 1d | TRAIN 2025 (in-sample) vs 2026 (HOLDOUT, never tuned on)")
print("="*96)
stats(ins, "2025 in-sample, gross, L=1")
stats(oos, "2026 HOLDOUT, gross, L=1")
print()
print("2026 HOLDOUT with real retail equity costs (1bp comm + 4bp spread/slip = 5bp RT):")
for L in (1,5,10,25,50):
    stats(oos, f"  2026 holdout, 5bp cost, L={L}x", cost_bp=5.0, L=L)
print()
bym={}
for _,sig,r,dt in oos: bym.setdefault(dt[:7],[]).append(r-0.0005)
print(f"{'month':<9} {'n':>4} {'WR':>7} {'ROI@1x':>10} {'ROI@50x':>14} {'liq@50x':>8}")
allpos=True
for m in sorted(bym):
    rr=bym[m]; e=1.0; e50=1.0; liq=sum(1 for r in rr if r<=-0.02)
    for r in rr:
        e*=(1+r); e50*=(1+r*50)
        if e50<=0: e50=0
    w=100*sum(1 for r in rr if r>0)/len(rr)
    if (e-1)<0: allpos=False
    print(f"{m:<9} {len(rr):>4} {w:>6.2f}% {(e-1)*100:>9.2f}% {(e50-1)*100:>13,.1f}% {liq:>8}")
print()
print("CONSTANT >5000%/mo achieved on 2026 holdout?  ", "YES" if False else "NO")
print("Every month positive at 1x?", allpos)
