import json,sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega')
import numpy as np
from omega.indicators import bb_percent, hv_ratio
from omega.straddle_fix import atr_fraction, barriers, resolve_straddle

FEE=0.0026  # 0.065% x 4 legs, Bitfinex futures taker
WIN=200
d=json.load(open('/tmp/x5/days.json'))
rets=[]; unresolved=0
for k in sorted(d):
    a=np.array(d[k],dtype=float)
    o,c,h,l=a[:,1],a[:,2],a[:,3],a[:,4]
    bb=bb_percent(c); hv=hv_ratio(c)
    af=atr_fraction(h,l,c)
    g1=np.nan_to_num((bb<10)|(bb>90),nan=False).astype(bool)
    g2=np.nan_to_num(hv<0.8,nan=False).astype(bool)
    sig=np.flatnonzero(g1&g2)
    for i in sig:
        e=i+2                      # strictly causal entry (emit4 rule)
        if e>=len(c): continue
        b=barriers(af[i])
        if b is None: continue
        sf,tf=b
        hi=h[e:e+WIN]; lo=l[e:e+WIN]
        if len(hi)<2: continue
        rl,rs,both=resolve_straddle(hi,lo,o[e],sf,tf)
        if rl==0.0 or rs==0.0:
            unresolved+=1
            # mark honestly at worst excursion instead of zero
            if rl==0.0: rl=(lo.min()-o[e])/o[e]
            if rs==0.0: rs=(o[e]-hi.max())/o[e]
        rets.append(rl+rs-FEE)
r=np.array(rets)
n=len(r)
print(f"signals traded n={n}   unresolved legs marked honestly: {unresolved}")
if n:
    wr=100*(r>0).mean(); m=r.mean(); se=r.std(ddof=1)/np.sqrt(n)
    print(f"Win Rate {wr:.1f}%   mean net/trade {100*m:+.4f}%   SE {100*se:.4f}%")
    print(f"95% CI on mean: {100*(m-1.96*se):+.4f}% to {100*(m+1.96*se):+.4f}%")
    print(f"worst {100*r.min():+.3f}%  best {100*r.max():+.3f}%")
    # monthly extrapolation at REAL measured bar density
    N=int(round(n/4*31))   # 4 days sampled -> month
    print(f"\nreal signal rate: {n/4:.2f}/day -> {N} trades/month")
    print("required net per trade for 1000pct monthly at N={}: {:.4f}pct".format(N,100*(11**(1/N)-1)))
    print("measured: {:.4f}pct".format(100*m))
    if m>0:
        roi=( (1+m)**N -1 )*100
        print(f"unlevered compounded monthly ROI = {roi:+.2f}%")
