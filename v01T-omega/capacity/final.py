"""THE HONEST ANSWER, with MEASURED per-asset costs and MEASURED capacity."""
import numpy as np, sys, os
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/inversion')
from load import load_1m
# MEASURED round-trip effective spread (bp) from real aggressor-flagged prints
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}
# Binance VIP taker fee, round trip, bp (0.02% x 2 = 4bp; VIP9 0.015% x2 = 3bp)
FEE=4.0
def sim(r,lev):
    cap=1.0;peak=1.0;dd=0.0
    for x in r:
        cap*=(1.0+lev*x)
        if cap<=0: return 0.0,1.0
        peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
    return cap,dd
def solve(r,mo,cd):
    lo,hi=0.01,300.0
    for _ in range(50):
        m=(lo+hi)/2; c,dd=sim(r,m)
        if c<=0 or dd>cd: hi=m
        else: lo=m
    c,dd=sim(r,lo); return lo,dd,(c**(1/mo)-1) if c>0 else -1.0
print("%-5s %8s %8s %9s %9s %9s %11s %12s"%("asset","n","acc%","gross","cost","NET bp","lev@DD20","ROI/mo"))
res={}
for nm in ('NEO','LTC','BTC'):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm); y=np.load('/tmp/ticks/xexy_%s.npy'%nm); t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    k=int(len(p)*0.005); sel=np.argsort(-np.abs(p))[:k]; sel=sel[np.argsort(t[sel])]
    gross=1e4*(np.sign(p[sel])*y[sel]).mean()
    acc=100*(np.sign(p[sel])==np.sign(y[sel])).mean()
    cost=SPREAD[nm]+FEE
    r=np.sign(p[sel])*y[sel]-cost*1e-4
    mo=(t.max()-t.min())/86400.0/30.44
    L,dd,roi=solve(r,mo,0.20)
    res[nm]=(sel,t,r,mo,L,roi)
    print("%-5s %8d %7.2f%% %+8.2f %9.2f %+9.2f %10.1fx %+11.2f%%"%(
        nm,len(sel),acc,gross,cost,1e4*r.mean(),L,100*roi))
print()
print("CAPACITY with MEASURED per-minute notional (Binance, from executions):")
NOT={'BTC':166767,'NEO':12303,'LTC':2}
print("%-5s %14s %12s %14s %16s"%("asset","notional/min","cap@10%","trades/mo","PnL/month"))
tot=0
for nm in ('NEO','LTC','BTC'):
    sel,t,r,mo,L,roi=res[nm]
    capital=NOT[nm]*0.10/L
    tpm=len(sel)/mo
    pnl=capital*L*r.mean()*tpm
    tot+=pnl
    print("%-5s %14s %12s %13.1f %15s"%(nm,"${:,}".format(NOT[nm]),
        "${:,.0f}".format(capital),tpm,"${:,.0f}".format(pnl)))
print("%-5s %14s %12s %13s %15s"%("TOTAL","","","","${:,.0f}".format(tot)))
