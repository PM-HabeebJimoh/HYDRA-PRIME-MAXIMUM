"""WALK-FORWARD ANTICIPATORY MODEL.
Train on past only, predict forward, trade the top slice. No lookahead anywhere.
Model: gradient-boosted stumps on ranked features (pure numpy, no sklearn)."""
import numpy as np, math, os
d=np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)),'feat.npz'),allow_pickle=True)
X=d['X'];y=d['y'];t0=d['t0'];t1=d['t1'];prem=d['prem'];sym=d['sym'];keys=list(d['keys'])
N,P=X.shape
print("rows %d  features %d  months %.1f"%(N,P,(t1.max()-t0.min())/86400000/30.44))

def rankify(A):
    """map each column to uniform [0,1] ranks - robust to outliers/scale"""
    R=np.empty_like(A)
    for j in range(A.shape[1]):
        o=np.argsort(A[:,j],kind='mergesort')
        rr=np.empty(len(o)); rr[o]=np.arange(len(o))
        R[:,j]=rr/max(len(o)-1,1)
    return R

class Stumps:
    """gradient boosting with depth-1 trees on pre-binned ranks"""
    def __init__(self,n=180,lr=0.06,bins=24,sub=0.7,seed=0):
        self.n=n;self.lr=lr;self.bins=bins;self.sub=sub;self.rng=np.random.default_rng(seed)
    def fit(self,Xb,y):
        self.base=y.mean()
        pred=np.full(len(y),self.base)
        self.tr=[]
        B=self.bins
        for it in range(self.n):
            g=y-pred
            m=self.rng.random(len(y))<self.sub
            gi=g[m]; Xi=Xb[m]
            best=(None,-1,None)
            for j in range(Xi.shape[1]):
                s=np.bincount(Xi[:,j],weights=gi,minlength=B)
                cnt=np.bincount(Xi[:,j],minlength=B).astype(float)
                cs=np.cumsum(s); cc=np.cumsum(cnt)
                tot=cs[-1]; tc=cc[-1]
                lft=cc[:-1]; rgt=tc-lft
                ok=(lft>=50)&(rgt>=50)
                if not ok.any(): continue
                sl=cs[:-1]; sr=tot-sl
                gain=np.where(ok,sl*sl/np.maximum(lft,1)+sr*sr/np.maximum(rgt,1),-1)
                k=int(np.argmax(gain))
                if gain[k]>best[1]: best=(j,gain[k],k)
            j,_,k=best
            if j is None: break
            left=Xb[:,j]<=k
            vl=g[left].mean() if left.any() else 0.0
            vr=g[~left].mean() if (~left).any() else 0.0
            self.tr.append((j,k,vl,vr))
            pred=pred+self.lr*np.where(left,vl,vr)
        return self
    def predict(self,Xb):
        p=np.full(len(Xb),self.base)
        for j,k,vl,vr in self.tr:
            p=p+self.lr*np.where(Xb[:,j]<=k,vl,vr)
        return p

# walk-forward: 6 folds, expanding window, always train on strictly earlier data
months=(t0-t0.min())/86400000/30.44
TOT=months.max()
folds=[]
start=TOT*0.40
edges=np.linspace(start,TOT,7)
for i in range(6):
    tr=months<edges[i]
    te=(months>=edges[i])&(months<edges[i+1])
    if tr.sum()>5000 and te.sum()>500: folds.append((tr,te))
print("folds:",len(folds))
oof=np.full(N,np.nan)
for fi,(tr,te) in enumerate(folds):
    Xtr=X[tr]; Xte=X[te]
    # bin using TRAIN quantiles only
    B=24; edg=[]
    Xb_tr=np.zeros_like(Xtr,dtype=np.int16); Xb_te=np.zeros_like(Xte,dtype=np.int16)
    for j in range(P):
        q=np.quantile(Xtr[:,j],np.linspace(0,1,B+1)[1:-1])
        q=np.unique(q)
        Xb_tr[:,j]=np.searchsorted(q,Xtr[:,j])
        Xb_te[:,j]=np.searchsorted(q,Xte[:,j])
    m=Stumps(seed=fi).fit(Xb_tr,y[tr])
    oof[te]=m.predict(Xb_te)
    print("  fold %d train %6d test %6d"%(fi,tr.sum(),te.sum()),flush=True)
np.save('oof.npy',oof)
v=np.isfinite(oof)
print()
print("OUT-OF-SAMPLE predictions: %d"%v.sum())
c=np.corrcoef(oof[v],y[v])[0,1]
print("corr(pred, actual) = %.4f"%c)
print()
print("%-10s %8s %10s %10s %8s"%("slice","n","mean y","WR%","t"))
pv=oof[v]; yv=y[v]
for frac in (1.0,0.5,0.25,0.10,0.05,0.02,0.01):
    k=int(len(pv)*frac)
    idx=np.argsort(-pv)[:k]
    s=yv[idx]
    se=s.std(ddof=1)/np.sqrt(len(s))
    print("top %-6s %8d %+9.2f%% %9.2f%% %+8.2f"%("%.0f%%"%(100*frac),len(s),100*s.mean(),100*(s>0).mean(),s.mean()/se))
