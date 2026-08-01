"""Theory says Sharpe 9.39 -> millions of %. Simulation says +100%.
One of them is lying. Find out which, exactly."""
import numpy as np
A=np.load('/tmp/v82/events.npy'); P=A[A[:,4]==0]
t0=A[:,0].min(); t1=A[:,1].max(); mo=(t1-t0)/86400000/30.44
R=P[:,2]

# Build ACTUAL monthly portfolio returns at a fixed small risk, parallel.
def monthly_returns(f):
    n=len(P); t_o=P[:,0]; t_c=P[:,1]
    ev=np.concatenate([np.stack([t_o,np.zeros(n),np.arange(n)],1),
                       np.stack([t_c,np.ones(n),np.arange(n)],1)])
    ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
    cap=1.0; staked=np.zeros(n); live=np.zeros(n,bool)
    marks=[]; curm=-1
    for k in range(len(ev)):
        ts=ev[k,0]; ty=ev[k,1]; i=int(ev[k,2])
        m=int((ts-t0)/86400000/30.44)
        if m!=curm:
            marks.append((m,cap)); curm=m
        if ty==0:
            staked[i]=cap*f; live[i]=True
        else:
            if live[i]: cap+=staked[i]*R[i]; live[i]=False
    marks.append((999,cap))
    eq=np.array([c for _,c in marks])
    return np.diff(np.log(eq))

lr=monthly_returns(0.0005)
lr=lr[np.isfinite(lr)]
print("ACTUAL monthly log-returns at risk=0.05%%: n=%d"%len(lr))
print("  mean %+.4f  sd %.4f  -> REALISED monthly Sharpe = %.3f"%(lr.mean(),lr.std(ddof=1),lr.mean()/lr.std(ddof=1)))
print("  theory predicted 9.387")
print()
print("THE DISCREPANCY IS REAL. Diagnose it:")

# Is the per-trade R distribution fat-tailed / skewed?
from math import sqrt
print("  per-trade R: mean %+.4f sd %.4f skew %.3f kurt %.3f min %.2f max %.2f"%(
    R.mean(),R.std(ddof=1),
    ((R-R.mean())**3).mean()/R.std()**3,
    ((R-R.mean())**4).mean()/R.std()**4-3, R.min(),R.max()))

# CRITICAL: are trades independent, or do they CLUSTER (many open at once, same direction)?
n=len(P); t_o=P[:,0]; t_c=P[:,1]
ev=np.concatenate([np.stack([t_o,np.zeros(n)],1),np.stack([t_c,np.ones(n)],1)])
ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
conc=0; cs=[]
for k in range(len(ev)):
    conc+= 1 if ev[k,1]==0 else -1
    cs.append(conc)
cs=np.array(cs)
print("  concurrency: mean %.2f  median %.0f  p95 %.0f  max %.0f"%(cs.mean(),np.median(cs),np.percentile(cs,95),cs.max()))

# Within a month, how correlated are the trade outcomes? -> effective n per month
mb=((P[:,0]-t0)/86400000/30.44).astype(int)
eff=[]
for m in np.unique(mb):
    v=R[mb==m]
    if len(v)<30: continue
    # effective sample size from the monthly mean's ACTUAL variance vs iid prediction
    eff.append(len(v))
eff=np.array(eff)
print("  trades/month: mean %.0f median %.0f"%(eff.mean(),np.median(eff)))
iid_sharpe = R.mean()/R.std(ddof=1)*np.sqrt(np.median(eff))
print("  iid monthly Sharpe from median count = %.3f"%iid_sharpe)
print("  REALISED = %.3f  -> effective independent trades/month = %.0f (of %.0f)"%(
    lr.mean()/lr.std(ddof=1), (lr.mean()/lr.std(ddof=1))**2/ (R.mean()/R.std(ddof=1))**2, np.median(eff)))
