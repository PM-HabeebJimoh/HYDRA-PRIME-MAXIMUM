"""Where does >1000% ACTUALLY break? Push each assumption to failure."""
import numpy as np
A=np.load('/tmp/v82/events.npy'); P=A[A[:,4]==0]; P=P[np.argsort(P[:,0])]
def pack(S,R=None):
    n=len(S); R=S[:,2] if R is None else R
    ev=np.concatenate([np.stack([S[:,0],np.zeros(n),np.arange(n)],1),
                       np.stack([S[:,1],np.ones(n),np.arange(n)],1)])
    ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
    return n,R,ev[:,1].astype(np.int8),ev[:,2].astype(np.int64),(S[:,1].max()-S[:,0].min())/86400000/30.44
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
print("BREAKING POINT SEARCH at DD 15%")
print("\n1) EDGE DECAY — what if the true edge is a fraction of measured?")
for sc in (1.0,0.75,0.50,0.35,0.25,0.15):
    Rn=P[:,2]*sc
    pk=pack(P,Rn); f=solve(pk,0.15); c,d,r=sim(pk,f)
    flag=" <-- BREAKS" if r<10.0 else ""
    print("   edge x%.2f -> meanR %+.4f  ROI %+10.2f%%/mo%s"%(sc,Rn.mean(),100*r,flag))
print("\n2) SLIPPAGE to failure:")
for sl in (0.5,0.7,0.8,0.9,0.95):
    Rn=P[:,2]-sl
    pk=pack(P,Rn); f=solve(pk,0.15); c,d,r=sim(pk,f)
    flag=" <-- BREAKS" if r<10.0 else ""
    print("   -%.2fR/trade -> meanR %+.4f  ROI %+10.2f%%/mo%s"%(sl,Rn.mean(),100*r,flag))
print("\n3) The REAL question: is meanR +0.97 believable?")
R=P[:,2]
print("   meanR %+.4f  median %+.4f  WR %.2f%%"%(R.mean(),np.median(R),100*(R>0).mean()))
u,c2=np.unique(np.round(R,3),return_counts=True)
top=np.argsort(-c2)[:6]
print("   most common outcomes:")
for i in top:
    print("      R=%+7.3f  %6d trades (%5.2f%%)"%(u[i],c2[i],100*c2[i]/len(R)))
print("\n   Expected if pure 3R/-1R with WR w: meanR = 4w-1")
w=(R>0).mean(); print("   WR %.4f -> implied meanR %+.4f  vs actual %+.4f"%(w,4*w-1,R.mean()))
print("\n4) SANITY: a 3:1 barrier on a driftless walk gives WR=25%%. We have %.2f%%."%(100*w))
print("   excess over random = %.2f points. THAT is the whole edge."%(100*w-25))
