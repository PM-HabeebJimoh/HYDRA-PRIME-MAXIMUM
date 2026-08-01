import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import load_1m, resample
import numpy as np
def bb_hv_vec(c, n=20):
    N=len(c)
    cs=np.cumsum(np.insert(c,0,0.0)); cs2=np.cumsum(np.insert(c*c,0,0.0))
    sma=np.full(N,np.nan); std=np.full(N,np.nan)
    sma[n-1:]=(cs[n:]-cs[:-n])/n
    ms=(cs2[n:]-cs2[:-n])/n
    std[n-1:]=np.sqrt(np.maximum(ms-sma[n-1:]**2,0.0))
    up=sma+2*std; lo=sma-2*std; w=up-lo
    bb=np.full(N,50.0); ok=np.isfinite(w)&(w>0)
    bb[ok]=(c[ok]-lo[ok])/w[ok]*100
    bb[~np.isfinite(bb)]=50.0
    r=np.zeros(N); r[1:]=c[1:]/c[:-1]-1
    def rstd(x,k):
        o=np.full(N,np.nan)
        cx=np.cumsum(np.insert(x,0,0.0)); cx2=np.cumsum(np.insert(x*x,0,0.0))
        m=(cx[k:]-cx[:-k])/k; v=(cx2[k:]-cx2[:-k])/k-m*m
        o[k-1:]=np.sqrt(np.maximum(v,0.0)*k/(k-1)); return o
    s5=rstd(r,5); s20=rstd(r,20)
    hv=np.full(N,1.0); g=np.isfinite(s5)&np.isfinite(s20)&(s20>0)
    hv[g]=s5[g]/s20[g]
    return bb,hv
SY=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
W=4

if __name__=='__main__':
    allsig=[];allbase=[]
    print("%-6s %8s %13s %8s %13s %8s"%("sym","sq_n","sq_mean","base_n","base_mean","ratio"),flush=True)
    for s in SY:
        a=load_1m(s)
        if a is None or len(a)<50000: continue
        f=resample(a,60); c=f[:,2]
        if len(c)<200: continue
        bb,hv=bb_hv_vec(c)
        sc=np.where(bb<10,92,np.where(bb>90,85,72))
        elite=((bb<10)|(bb>90))&(hv<0.8)&(sc>=85)
        N=len(c); idx=np.arange(30,N-W)
        mx=np.max(np.stack([np.abs(c[idx+k]-c[idx])/c[idx] for k in range(1,W+1)]),axis=0)
        e=elite[idx]
        if e.sum()<20: continue
        sg=mx[e]; bs=mx[~e]
        allsig.append(sg); allbase.append(bs)
        print("%-6s %8d %12.4f%% %8d %12.4f%% %8.3f"%(s,len(sg),100*sg.mean(),len(bs),100*bs.mean(),sg.mean()/bs.mean()),flush=True)
    S=np.concatenate(allsig); B=np.concatenate(allbase)
    np.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),'sig_moves.npy'),S)
    np.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),'base_moves.npy'),B)
    se=np.sqrt(S.var(ddof=1)/len(S)+B.var(ddof=1)/len(B))
    print()
    print("POOLED squeeze n=%d mean %.4f%% | baseline n=%d mean %.4f%%"%(len(S),100*S.mean(),len(B),100*B.mean()))
    print("difference %+.5f%%   t = %+.2f   ratio = %.4f"%(100*(S.mean()-B.mean()),(S.mean()-B.mean())/se,S.mean()/B.mean()))
