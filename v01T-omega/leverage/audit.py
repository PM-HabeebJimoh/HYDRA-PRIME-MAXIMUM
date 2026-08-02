"""ZERO negative months out of 12, and +35,000%/mo. That is not a strategy,
that is a bug. Audit before reporting anything."""
import numpy as np
p=np.load('/tmp/ticks/xex_NEO.npy'); y=np.load('/tmp/ticks/xexy_NEO.npy'); t=np.load('/tmp/ticks/xext_NEO.npy')
v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
print("1) OVERLAP CHECK — are trades sequential or concurrent?")
k=int(len(p)*0.02); sel=np.argsort(-np.abs(p))[:k]; sel=sel[np.argsort(t[sel])]
ts=t[sel]
gaps=np.diff(ts)
print("   n=%d  minutes between trades: median %.0f  min %.0f"%(len(ts),np.median(gaps),gaps.min()))
print("   trades in the SAME minute: %d"%(gaps==0).sum())
print("   holding period is 1 minute; gaps < 1 min mean OVERLAP -> capital reused")
print("   fraction with gap < 1 min: %.1f%%"%(100*(gaps<60).mean()))
print()
print("2) THE COMPOUNDING ASSUMPTION")
r=np.sign(p[sel])*y[sel]-8.0*1e-4
print("   mean per-trade return %.5f = %.2f bp"%(r.mean(),1e4*r.mean()))
print("   trades/month %.1f"%(len(r)/((t.max()-t.min())/86400.0/30.44)))
print("   at 10.8x, per-trade = %.4f%% of capital"%(100*10.8*r.mean()))
n_mo=len(r)/((t.max()-t.min())/86400.0/30.44)
print("   compounded over %.0f trades/mo: (1+%.5f)^%.0f = %.2fx"%(
    n_mo,10.8*r.mean(),n_mo,(1+10.8*r.mean())**n_mo))
print("   => the ROI comes from COMPOUNDING every trade at full size.")
print()
print("3) IS THAT PHYSICALLY POSSIBLE?")
print("   Each trade holds 1 minute. To compound, trade N must SETTLE before N+1.")
print("   If %.1f%% of trades overlap, they share capital and CANNOT all be full size."%(100*(gaps<60).mean()))
print()
print("4) NON-OVERLAPPING TEST — enforce one position at a time")
keep=[];last=-1e18
for i in range(len(ts)):
    if ts[i]>=last+60:
        keep.append(sel[np.argsort(t[sel])][i] if False else i); last=ts[i]
keep=np.array(keep)
r2=r[keep]
mo=(ts.max()-ts.min())/86400.0/30.44
print("   kept %d of %d trades (%.1f%%)"%(len(keep),len(r),100*len(keep)/len(r)))
def sim(rr,lev):
    cap=1.0;peak=1.0;dd=0.0
    for x in rr:
        cap*=(1+lev*x)
        if cap<=0: return 0,1,-1
        peak=max(peak,cap);dd=max(dd,(peak-cap)/peak)
    return cap,dd,cap**(1/mo)-1
for lev in (1,5,10.8):
    c,dd,roi=sim(r2,lev)
    print("   lev %5.1fx  DD %6.2f%%  ROI %+12.2f%%/mo"%(lev,100*dd,100*roi))
