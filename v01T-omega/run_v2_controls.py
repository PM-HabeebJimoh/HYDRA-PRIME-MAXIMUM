"""Controls for the v2 pullback rule. If these fail, the edge is not real."""
from load import *; from v82 import *
from hybrid import ddsolve
import numpy as np, bisect, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega')
from omega.indicators import bb_percent
rng=np.random.default_rng(11)

def harv(f,h,mode,bb_lo=40,tmult=3.0,cost=0.02):
    tu,td,r3,st=compute_1h_forecast(h); A=np.concatenate([[np.nan],atr(f)[:-1]])
    C=f[:,2]; bb=bb_percent(C); ht=list(h[:,0]); O,H,L=f[:,1],f[:,3],f[:,4]
    out=[];busy=-1
    for i in range(60,len(f)-12):
        if i<busy: continue
        k=bisect.bisect_right(ht,f[i,0])-1
        if k<60: continue
        a=A[i]
        if not np.isfinite(a) or a<=0: continue
        b=bb[i]
        if not np.isfinite(b): continue
        if tu[k] and st[k]>=2 and r3[k]>0: d=1
        elif td[k] and st[k]<=1 and r3[k]<0: d=-1
        else: continue
        if mode in ('v2','flipdir','randdir'):
            if d==1 and not b<bb_lo: continue
            if d==-1 and not b>100-bb_lo: continue
        if mode=='inverted':   # BREAKOUT instead of pullback
            if d==1 and not b>100-bb_lo: continue
            if d==-1 and not b<bb_lo: continue
        if mode=='flipdir': d=-d
        if mode=='randdir': d=1 if rng.random()<0.5 else -1
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
        out.append((f[i,0],f[jj,0],(ex-S)*d/a-cost)); busy=jj
    return out

syms=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
D={}
for s in syms:
    a=load_1m(s)
    if a is None or len(a)<50000: continue
    D[s]=(resample(a,5),resample(a,60))
print('CONTROL SUITE — v01T-OMEGA v2 (bb<40 pullback, T3)')
print('%-24s %8s %8s %9s %8s'%('control','n','WR%','meanR','t-stat'))
base=None
for mode in ('v2','flipdir','randdir','inverted'):
    ev=[]
    for s,(f,h) in D.items(): ev+=harv(f,h,mode)
    R=np.array([e[2] for e in ev]); se=R.std(ddof=1)/np.sqrt(len(R))
    if mode=='v2': base=R
    print('%-24s %8d %8.2f %+9.4f %8.1f'%(mode,len(R),100*(R>0).mean(),R.mean(),R.mean()/se))
# bootstrap p-value vs zero
b=np.array([rng.choice(base,len(base),replace=True).mean() for _ in range(2000)])
print('\nbootstrap 2000x: mean %+.4f  2.5%%=%+.4f  97.5%%=%+.4f  P(mean<=0)=%.4f'%(
    base.mean(),np.percentile(b,2.5),np.percentile(b,97.5),(b<=0).mean()))
