"""Walk-forward SIGNED-return model. Ablation: chart-only vs +flow vs +flow*liquidity."""
import numpy as np, math
d=np.load('/tmp/ticks/dir.npz',allow_pickle=True)
X=d['X'];y=d['y'];ya=d['yabs'];t0=d['t0'];t1=d['t1'];sym=d['sym'];keys=list(d['keys'])
ic={k:i for i,k in enumerate(keys)}
CHART=['bb','bb_ext','s20','z_inten','z_vol','runs','z_esp','vpin','z_lam']
FLOW=['ofi','ofi_1','ofi_2','ofi_c3','ofi_c12','z_ofi','bigofi','bigsh_x_bigofi','ac','bestshare','z_clipr']
INTER=['ofi_x_lam','ofi_div_depth','ofi_x_vpin','ofi_x_esp','ofi_x_bb']
class Stumps:
    def __init__(s,n=200,lr=0.05,bins=24,sub=0.7,seed=0):
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
                lf=cc[:-1];rg=tc-lf;ok=(lf>=100)&(rg>=100)
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
months=(t0-t0.min())/86400.0/30.44
TOT=months.max();edges=np.linspace(TOT*0.40,TOT,7)
def run(cols,tag,target):
    ci=[ic[c] for c in cols]
    oof=np.full(len(y),np.nan)
    for i in range(6):
        tr=months<edges[i];te=(months>=edges[i])&(months<edges[i+1])
        if tr.sum()<3000 or te.sum()<300: continue
        Xt=X[np.ix_(tr,ci)];Xe=X[np.ix_(te,ci)]
        B=24;bt=np.zeros_like(Xt,dtype=np.int16);be=np.zeros_like(Xe,dtype=np.int16)
        for j in range(len(ci)):
            q=np.unique(np.quantile(Xt[:,j],np.linspace(0,1,B+1)[1:-1]))
            bt[:,j]=np.searchsorted(q,Xt[:,j]);be[:,j]=np.searchsorted(q,Xe[:,j])
        m=Stumps(seed=i).fit(bt,target[tr]);oof[te]=m.predict(be)
    v=np.isfinite(oof)
    c=np.corrcoef(oof[v],y[v])[0,1]
    # directional accuracy on confident predictions
    pv=oof[v];yv=y[v]
    line=[]
    for fr in (0.20,0.10,0.05):
        k=int(len(pv)*fr)
        lo=np.argsort(pv)[:k]; hi=np.argsort(-pv)[:k]
        ls=yv[hi]; ss=yv[lo]
        spread=(ls.mean()-ss.mean())/2
        acc=100*(np.concatenate([ls>0,ss<0]).mean())
        line.append((spread,acc))
    print("%-26s corr %+.4f | L-S@20%% %+.4f acc %.1f%% | @10%% %+.4f acc %.1f%% | @5%% %+.4f acc %.1f%%"%(
        tag,c,line[0][0],line[0][1],line[1][0],line[1][1],line[2][0],line[2][1]),flush=True)
    return oof
print("n=%d  target = vol-normalised SIGNED return over next %dh"%(len(y),4))
print()
print("--- predicting DIRECTION (signed) ---")
a=run(CHART,'chart only',y)
b=run(CHART+FLOW,'chart + order flow',y)
c=run(CHART+FLOW+INTER,'chart + flow + liquidity',y)
np.save('/tmp/ticks/oof_dir.npy',c)
np.save('/tmp/ticks/oof_dir_chart.npy',a)
print()
print("--- predicting MAGNITUDE (|move|), for comparison ---")
m=run(CHART+FLOW+INTER,'chart + flow + liquidity',ya)
np.save('/tmp/ticks/oof_mag.npy',m)
