"""FULL MODEL: cross-EXCHANGE dislocation + cross-ASSET flow + own microstructure.
Target: sign of Bitfinex next-minute return. Walk-forward. Report ACCURACY."""
import numpy as np, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/inversion')
from load import load_1m
def roll(x,k,fn='mean'):
    M=len(x);o=np.full(M,np.nan);v=np.nan_to_num(x)
    c=np.cumsum(np.insert(v,0,0.0));m=(c[k:]-c[:-k])/k
    if fn=='mean': o[k-1:]=m
    else:
        c2=np.cumsum(np.insert(v*v,0,0.0));var=(c2[k:]-c2[:-k])/k-m*m
        o[k-1:]=np.sqrt(np.maximum(var,0.0)*k/(k-1))
    return o
class Stumps:
    def __init__(s,n=250,lr=0.05,bins=32,sub=0.7,seed=0):
        s.n=n;s.lr=lr;s.bins=bins;s.sub=sub;s.rng=np.random.default_rng(seed)
    def fit(s,Xb,y):
        s.base=y.mean();pred=np.full(len(y),s.base);s.tr=[];B=s.bins
        for _ in range(s.n):
            g=y-pred;m=s.rng.random(len(y))<s.sub;gi=g[m];Xi=Xb[m]
            best=(None,-1,None)
            for j in range(Xi.shape[1]):
                sm=np.bincount(Xi[:,j],weights=gi,minlength=B)
                cn=np.bincount(Xi[:,j],minlength=B).astype(float)
                cs=np.cumsum(sm);cc=np.cumsum(cn);tot=cs[-1];tc=cc[-1]
                lf=cc[:-1];rg=tc-lf;ok=(lf>=200)&(rg>=200)
                if not ok.any(): continue
                sl=cs[:-1];sr=tot-sl
                gain=np.where(ok,sl*sl/np.maximum(lf,1)+sr*sr/np.maximum(rg,1),-1)
                k=int(np.argmax(gain))
                if gain[k]>best[1]: best=(j,gain[k],k)
            j,_,k=best
            if j is None: break
            left=Xb[:,j]<=k
            vl=g[left].mean() if left.any() else 0.0
            vr=g[~left].mean() if (~left).any() else 0.0
            s.tr.append((j,k,vl,vr));pred=pred+s.lr*np.where(left,vl,vr)
        return s
    def predict(s,Xb):
        p=np.full(len(Xb),s.base)
        for j,k,vl,vr in s.tr: p=p+s.lr*np.where(Xb[:,j]<=k,vl,vr)
        return p
