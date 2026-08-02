"""MONTH-BY-MONTH 2026 BACKTEST — real Bitfinex XLM perp daily bars.

Tests the FOUNDATION of the volatility-magnitude system per month:
  vol persistence = corr(trailing vol, forward |move|)
plus the straddle payoff at IV = 1.25x trailing vol (the iter34 construction).

Strictly causal: features at day i, outcome over days i+1..i+W.
"""
import numpy as np, json, math, datetime as dt
R=np.array(json.load(open('/tmp/y26/XLM_1D_2026.json')),dtype=float)
t=R[:,0]; o=R[:,1]; c=R[:,2]; h=R[:,3]; l=R[:,4]
N=len(c); W=3
def roll(x,k,fn='mean'):
    M=len(x);out=np.full(M,np.nan);v=np.nan_to_num(x)
    cs=np.cumsum(np.insert(v,0,0.0));m=(cs[k:]-cs[:-k])/k
    if fn=='mean': out[k-1:]=m
    else:
        c2=np.cumsum(np.insert(v*v,0,0.0));var=(c2[k:]-c2[:-k])/k-m*m
        out[k-1:]=np.sqrt(np.maximum(var,0.0)*k/(k-1))
    return out
r=np.zeros(N); r[1:]=np.log(np.maximum(c[1:],1e-12)/np.maximum(c[:-1],1e-12))
s20=roll(r,20,'std')
def Nd(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def prem(sig_T): return 2*(Nd(sig_T/2)-Nd(-sig_T/2))
IVM=1.25
idx=np.arange(25,N-W-1)
fwd=np.array([np.max(np.abs(c[i+1:i+1+W]-c[i]))/c[i] for i in idx])
sig=s20[idx]
pay=np.array([abs(c[min(i+W,N-1)]-o[i+1])/o[i+1] for i in idx])
sigT=sig*math.sqrt(W)*IVM
pr=np.array([prem(x) if np.isfinite(x) and x>0 else np.nan for x in sigT])
ret=(pay-pr)/pr
mon=np.array([dt.datetime.utcfromtimestamp(x/1000).month for x in t[idx]])
names={1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',7:'Jul',8:'Aug'}
print("="*82)
print("2026 MONTH-BY-MONTH — real Bitfinex tXLMF0:USTF0 daily, %d bars"%N)
print("="*82)
print("%-5s %6s %11s %13s %12s %11s %10s"%("month","days","vol persist","straddle ret","WR%","realised vol","tot |move|"))
allp=[];allr=[]
for m in range(1,9):
    k=mon==m
    if k.sum()<8: 
        print("%-5s %6d   (too few days)"%(names[m],k.sum())); continue
    x=sig[k]; y=fwd[k]; rr=ret[k]
    ok=np.isfinite(x)&np.isfinite(y)
    p=np.corrcoef(x[ok],y[ok])[0,1] if ok.sum()>5 else np.nan
    okr=np.isfinite(rr)
    allp.append(p); allr.append(rr[okr].mean())
    cm=c[idx][k]
    tot=100*np.sum(np.abs(np.diff(cm))/cm[:-1]) if len(cm)>1 else 0.0
    print("%-5s %6d %+11.4f %+12.2f%% %11.1f%% %10.3f%% %9.2f%%"%(
        names[m],k.sum(),p,100*rr[okr].mean(),100*(rr[okr]>0).mean(),
        100*np.nanmean(x),tot))
print("-"*82)
ap=np.array(allp); ar=np.array(allr)
print("%-5s %6s %+11.4f %+12.2f%%"%("MEAN","",np.nanmean(ap),100*np.nanmean(ar)))
print("   months with POSITIVE vol persistence: %d/%d"%((ap>0).sum(),len(ap)))
print("   months with POSITIVE straddle return: %d/%d"%((ar>0).sum(),len(ar)))
print()
print("2018-2021 BASELINE (13 instruments, 6h): vol persistence = +0.3682, positive 13/13")
