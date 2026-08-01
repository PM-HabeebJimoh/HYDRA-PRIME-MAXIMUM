"""WR / DD / MONTHLY ROI on the walk-forward out-of-sample predictions.
Concurrent positions, one capital pool, DD enforced by direct path simulation."""
import numpy as np, os
d=np.load('feat.npz',allow_pickle=True)
y=d['y'];t0=d['t0'];t1=d['t1'];sym=d['sym']
oof=np.load('oof.npy')
v=np.isfinite(oof)
y=y[v];t0=t0[v];t1=t1[v];sym=sym[v];p=oof[v]
mo=(t1.max()-t0.min())/86400000/30.44
print("out-of-sample window: %.1f months, %d candidate trades"%(mo,len(y)))

def sim(ret,T0,T1,f,cap_dd=None):
    n=len(ret)
    ev=np.concatenate([np.stack([T0,np.zeros(n),np.arange(n)],1),
                       np.stack([T1,np.ones(n),np.arange(n)],1)])
    ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
    ET=ev[:,1].astype(np.int8); EI=ev[:,2].astype(np.int64)
    cap=1.0;peak=1.0;dd=0.0;st=np.zeros(n);lv=np.zeros(n,bool)
    for k in range(len(ET)):
        i=EI[k]
        if ET[k]==0: st[i]=cap*f; lv[i]=True
        else:
            if lv[i]:
                cap+=st[i]*ret[i]; lv[i]=False
                if cap<=0: return 0.0,1.0
                if cap>peak: peak=cap
                dd=max(dd,(peak-cap)/peak)
    return cap,dd
def solve(ret,T0,T1,cap_dd):
    lo,hi=1e-8,2.0
    for _ in range(46):
        m=(lo+hi)/2; c,dd=sim(ret,T0,T1,m)
        if c<=0 or dd>cap_dd: hi=m
        else: lo=m
    c,dd=sim(ret,T0,T1,lo)
    return lo,dd,(c**(1/mo)-1) if c>0 else -1.0

print()
print("%-8s %7s %7s %8s | %11s %8s %14s"%("slice","n","WR%","mean","prem/trade","real DD","MONTHLY ROI"))
for frac in (0.25,0.10,0.05,0.02,0.01):
    k=int(len(p)*frac)
    idx=np.argsort(-p)[:k]
    idx=idx[np.argsort(t0[idx])]
    ret=y[idx]; T0=t0[idx]; T1=t1[idx]
    for cd in (0.04,):
        f,dd,roi=solve(ret,T0,T1,cd)
        print("top %-4s %7d %6.2f%% %+7.2f%% | %10.4f%% %7.2f%% %+13.2f%%"%(
            "%.0f%%"%(100*frac),len(ret),100*(ret>0).mean(),100*ret.mean(),100*f,100*dd,100*roi))
print()
print("--- top 2%, varying DD budget ---")
k=int(len(p)*0.02); idx=np.argsort(-p)[:k]; idx=idx[np.argsort(t0[idx])]
ret=y[idx];T0=t0[idx];T1=t1[idx]
print("%-10s %11s %9s %14s"%("DD cap","prem/trade","real DD","MONTHLY ROI"))
for cd in (0.02,0.04,0.06,0.10,0.15,0.20):
    f,dd,roi=solve(ret,T0,T1,cd)
    print("%-10s %10.4f%% %8.2f%% %+13.2f%%"%("%.0f%%"%(100*cd),100*f,100*dd,100*roi))
