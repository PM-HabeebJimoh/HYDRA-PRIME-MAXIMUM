"""WR / DD / MONTHLY ROI for EURUSD and BTC-USD, 2026, month by month.
Real equity paths with compounding and drawdown - the numbers actually asked for."""
import json, math, numpy as np, datetime as dt
D=json.load(open('/tmp/m2026.json'))
def roll(x,k):
    N=len(x);o=np.full(N,np.nan);v=np.nan_to_num(x)
    c=np.cumsum(np.insert(v,0,0.0));c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(c[k:]-c[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0.0)*k/(k-1)); return o
def Nd(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def prem(s): return 2*(Nd(s/2)-Nd(-s/2))
def trades(t,c,W=3,IVM=1.25):
    t=np.array(t,float); c=np.array(c,float); N=len(c)
    r=np.zeros(N); r[1:]=np.log(np.maximum(c[1:],1e-12)/np.maximum(c[:-1],1e-12))
    s20=roll(r,20)
    idx=np.arange(25,N-W-1)
    pay=np.array([abs(c[min(i+W,N-1)]-c[i])/c[i] for i in idx])
    sig=s20[idx]; sT=sig*math.sqrt(W)*IVM
    pr=np.array([prem(x) if np.isfinite(x) and x>0 else np.nan for x in sT])
    ret=(pay-pr)/pr            # return on premium paid
    ok=np.isfinite(ret)
    return t[idx][ok], ret[ok]
def path(rets,f):
    cap=1.0;peak=1.0;dd=0.0
    for x in rets:
        cap*=(1.0+f*x)
        if cap<=0: return 0.0,1.0
        peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
    return cap,dd
def solve(rets,cap_dd):
    lo,hi=1e-6,1.0
    for _ in range(50):
        m=(lo+hi)/2; cpt,dd=path(rets,m)
        if cpt<=0 or dd>cap_dd: hi=m
        else: lo=m
    return (lo,)+path(rets,lo)
ORD=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug']
for key,lab in (('eur','EURUSD=X'),('btc','BTC-USD')):
    t,r=trades(D[key]['t'],D[key]['c'])
    mon=np.array([dt.datetime.utcfromtimestamp(x).strftime('%b') for x in t])
    print("="*80)
    print("%s  2026 — WR / DD / MONTHLY ROI  (straddle, IV=1.25x, full allocation)"%lab)
    print("="*80)
    print("%-6s %7s %9s %13s %11s %13s"%("month","trades","WR%","mean/trade","maxDD","MONTHLY ROI"))
    allr=[]
    for m in ORD:
        k=mon==m
        if k.sum()<6: continue
        rr=r[k]; allr.append(rr)
        cap,dd=path(rr,1.0)
        print("%-6s %7d %8.1f%% %+12.2f%% %10.2f%% %+12.2f%%"%(
            m,len(rr),100*(rr>0).mean(),100*rr.mean(),100*dd,100*(cap-1)))
    A=np.concatenate(allr)
    cap,dd=path(A,1.0)
    mo=(t.max()-t.min())/86400.0/30.44
    print("-"*80)
    print("%-6s %7d %8.1f%% %+12.2f%% %10.2f%% %+12.2f%%  <- full period, %.1f months"%(
        "TOTAL",len(A),100*(A>0).mean(),100*A.mean(),100*dd,100*((cap**(1/mo)-1) if cap>0 else -1),mo))
    print()
    print("  DD-CONSTRAINED SIZING (fraction of capital per straddle):")
    print("  %-10s %12s %10s %14s"%("DD cap","size","real DD","MONTHLY ROI"))
    for cd in (0.04,0.10,0.20):
        f,cpt,dd2=solve(A,cd)
        roi=(cpt**(1/mo)-1) if cpt>0 else -1
        print("  %-10s %11.4f%% %9.2f%% %+13.2f%%"%("%.0f%%"%(100*cd),100*f,100*dd2,100*roi))
    print()
