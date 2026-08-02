"""Find leverage that maximises ROI subject to a DD cap. Real path sim."""
import numpy as np
def load(bf,slice_frac):
    p=np.load('/tmp/ticks/xex_%s.npy'%bf); y=np.load('/tmp/ticks/xexy_%s.npy'%bf); t=np.load('/tmp/ticks/xext_%s.npy'%bf)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    k=max(50,int(len(p)*slice_frac))
    sel=np.argsort(-np.abs(p))[:k]; sel=sel[np.argsort(t[sel])]
    return np.sign(p[sel])*y[sel], t[sel], (t.max()-t.min())/86400.0/30.44
def sim(r,mo,fee,lev):
    cap=1.0;peak=1.0;dd=0.0
    for x in r-fee*1e-4:
        cap*=(1.0+lev*x)
        if cap<=0: return 0.0,1.0,-1.0
        peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
    return cap,dd,cap**(1/mo)-1
def solve(r,mo,fee,cap_dd):
    lo,hi=0.01,200.0
    for _ in range(50):
        m=(lo+hi)/2; c,dd,roi=sim(r,mo,fee,m)
        if c<=0 or dd>cap_dd: hi=m
        else: lo=m
    return (lo,)+sim(r,mo,fee,lo)
print("DD-CONSTRAINED LEVERAGE — NEO top 0.5% (86.98% acc), Binance VIP 8bp")
r,t,mo=load('NEO',0.005)
print("  %d trades over %.1f months = %.1f trades/month"%(len(r),mo,len(r)/mo))
print()
print("%-10s %10s %10s %14s"%("DD cap","leverage","real DD","MONTHLY ROI"))
for cd in (0.04,0.05,0.10,0.15,0.20,0.25,0.30):
    L,c,dd,roi=solve(r,mo,8.0,cd)
    flag=" <== >500%" if roi>5.0 else ""
    print("%-10s %9.1fx %9.2f%% %+13.2f%%%s"%("%.0f%%"%(100*cd),L,100*dd,100*roi,flag))
print()
print("SAME, across fee tiers, DD capped at 20%")
print("%-22s %10s %10s %14s"%("fee","leverage","real DD","MONTHLY ROI"))
for lbl,fee in (('Binance taker 20bp',20.0),('Binance VIP 8bp',8.0),('VIP9 4bp',4.0),('maker 0bp',0.0)):
    L,c,dd,roi=solve(r,mo,fee,0.20)
    print("%-22s %9.1fx %9.2f%% %+13.2f%%"%(lbl,L,100*dd,100*roi))
print()
print("SLICE SWEEP (VIP 8bp, DD 20%) — more trades vs higher accuracy")
print("%-12s %8s %10s %10s %14s"%("slice","trades","leverage","real DD","MONTHLY ROI"))
for sf in (0.001,0.002,0.005,0.01,0.02,0.05):
    r2,t2,mo2=load('NEO',sf)
    L,c,dd,roi=solve(r2,mo2,8.0,0.20)
    print("top %-8s %8d %9.1fx %9.2f%% %+13.2f%%"%("%.1f%%"%(100*sf),len(r2),L,100*dd,100*roi))
