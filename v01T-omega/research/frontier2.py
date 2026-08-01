"""HONEST DD FRONTIER on CAUSAL events (lookahead removed)."""
import numpy as np
A=np.load('/tmp/v82/events_causal.npy'); A=A[np.argsort(A[:,0])]
R=A[:,2]; n=len(A)
mo=(A[:,1].max()-A[:,0].min())/86400000/30.44
ev=np.concatenate([np.stack([A[:,0],np.zeros(n),np.arange(n)],1),
                   np.stack([A[:,1],np.ones(n),np.arange(n)],1)])
ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
ET=ev[:,1].astype(np.int8); EI=ev[:,2].astype(np.int64)
def sim(f):
    cap=1.0;peak=1.0;dd=0.0;st=np.zeros(n);lv=np.zeros(n,bool)
    for k in range(len(ET)):
        i=EI[k]
        if ET[k]==0: st[i]=cap*f;lv[i]=True
        else:
            if lv[i]:
                cap+=st[i]*R[i];lv[i]=False
                if cap<=0: return 0.0,1.0
                if cap>peak: peak=cap
                d=(peak-cap)/peak
                if d>dd: dd=d
    return cap,dd
def solve(t):
    lo,hi=1e-9,3.0
    for _ in range(50):
        m=(lo+hi)/2;c,d=sim(m)
        if c<=0 or d>t: hi=m
        else: lo=m
    c,d=sim(lo); return lo,d,(c**(1/mo)-1) if c>0 else -1.0
print("CAUSAL v2 — n=%d  %.1f months  WR %.2f%%  meanR %+.4f  t=%.1f"%(
    n,mo,100*(R>0).mean(),R.mean(),R.mean()/(R.std(ddof=1)/np.sqrt(n))))
print("baseline for 3:1 barrier on driftless walk = 25.00%% WR; we have %.2f%% (+%.2f pts)"%(
    100*(R>0).mean(),100*(R>0).mean()-25))
print()
print("%-9s %12s %9s %15s %14s"%("DD cap","risk/trade","real DD","ROI/mo","x$10k"))
res=[]
for t in (0.04,0.05,0.06,0.08,0.10,0.15,0.20,0.25,0.30,0.40,0.50,0.60):
    f,d,r=solve(t); res.append((t,f,d,r))
    print("%-9s %11.4f%% %8.2f%% %+14.2f%% %14s"%(f"{100*t:.0f}%",100*f,100*d,100*r,f"${10000*(1+r):,.0f}"))
np.save('/tmp/v82/frontier_causal.npy',np.array(res))
hit=[x for x in res if x[3]>=10.0]
print()
print("ROI>=1000%% first at DD %.0f%%"%(100*hit[0][0]) if hit else "ROI>=1000%% NOT reached up to DD 60%%")
