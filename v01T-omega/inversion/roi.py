"""WR / DD / MONTHLY ROI for the vol-Q1 band-only long straddle.
Needs timestamps -> re-harvest with time, sequential portfolio, DD-capped sizing."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import load_1m, resample
import numpy as np
from still import bb_hv_vec
SY=["XLM","TRX","BTC","ETH","XRP","EOS","LTC","NEO","XMR","ETC","IOT","BSV","XTZ"]
W=4
def Nd(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def prem_of(s): return 2*(Nd(s/2)-Nd(-s/2))
rows=[]
for si,s in enumerate(SY):
    a=load_1m(s)
    if a is None or len(a)<50000: continue
    f=resample(a,60); c=f[:,2]; t=f[:,0]
    if len(c)<200: continue
    bb,hv=bb_hv_vec(c)
    r=np.zeros(len(c)); r[1:]=c[1:]/c[:-1]-1
    N=len(c)
    cx=np.cumsum(np.insert(r,0,0.0)); cx2=np.cumsum(np.insert(r*r,0,0.0))
    k=20; m=(cx[k:]-cx[:-k])/k; v=(cx2[k:]-cx2[:-k])/k-m*m
    s20=np.full(N,np.nan); s20[k-1:]=np.sqrt(np.maximum(v,0.0)*k/(k-1))
    atb=(bb<10)|(bb>90)
    for i in range(30,N-W-2):
        if not atb[i]: continue
        if not np.isfinite(s20[i]) or s20[i]<=0: continue
        e=i+1; S0=f[e,1]; j=min(e+W,N-1)
        rows.append((t[e],t[j],s20[i],abs(c[j]-S0)/S0,si))
D=np.array(rows); D=D[np.argsort(D[:,0])]
np.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),'q1_rows.npy'),D)
t0,t1,sg,payf,sym=D.T
thr=np.quantile(sg,0.2)
m=sg<=thr
print("vol-Q1 subset: n=%d of %d (threshold s20<=%.6f)"%(m.sum(),len(D),thr))
for IVM in (1.10,1.25,1.40):
    prem=np.array([prem_of(x) for x in sg[m]*math.sqrt(W)*IVM])
    ret=(payf[m]-prem)/prem           # return on premium
    T0=t0[m]; T1=t1[m]
    mo=(T1.max()-T0.min())/86400000/30.44
    n=len(ret)
    # portfolio: allocate f of equity to PREMIUM per trade, concurrent
    ev=np.concatenate([np.stack([T0,np.zeros(n),np.arange(n)],1),
                       np.stack([T1,np.ones(n),np.arange(n)],1)])
    ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
    ET=ev[:,1].astype(np.int8); EI=ev[:,2].astype(np.int64)
    def sim(fr):
        cap=1.0;peak=1.0;dd=0.0;st=np.zeros(n);lv=np.zeros(n,bool)
        for kk in range(len(ET)):
            i=EI[kk]
            if ET[kk]==0: st[i]=cap*fr; lv[i]=True
            else:
                if lv[i]:
                    cap+=st[i]*ret[i]; lv[i]=False
                    if cap<=0: return 0.0,1.0
                    peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
        return cap,dd
    def solve(cap_dd):
        lo,hi=1e-7,1.0
        for _ in range(46):
            mid=(lo+hi)/2; c_,d_=sim(mid)
            if c_<=0 or d_>cap_dd: hi=mid
            else: lo=mid
        c_,d_=sim(lo); return lo,d_,(c_**(1/mo)-1) if c_>0 else -1
    print()
    print("IV = %.2fx  | n=%d  %.1f months  WIN RATE %.2f%%  mean/trade %+.2f%% of premium"%(
        IVM,n,mo,100*(ret>0).mean(),100*ret.mean()))
    print("  %-10s %12s %9s %14s"%("DD cap","premium/trade","real DD","MONTHLY ROI"))
    for cd in (0.04,0.10,0.20):
        fr,dd,roi=solve(cd)
        print("  %-10s %11.4f%% %8.2f%% %+13.2f%%"%("%.0f%%"%(100*cd),100*fr,100*dd,100*roi))
