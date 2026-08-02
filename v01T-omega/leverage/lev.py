"""LEVERAGE APPLIED TO REAL TRADE SEQUENCES.
Not arithmetic - actual path simulation with compounding, per fee tier."""
import numpy as np
def run(bf, fee_bp, frac, lev, slice_frac=0.005):
    p=np.load('/tmp/ticks/xex_%s.npy'%bf); y=np.load('/tmp/ticks/xexy_%s.npy'%bf); t=np.load('/tmp/ticks/xext_%s.npy'%bf)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    k=max(50,int(len(p)*slice_frac))
    sel=np.argsort(-np.abs(p))[:k]
    sel=sel[np.argsort(t[sel])]
    r=np.sign(p[sel])*y[sel] - fee_bp*1e-4     # per-trade return on notional
    mo=(t.max()-t.min())/86400.0/30.44
    cap=1.0; peak=1.0; dd=0.0
    for x in r:
        cap*= (1.0 + frac*lev*x)
        if cap<=0: return 0.0,1.0,-1.0,len(r),mo
        peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
    return cap,dd,(cap**(1/mo)-1),len(r),mo
FEES={'Bitfinex taker 40bp':40.0,'Binance taker 20bp':20.0,'Binance VIP 8bp':8.0,'VIP9 4bp':4.0,'maker 0bp':0.0}
print("NEO, top 0.5% confidence, 86.98% accuracy — LEVERAGE SWEEP")
print("%-22s %6s %8s %10s %12s %14s"%("fee tier","lev","frac","trades","maxDD","MONTHLY ROI"))
for lbl,fee in FEES.items():
    for lev in (1,5,10,25):
        cap,dd,roi,n,mo=run('NEO',fee,1.0,lev)
        if roi<=-1: print("%-22s %5dx %8s %10d %12s %14s"%(lbl,lev,"100%",n,"BUST","BUST")); continue
        print("%-22s %5dx %8s %10d %11.2f%% %+13.2f%%"%(lbl,lev,"100%",n,100*dd,100*roi))
    print()
