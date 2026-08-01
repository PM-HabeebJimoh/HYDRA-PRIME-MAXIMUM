"""THE FIX: normalise risk by ACTIVITY, not by fixed fraction.

Diagnosis: monthly mean-R Sharpe = 5.00 (edge is rock stable, 0 negative months).
           monthly sum-R  Sharpe = 1.45 (because trade COUNT swings 72.6%).
At fixed fractional risk, equity tracks sum(R) -> you inherit the count noise
for free, with NO extra return. That is a pure, removable inefficiency.

FIX: size each trade by 1/(expected concurrent activity), estimated CAUSALLY
from the trailing window. Busy periods -> smaller per-trade risk; quiet
periods -> larger. Monthly RISK BUDGET becomes constant instead of the
per-trade risk being constant. This converts sum-R Sharpe into mean-R Sharpe.
"""
import numpy as np
A=np.load('/tmp/v82/events.npy'); P=A[A[:,4]==0]
P=P[np.argsort(P[:,0])]
t0=P[:,0].min(); R=P[:,2]; n=len(P)
mo=(P[:,1].max()-t0)/86400000/30.44

def sim(f,mode='flat',halflife_days=30.0,floor=0.25,cap=4.0):
    ev=np.concatenate([np.stack([P[:,0],np.zeros(n),np.arange(n)],1),
                       np.stack([P[:,1],np.ones(n),np.arange(n)],1)])
    ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
    capital=1.0;peak=1.0;dd=0.0
    staked=np.zeros(n);live=np.zeros(n,bool)
    lam=np.log(2)/(halflife_days*86400000.0)
    rate=0.0; last=None; base=None
    for k in range(len(ev)):
        ts=ev[k,0]; ty=ev[k,1]; i=int(ev[k,2])
        if ty==0:
            # causal EWMA arrival rate of signals (trades per day)
            if last is None: rate=1.0; last=ts
            else:
                dt=max(ts-last,1.0); decay=np.exp(-lam*dt)
                rate=rate*decay+(1-decay)*(86400000.0/dt)
                last=ts
            if base is None: base=rate
            if mode=='flat': w=1.0
            else:
                w=base/max(rate,1e-9)
                w=min(cap,max(floor,w))
            staked[i]=capital*f*w; live[i]=True
        else:
            if live[i]:
                capital+=staked[i]*R[i]; live[i]=False
                if capital<=0: return 0.0,1.0
                peak=max(peak,capital); dd=max(dd,(peak-capital)/peak)
    return capital,dd

def solve(mode,target=0.04):
    lo,hi=1e-7,1.0
    for _ in range(48):
        m=(lo+hi)/2
        c,dd=sim(m,mode)
        if c<=0 or dd>target: hi=m
        else: lo=m
    c,dd=sim(lo,mode)
    return lo,dd,c**(1/mo)-1

print("%-34s %11s %9s %14s"%("sizing","risk/trade","maxDD%","ROI/mo @DD4"))
for mode,lbl in (('flat','FLAT fractional (iter27)'),('act','ACTIVITY-NORMALISED')):
    f,dd,roi=solve(mode)
    print("%-34s %10.5f%% %9.3f %+13.2f%%"%(lbl,100*f,100*dd,100*roi))
