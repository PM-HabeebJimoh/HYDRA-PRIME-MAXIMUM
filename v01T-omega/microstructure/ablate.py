"""ABLATION: CHART-ONLY vs TAPE-ONLY vs BOTH. Walk-forward, out of sample.
If TAPE adds nothing over CHART, the whole thesis fails and I say so."""
import numpy as np, math
d=np.load('/tmp/ticks/micro.npz',allow_pickle=True)
X=d['X'];y=d['y'];t0=d['t0'];t1=d['t1'];sym=d['sym'];keys=list(d['keys'])
CHART=['bb','bb_ext','hv','s20']
TAPE=[k for k in keys if k not in CHART]
ic={k:i for i,k in enumerate(keys)}
class Stumps:
    def __init__(s,n=200,lr=0.06,bins=24,sub=0.7,seed=0):
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
                lf=cc[:-1];rg=tc-lf;ok=(lf>=50)&(rg>=50)
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
def run(cols,tag):
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
        m=Stumps(seed=i).fit(bt,y[tr]);oof[te]=m.predict(be)
    v=np.isfinite(oof)
    c=np.corrcoef(oof[v],y[v])[0,1]
    res=[]
    for fr in (0.25,0.10,0.05):
        k=int(v.sum()*fr);ix=np.argsort(-oof[v])[:k];s=y[v][ix]
        res.append((100*s.mean(),100*(s>0).mean()))
    print("%-14s corr %.4f | top25 %+7.2f%% WR%.1f | top10 %+7.2f%% WR%.1f | top5 %+7.2f%% WR%.1f"%(
        tag,c,res[0][0],res[0][1],res[1][0],res[1][1],res[2][0],res[2][1]),flush=True)
    return oof
print("n=%d  chart=%d feats  tape=%d feats"%(len(y),len(CHART),len(TAPE)))
oc=run(CHART,'CHART only')
ot=run(TAPE,'TAPE only')
ob=run(keys,'CHART+TAPE')
np.save('/tmp/ticks/oof_both.npy',ob)
np.save('/tmp/ticks/oof_chart.npy',oc)
