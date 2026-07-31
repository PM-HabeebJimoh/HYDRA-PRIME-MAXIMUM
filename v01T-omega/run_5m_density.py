import json,sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega')
import numpy as np
from omega.indicators import bb_percent, hv_ratio, score_of

d=json.load(open('/tmp/x5/days.json'))
tot_bars=0; tot_g1=0; tot_g2=0; tot_both=0
gaps_all=[]
for k in sorted(d):
    a=np.array(d[k],dtype=float)
    ts=a[:,0]; o=a[:,1]; c=a[:,2]; h=a[:,3]; l=a[:,4]
    gaps=np.diff(ts)/60000.0
    gaps_all+= list(gaps)
    bb=bb_percent(c); hv=hv_ratio(c)
    g1=(bb<10)|(bb>90); g2=hv<0.8
    g1=np.nan_to_num(g1,nan=False).astype(bool); g2=np.nan_to_num(g2,nan=False).astype(bool)
    both=g1&g2
    tot_bars+=len(a); tot_g1+=g1.sum(); tot_g2+=g2.sum(); tot_both+=both.sum()
    # measure: is a "5m bar" actually 5 minutes?
    print(f"{k}: bars={len(a):3d} G1={g1.sum():2d} G2={g2.sum():2d} both={both.sum():2d} "
          f"medgap={np.median(gaps):.0f}min meangap={gaps.mean():.1f}min maxgap={gaps.max():.0f}min")
g=np.array(gaps_all)
print()
print(f"TOTAL bars={tot_bars} G1={tot_g1} G2={tot_g2} BOTH(signals)={tot_both}")
print(f"gap distribution: 5min={100*(g==5).mean():.1f}%  >5min={100*(g>5).mean():.1f}%  median={np.median(g):.0f}min")
print(f"bars per real 24h day (avg over 4 sampled days) = {tot_bars/4:.1f}  vs 288 if continuous")
print(f"=> real monthly bar count ~= {tot_bars/4*31:.0f}, NOT 8928")
