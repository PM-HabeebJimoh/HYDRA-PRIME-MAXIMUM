"""Those TEST ROIs are extreme. Before believing anything, stress the assumptions.
Each test is a way the real world differs from the simulation."""
import numpy as np, datetime as dt
A=np.load('/tmp/v82/events.npy'); P=A[A[:,4]==0]; P=P[np.argsort(P[:,0])]
def pack(S,R=None):
    n=len(S); R=S[:,2] if R is None else R
    ev=np.concatenate([np.stack([S[:,0],np.zeros(n),np.arange(n)],1),
                       np.stack([S[:,1],np.ones(n),np.arange(n)],1)])
    ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
    mo=(S[:,1].max()-S[:,0].min())/86400000/30.44
    return n,R,ev[:,1].astype(np.int8),ev[:,2].astype(np.int64),mo
def sim(pk,f):
    n,R,ET,EI,mo=pk
    cap=1.0;peak=1.0;dd=0.0;st=np.zeros(n);lv=np.zeros(n,bool)
    for k in range(len(ET)):
        i=EI[k]
        if ET[k]==0: st[i]=cap*f;lv[i]=True
        else:
            if lv[i]:
                cap+=st[i]*R[i];lv[i]=False
                if cap<=0: return 0.0,1.0,-1.0
                if cap>peak: peak=cap
                d=(peak-cap)/peak
                if d>dd: dd=d
    return cap,dd,(cap**(1/mo)-1)
def solve(pk,t):
    lo,hi=1e-9,3.0
    for _ in range(50):
        m=(lo+hi)/2;c,d,_=sim(pk,m)
        if c<=0 or d>t: hi=m
        else: lo=m
    return lo
base=pack(P)
COST_BASE=0.02
print("STRESS TESTS at DD target 15%  (baseline ROI/mo shown first)")
f=solve(base,0.15); c,d,r=sim(base,f)
print("  baseline                       risk %.4f%%  DD %.2f%%  ROI %+.2f%%/mo"%(100*f,100*d,100*r))
print()
# 1. higher cost
print("1) COST — baseline used 2%% of stop. Raise it:")
for extra in (0.03,0.05,0.10,0.20,0.30):
    Rn=P[:,2]-(extra-COST_BASE)
    pk=pack(P,Rn); f2=solve(pk,0.15); c2,d2,r2=sim(pk,f2)
    print("   cost %4.0f%% of stop -> risk %.4f%%  ROI %+.2f%%/mo"%(100*extra,100*f2,100*r2))
print()
# 2. slippage on EVERY entry (missed the good fill)
print("2) ENTRY SLIPPAGE — you don't get the close, you get worse:")
for sl in (0.05,0.10,0.25,0.50):
    Rn=P[:,2]-sl
    pk=pack(P,Rn); f2=solve(pk,0.15); c2,d2,r2=sim(pk,f2)
    print("   -%.2fR per trade -> risk %.4f%%  ROI %+.2f%%/mo"%(sl,100*f2,100*r2))
print()
# 3. capacity: you can't take every signal
print("3) CAPACITY — take only a random subset of signals:")
rng=np.random.default_rng(3)
for frac in (0.75,0.50,0.25):
    m=rng.random(len(P))<frac
    pk=pack(P[m]); f2=solve(pk,0.15); c2,d2,r2=sim(pk,f2)
    print("   %3.0f%% of signals (n=%6d) -> risk %.4f%%  ROI %+.2f%%/mo"%(100*frac,m.sum(),100*f2,100*r2))
print()
# 4. execution delay: enter 1 bar later
print("4) worst-case: shuffle trade ORDER (destroys lucky sequencing)")
res=[]
for s in range(20):
    rs=np.random.default_rng(s)
    idx=rs.permutation(len(P))
    Q=P.copy(); Q[:,2]=P[idx,2]
    pk=pack(Q); f2=solve(pk,0.15); c2,d2,r2=sim(pk,f2)
    res.append(r2)
res=np.array(res)
print("   20 shuffles: ROI median %+.2f%%  p5 %+.2f%%  p95 %+.2f%%"%(
    100*np.median(res),100*np.percentile(res,5),100*np.percentile(res,95)))