BTCB=np.load('/tmp/ticks/min_BTCUSDT.npy')
for bn,bf in [('NEOUSDT','NEO'),('BTCUSDT','BTC'),('LTCBTC','LTC')]:
    B=np.load('/tmp/ticks/min_%s.npy'%bn)
    a=load_1m(bf)
    if a is None: continue
    bt=(a[:,0]/1000.0).astype(np.int64); bc=a[:,2]
    nt=B[:,0].astype(np.int64)
    common,ia,ib=np.intersect1d(bt,nt,return_indices=True)
    if len(common)<50000: continue
    pb=bc[ia]; pn=B[ib,1]; of=B[ib,2]; vol=B[ib,3]
    _,ic,ig=np.intersect1d(common,BTCB[:,0].astype(np.int64),return_indices=True)
    btc_r=np.zeros(len(common)); btc_o=np.zeros(len(common))
    bp=BTCB[ig,1]; brr=np.zeros(len(bp)); brr[1:]=np.log(np.maximum(bp[1:],1e-12)/np.maximum(bp[:-1],1e-12))
    btc_r[ic]=brr; btc_o[ic]=BTCB[ig,2]
    rb=np.zeros(len(pb)); rb[1:]=np.log(np.maximum(pb[1:],1e-12)/np.maximum(pb[:-1],1e-12))
    rn=np.zeros(len(pn)); rn[1:]=np.log(np.maximum(pn[1:],1e-12)/np.maximum(pn[:-1],1e-12))
    lr=np.log(np.maximum(pn,1e-12))-np.log(np.maximum(pb,1e-12))
    F={}
    for k in (10,30,60):
        F['disloc%d'%k]=lr-roll(lr,k)
    sd=roll(lr,60,'std')
    F['disloc_z']=(lr-roll(lr,60))/np.maximum(sd,1e-12)
    F['binance_ret']=rn; F['binance_ret3']=roll(rn,3); F['binance_ofi']=of
    F['binance_ofi3']=roll(of,3)
    F['bfx_ret']=rb; F['bfx_ret3']=roll(rb,3)
    F['btc_ret']=btc_r; F['btc_ret3']=roll(btc_r,3); F['btc_ofi']=btc_o
    F['sig']=roll(rb,30,'std')
    F['zvol']=(np.log(np.maximum(vol,1e-9))-roll(np.log(np.maximum(vol,1e-9)),60))/np.maximum(roll(np.log(np.maximum(vol,1e-9)),60,'std'),1e-12)
    F['disloc_x_sig']=F['disloc30']*np.nan_to_num(F['sig'])
    keys=sorted(F.keys())
    idx=np.arange(70,len(common)-2)
    g=(common[idx+1]-common[idx]==60)&(common[idx]-common[idx-1]==60)
    idx=idx[g]
    X=np.stack([F[k][idx] for k in keys],1)
    y=rb[idx+1]
    s30=F['sig'][idx]
    ok=np.isfinite(y)&np.isfinite(X).all(1)&np.isfinite(s30)&(s30>0)&(np.abs(y/s30)<20)
    X=X[ok];y=y[ok];tt=common[idx][ok];s30=s30[ok]
    months=(tt-tt.min())/86400.0/30.44
    TOT=months.max(); edges=np.linspace(TOT*0.4,TOT,7)
    oof=np.full(len(y),np.nan)
    for i in range(6):
        tr=months<edges[i]; te=(months>=edges[i])&(months<edges[i+1])
        if tr.sum()<5000 or te.sum()<500: continue
        Xt=X[tr];Xe=X[te];Bn=32
        bt2=np.zeros_like(Xt,dtype=np.int16);be=np.zeros_like(Xe,dtype=np.int16)
        for j in range(X.shape[1]):
            q=np.unique(np.quantile(Xt[:,j],np.linspace(0,1,Bn+1)[1:-1]))
            bt2[:,j]=np.searchsorted(q,Xt[:,j]);be[:,j]=np.searchsorted(q,Xe[:,j])
        m=Stumps(seed=i).fit(bt2,np.clip(y[tr]/s30[tr],-5,5))
        oof[te]=m.predict(be)
    v=np.isfinite(oof); pv=oof[v]; yv=y[v]
    print()
    print("=== %s (Bitfinex follower) ===  n_oos=%d  corr %+.4f"%(bf,v.sum(),np.corrcoef(pv,yv)[0,1]))
    print("  %-12s %8s %10s %11s"%("slice","n","ACCURACY","mean bp"))
    for fr in (1.0,0.10,0.02,0.01,0.005,0.002,0.001):
        k=max(50,int(len(pv)*fr))
        sel=np.argsort(-np.abs(pv))[:k]
        acc=100*(np.sign(pv[sel])==np.sign(yv[sel])).mean()
        bp=1e4*(np.sign(pv[sel])*yv[sel]).mean()
        print("  top %-8s %8d %9.2f%% %+10.3f"%("%.1f%%"%(100*fr),k,acc,bp))
    np.save('/tmp/ticks/xex_%s.npy'%bf,oof); np.save('/tmp/ticks/xexy_%s.npy'%bf,y); np.save('/tmp/ticks/xext_%s.npy'%bf,tt)
