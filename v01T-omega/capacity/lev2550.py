"""25x and 50x. Directly. On real trade sequences with MEASURED costs.
No hedging, no caveats first - just run it and see what the path does."""
import numpy as np
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}
FEE=4.0
def run(nm,lev,slice_frac=0.005):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm); y=np.load('/tmp/ticks/xexy_%s.npy'%nm); t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    k=int(len(p)*slice_frac); sel=np.argsort(-np.abs(p))[:k]; sel=sel[np.argsort(t[sel])]
    r=np.sign(p[sel])*y[sel]-(SPREAD[nm]+FEE)*1e-4
    mo=(t.max()-t.min())/86400.0/30.44
    cap=1.0;peak=1.0;dd=0.0;bust=False
    for x in r:
        cap*=(1.0+lev*x)
        if cap<=0: bust=True; cap=0.0; break
        peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
    roi=(cap**(1/mo)-1) if cap>0 else -1.0
    # worst single trade at this leverage
    worst=lev*r.min()
    return len(r),mo,roi,dd,bust,worst,r
print("DIRECT LEVERAGE RUN — measured costs, real sequences, top 0.5% slice")
print("%-5s %6s %8s %9s %14s %12s %10s"%("asset","lev","trades","worst tr","MONTHLY ROI","maxDD","result"))
for nm in ('NEO','LTC','BTC'):
    for lev in (10,25,50):
        n,mo,roi,dd,bust,worst,r=run(nm,lev)
        st="BUST" if bust else ("OK" if dd<0.95 else "near-bust")
        print("%-5s %5dx %8d %8.1f%% %+13.2f%% %11.2f%% %10s"%(
            nm,lev,n,100*worst,100*roi if not bust else -100,100*dd,st))
    print()
