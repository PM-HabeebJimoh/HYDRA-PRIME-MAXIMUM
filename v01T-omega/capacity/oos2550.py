"""25x/50x clears >500%. Before reporting: does it hold OUT OF SAMPLE,
and does it survive a liquidation check? At 50x, one -2% adverse move = -100%."""
import numpy as np
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}; FEE=4.0
def get(nm,sf=0.005):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm); y=np.load('/tmp/ticks/xexy_%s.npy'%nm); t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    k=int(len(p)*sf); sel=np.argsort(-np.abs(p))[:k]; sel=sel[np.argsort(t[sel])]
    return np.sign(p[sel])*y[sel]-(SPREAD[nm]+FEE)*1e-4, t[sel]
def path(r,lev,mo):
    cap=1.0;peak=1.0;dd=0.0
    for x in r:
        cap*=(1.0+lev*x)
        if cap<=0: return 0.0,1.0,-1.0
        peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
    return cap,dd,cap**(1/mo)-1
print("OUT-OF-SAMPLE SPLIT (first half -> second half), measured costs")
print("%-5s %5s | %12s %9s | %13s %9s"%("asset","lev","TRAIN ROI","DD","TEST ROI","DD"))
for nm in ('NEO','LTC','BTC'):
    r,t=get(nm)
    half=t.min()+(t.max()-t.min())/2
    a=t<half; b=t>=half
    if a.sum()<30 or b.sum()<30: continue
    moa=(t[a].max()-t[a].min())/86400.0/30.44
    mob=(t[b].max()-t[b].min())/86400.0/30.44
    for lev in (25,50):
        c1,d1,r1=path(r[a],lev,moa)
        c2,d2,r2=path(r[b],lev,mob)
        f1="BUST" if c1<=0 else "%+.2f%%"%(100*r1)
        f2="BUST" if c2<=0 else "%+.2f%%"%(100*r2)
        print("%-5s %4dx | %12s %8.1f%% | %13s %8.1f%%"%(nm,lev,f1,100*d1,f2,100*d2))
print()
print("LIQUIDATION CHECK — at leverage L, a single adverse move of 1/L wipes out")
print("%-5s %8s %10s %12s %14s"%("asset","lev","liq @","worst trade","liquidated?"))
for nm in ('NEO','LTC','BTC'):
    r,_=get(nm)
    for lev in (25,50):
        liq=100.0/lev
        worst=100*abs(r.min())
        print("%-5s %7dx %9.2f%% %11.2f%% %14s"%(nm,lev,liq,worst,"YES" if worst>=liq else "no"))
