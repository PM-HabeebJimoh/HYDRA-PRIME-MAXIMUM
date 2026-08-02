"""MONTH-BY-MONTH 2026 for EURUSD and BTC-USD.
Tests the volatility-magnitude foundation (vol persistence) and the
straddle payoff priced at IV = 1.25x trailing vol, exactly as iter46/47."""
import json, math, numpy as np, datetime as dt
D=json.load(open('/tmp/m2026.json'))
def roll(x,k):
    N=len(x);o=np.full(N,np.nan);v=np.nan_to_num(x)
    c=np.cumsum(np.insert(v,0,0.0));c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(c[k:]-c[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0.0)*k/(k-1)); return o
def Nd(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def prem(s): return 2*(Nd(s/2)-Nd(-s/2))
def run(t,c,label,W=3,IVM=1.25):
    t=np.array(t,float); c=np.array(c,float); N=len(c)
    r=np.zeros(N); r[1:]=np.log(np.maximum(c[1:],1e-12)/np.maximum(c[:-1],1e-12))
    s20=roll(r,20)
    idx=np.arange(25,N-W-1)
    fwd=np.array([np.max(np.abs(c[i+1:i+1+W]-c[i]))/c[i] for i in idx])
    pay=np.array([abs(c[min(i+W,N-1)]-c[i])/c[i] for i in idx])
    sig=s20[idx]; sigT=sig*math.sqrt(W)*IVM
    pr=np.array([prem(x) if np.isfinite(x) and x>0 else np.nan for x in sigT])
    ret=(pay-pr)/pr
    mon=np.array([dt.datetime.utcfromtimestamp(x).strftime('%b') for x in t[idx]])
    order=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug']
    print("="*76)
    print("%s — %d real 2026 daily bars"%(label,N))
    print("="*76)
    print("%-6s %7s %13s %15s %9s %12s"%("month","days","vol persist","straddle ret","WR%","realised vol"))
    P=[];S=[]
    for m in order:
        k=mon==m
        if k.sum()<8: continue
        x=sig[k]; y=fwd[k]; rr=ret[k]
        ok=np.isfinite(x)&np.isfinite(y); okr=np.isfinite(rr)
        if ok.sum()<6 or okr.sum()<6: continue
        p=np.corrcoef(x[ok],y[ok])[0,1]
        P.append(p); S.append(rr[okr].mean())
        print("%-6s %7d %+13.4f %+14.2f%% %8.1f%% %11.3f%%"%(
            m,k.sum(),p,100*rr[okr].mean(),100*(rr[okr]>0).mean(),100*np.nanmean(x)))
    P=np.array(P);S=np.array(S)
    print("-"*76)
    print("%-6s %7s %+13.4f %+14.2f%%"%("MEAN","",np.nanmean(P),100*np.nanmean(S)))
    print("  positive persistence %d/%d | profitable months %d/%d"%(
        (P>0).sum(),len(P),(S>0).sum(),len(S)))
    print()
    return P,S
run(D['eur']['t'],D['eur']['c'],"EURUSD=X")
run(D['btc']['t'],D['btc']['c'],"BTC-USD")
print("2018-2021 baseline (13 crypto instruments, 6h): vol persistence +0.3682, positive 13/13")
