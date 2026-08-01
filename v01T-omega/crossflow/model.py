"""FULL DIRECTION MODEL: predict SIGN of alt's next-minute return using
cross-asset flow + returns from ALL other symbols (upstream), plus own-asset
microstructure. Walk-forward. Report DIRECTIONAL ACCURACY."""
import numpy as np, math
SYMS=['BTCUSDT','BNBUSDT','NEOUSDT','QTUMUSDT','ETHBTC','LTCBTC']
D={s:np.load('/tmp/ticks/min_%s.npy'%s) for s in SYMS}
# common minute grid
common=None
for s in SYMS:
    t=D[s][:,0]
    common=t if common is None else np.intersect1d(common,t)
print("common minutes across %d symbols: %d"%(len(SYMS),len(common)))
P={};O={};V={};N={}
for s in SYMS:
    A=D[s]; idx=np.searchsorted(A[:,0],common)
    P[s]=A[idx,1]; O[s]=A[idx,2]; V[s]=A[idx,3]; N[s]=A[idx,4]
R={s:np.concatenate([[0.0],np.log(np.maximum(P[s][1:],1e-12)/np.maximum(P[s][:-1],1e-12))]) for s in SYMS}
def roll(x,k,fn='mean'):
    M=len(x);o=np.full(M,np.nan);v=np.nan_to_num(x)
    c=np.cumsum(np.insert(v,0,0.0));m=(c[k:]-c[:-k])/k
    if fn=='mean': o[k-1:]=m
    else:
        c2=np.cumsum(np.insert(v*v,0,0.0));var=(c2[k:]-c2[:-k])/k-m*m
        o[k-1:]=np.sqrt(np.maximum(var,0.0)*k/(k-1))
    return o
def z(x,k=60): return (x-roll(x,k))/np.maximum(roll(x,k,'std'),1e-12)

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

results={}
for tgt in ['QTUMUSDT','NEOUSDT','BNBUSDT']:
    F={}
    for s in SYMS:                      # cross-asset upstream block
        F['ofi_'+s]=O[s]
        F['r_'+s]=R[s]
        F['r2_'+s]=roll(R[s],2)
        F['r5_'+s]=roll(R[s],5)
        F['ofi3_'+s]=roll(O[s],3)
        F['zv_'+s]=z(np.log(np.maximum(V[s],1e-9)))
    own=tgt
    sig=roll(R[own],30,'std')
    F['own_sig']=sig
    F['own_z']=z(R[own],30)
    F['own_ofi_x_sig']=O[own]*np.nan_to_num(sig)
    # BTC-relative: alt lagging BTC is the core lead-lag state
    F['gap_btc']=roll(R[own],5)-roll(R['BTCUSDT'],5)
    F['gap_btc15']=roll(R[own],15)-roll(R['BTCUSDT'],15)
    keys=sorted(F.keys())
    M=len(common)
    fwd=np.concatenate([np.log(np.maximum(P[own][1:],1e-12)/np.maximum(P[own][:-1],1e-12)),[np.nan]])
    idx=np.arange(70,M-2)
    cont=(common[idx+1]-common[idx])==60.0
    idx=idx[cont]
    X=np.stack([F[k][idx] for k in keys],1)
    y=fwd[idx]
    ynorm=y/np.maximum(sig[idx],1e-12)
    ok=np.isfinite(y)&np.isfinite(X).all(1)&np.isfinite(ynorm)&(np.abs(ynorm)<20)
    X=X[ok];y=y[ok];tt=common[idx][ok];ynorm=ynorm[ok]
    months=(tt-tt.min())/86400.0/30.44
    TOT=months.max(); edges=np.linspace(TOT*0.4,TOT,7)
    oof=np.full(len(y),np.nan)
    for i in range(6):
        tr=months<edges[i]; te=(months>=edges[i])&(months<edges[i+1])
        if tr.sum()<5000 or te.sum()<500: continue
        Xt=X[tr];Xe=X[te];B=32
        bt=np.zeros_like(Xt,dtype=np.int16);be=np.zeros_like(Xe,dtype=np.int16)
        for j in range(X.shape[1]):
            q=np.unique(np.quantile(Xt[:,j],np.linspace(0,1,B+1)[1:-1]))
            bt[:,j]=np.searchsorted(q,Xt[:,j]);be[:,j]=np.searchsorted(q,Xe[:,j])
        m=Stumps(seed=i).fit(bt,np.clip(ynorm[tr],-5,5))
        oof[te]=m.predict(be)
    v=np.isfinite(oof)
    pv=oof[v];yv=y[v]
    c=np.corrcoef(pv,yv)[0,1]
    print()
    print("=== %s ===  n_oos=%d  corr %+.4f"%(tgt,v.sum(),c))
    print("  %-12s %9s %10s %12s"%("confidence","n","ACCURACY","mean bp"))
    for fr in (1.0,0.20,0.10,0.05,0.02,0.01):
        k=int(len(pv)*fr)
        sel=np.argsort(-np.abs(pv))[:k]
        pred=np.sign(pv[sel]); act=np.sign(yv[sel])
        acc=100*(pred==act).mean()
        bp=1e4*(pred*yv[sel]).mean()
        print("  top %-8s %9d %9.2f%% %+11.3f"%("%.0f%%"%(100*fr),k,acc,bp))
    results[tgt]=(oof,v,y,tt)
    np.save('/tmp/ticks/dirmodel_%s.npy'%tgt,oof)
