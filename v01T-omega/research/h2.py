"""Harvest ALL streams as tagged events: (t_entry, t_exit, R, symbol, stream).
Two streams per symbol: pullback and breakout. Both are real V82-direction trades."""
from load import *; from v82 import *
import numpy as np, bisect, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega')
from omega.indicators import bb_percent

def harv(f,h,mode,bb_lo=40.0,tm=3.0,cost=0.02):
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
        if mode=='pull':
            if d==1 and not b<bb_lo: continue
            if d==-1 and not b>100-bb_lo: continue
        else:
            if d==1 and not b>100-bb_lo: continue
            if d==-1 and not b<bb_lo: continue
        S=C[i]; stop=S-d*a; targ=S+d*tm*a; ex=None; jj=i+12
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

if __name__=='__main__':
    syms=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
    rec=[]
    for si,s in enumerate(syms):
        a=load_1m(s)
        if a is None or len(a)<50000: continue
        f=resample(a,5); h=resample(a,60)
        for mi,mode in enumerate(('pull','brk')):
            for (t0,t1,R) in harv(f,h,mode): rec.append((t0,t1,R,si,mi))
    A=np.array(rec,dtype=float); A=A[np.argsort(A[:,0])]
    np.save('/tmp/v82/events.npy',A)
    print('events',A.shape, 'pull',(A[:,4]==0).sum(),'brk',(A[:,4]==1).sum())
