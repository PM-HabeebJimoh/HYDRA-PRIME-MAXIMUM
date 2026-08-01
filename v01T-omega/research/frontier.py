"""THE DD FRONTIER: what ROI is reachable at every drawdown budget?
Direct path simulation on real trades. No formulas, no bootstrap."""
import numpy as np
A=np.load('/tmp/v82/events.npy'); P=A[A[:,4]==0]
P=P[np.argsort(P[:,0])]; R=P[:,2]; n=len(P)
t0=P[:,0].min(); mo=(P[:,1].max()-t0)/86400000/30.44
ev=np.concatenate([np.stack([P[:,0],np.zeros(n),np.arange(n)],1),
                   np.stack([P[:,1],np.ones(n),np.arange(n)],1)])
ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
ET=ev[:,1].astype(np.int8); EI=ev[:,2].astype(np.int64)

def sim(f):
    cap=1.0;peak=1.0;dd=0.0
    st=np.zeros(n);lv=np.zeros(n,bool)
    for k in range(len(ET)):
        i=EI[k]
        if ET[k]==0: st[i]=cap*f; lv[i]=True
        else:
            if lv[i]:
                cap+=st[i]*R[i]; lv[i]=False
                if cap<=0: return 0.0,1.0
                if cap>peak: peak=cap
                d=(peak-cap)/peak
                if d>dd: dd=d
    return cap,dd

def solve(target):
    lo,hi=1e-9,3.0
    for _ in range(52):
        m=(lo+hi)/2; c,d=sim(m)
        if c<=0 or d>target: hi=m
        else: lo=m
    c,d=sim(lo)
    return lo,d,(c**(1/mo)-1) if c>0 else -1.0

print("v01T-OMEGA v2 DRAWDOWN FRONTIER — real trades, %d, %.1f months"%(n,mo))
print("%-8s %12s %9s %16s %14s"%("DD cap","risk/trade","real DD","ROI/mo","x10k -> 1mo"))
out=[]
for t in (0.02,0.03,0.04,0.05,0.06,0.08,0.10,0.12,0.15,0.20,0.25,0.30,0.40,0.50):
    f,d,roi=solve(t)
    out.append((t,f,d,roi))
    print("%-8s %11.4f%% %8.2f%% %+15.2f%% %14s"%(f"{100*t:.0f}%",100*f,100*d,100*roi,f"${10000*(1+roi):,.0f}"))
np.save('/tmp/v82/frontier.npy',np.array(out))
print()
tgt=10.0
hit=[o for o in out if o[3]>=tgt]
if hit: print("ROI>=1000%% first reached at DD cap %.0f%% (real DD %.2f%%, risk %.4f%%)"%(100*hit[0][0],100*hit[0][2],100*hit[0][1]))
else: print("ROI>=1000%% NOT reached even at DD 50%%")
