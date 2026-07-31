"""v01T-OMEGA v2: V82's directional engine + v01T's squeeze gate.

v01T's straddle is dead (proven: predicts volatility, not direction).
But its SQUEEZE DETECTOR (BB% extreme + HV<0.8) is a genuine volatility-
expansion predictor. V82 supplies the DIRECTION. Combine them:
  direction  <- V82 1H trend + streak + 3-bar return
  timing     <- v01T squeeze on the 5m bar (compression before expansion)
"""
from load import *; from v82 import *
import numpy as np, bisect, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega')
from omega.indicators import bb_percent, hv_ratio

def gates_v01t(f):
    C=f[:,2]
    bb=bb_percent(C); hv=hv_ratio(C)
    g1=np.nan_to_num((bb<10)|(bb>90),nan=False).astype(bool)
    g2=np.nan_to_num(hv<0.8,nan=False).astype(bool)
    return g1,g2,bb,hv

def harvest(f,h,mode,cost=0.02,tmult=2.0):
    tu,td,r3,st=compute_1h_forecast(h); A=np.concatenate([[np.nan],atr(f)[:-1]])
    g1,g2,bb,hv=gates_v01t(f)
    ht=list(h[:,0]); O,C,H,L=f[:,1],f[:,2],f[:,3],f[:,4]
    out=[]; busy=-1
    for i in range(60,len(f)-12):
        if i<busy: continue
        k=bisect.bisect_right(ht,f[i,0])-1
        if k<60: continue
        a=A[i]
        if not np.isfinite(a) or a<=0: continue
        if tu[k] and st[k]>=2 and r3[k]>0: d=1
        elif td[k] and st[k]<=1 and r3[k]<0: d=-1
        else: continue
        if mode=='squeeze'   and not (g1[i] and g2[i]): continue
        if mode=='hvonly'    and not g2[i]: continue
        if mode=='bandonly'  and not g1[i]: continue
        if mode=='align':
            # squeeze AND band edge on the correct side for the trend
            if not (g1[i] and g2[i]): continue
            if d==1 and not (bb[i]<10): continue     # buy the LOWER band in an uptrend
            if d==-1 and not (bb[i]>90): continue
        S=C[i]; stop=S-d*a; targ=S+d*tmult*a; ex=None; jj=i+12
        for j in range(i+1,i+12):
            op=O[j]
            if d==1:
                if op<=stop or op>=targ: ex=op;jj=j;break
                if L[j]<=stop: ex=stop;jj=j;break
                if H[j]>=targ: ex=targ;jj=j;break
            else:
                if op>=stop or op<=targ: ex=op;jj=j;break
                if H[j]>=stop: ex=stop;jj=j;break
                if L[j]<=targ: ex=targ;jj=j;break
        if ex is None: ex=C[i+12]
        out.append((f[i,0],f[jj,0],(ex-S)*d/a-cost))
        busy=jj
    return out

def ddsolve(ev,target=0.04):
    R=np.array([e[2] for e in ev])
    if len(R)<10: return None
    t0=min(e[0] for e in ev); t1=max(e[1] for e in ev); mo=(t1-t0)/86400000/30.44
    def sim(fr):
        cap=1.0;peak=1.0;dd=0.0
        for r in R:
            cap*=(1+fr*r)
            if cap<=0: return None,1.0
            peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
        return cap,dd
    lo,hi=1e-6,0.5
    for _ in range(45):
        m=(lo+hi)/2; c,dd=sim(m)
        if c is None or dd>target: hi=m
        else: lo=m
    c,dd=sim(lo)
    se=R.std(ddof=1)/np.sqrt(len(R))
    return dict(n=len(R),months=mo,meanR=R.mean(),se=se,t=R.mean()/se,
                wr=100*(R>0).mean(),risk=lo,dd=dd,roi=c**(1/mo)-1,permo=len(R)/mo)

if __name__=='__main__':
    syms=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
    D={}
    for s in syms:
        a=load_1m(s)
        if a is None or len(a)<50000: continue
        D[s]=(resample(a,5),resample(a,60))
    print('loaded',len(D),'symbols\n')
    print('%-12s %8s %7s %8s %8s %8s %9s %10s'%('mode','n','tr/mo','WR%','meanR','t-stat','risk%','ROI/mo@DD4'))
    for mode in ('v82','hvonly','bandonly','squeeze','align'):
        ev=[]
        for s,(f,h) in D.items(): ev+=harvest(f,h,mode)
        ev.sort()
        r=ddsolve(ev)
        if r is None: print('%-12s too few'%mode); continue
        print('%-12s %8d %7.0f %8.2f %+8.4f %8.1f %9.4f %+10.2f%%'%(
            mode,r['n'],r['permo'],r['wr'],r['meanR'],r['t'],100*r['risk'],100*r['roi']))
