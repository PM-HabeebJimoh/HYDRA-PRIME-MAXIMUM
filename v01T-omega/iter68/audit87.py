"""
iter68: AUDIT MY OWN 87.01% DIRECTION CLAIM.

The user asks: "are you sure the accuracy >80% direction?"

iter67 PROVED that close-to-close targets are contaminated by bid-ask bounce:
NEO c_vs_vwap showed 59.28% close-to-close but 44.83% on the tradable
next-open->next-close target.

beyond/full.py - the file that produced 87.01% - uses:
    bc = a[:,2]                                  <- CLOSE column
    rb[1:] = log(pb[1:]/pb[:-1])                 <- CLOSE-to-CLOSE return
    y = rb[idx+1]                                <- predicts close[i+1] vs close[i]

That is EXACTLY the contaminated target. So the 87.01% may be measuring bounce,
not tradable direction.

TEST: same model, same features, same walk-forward, three targets:
  (a) CC : close[i+1] / close[i]      - what I reported (contaminated)
  (b) OC : close[i+1] / OPEN[i+1]     - TRADABLE (enter next open, exit next close)
  (c) CO : open[i+1]  / close[i]      - the gap alone (pure bounce component)

If (a) is high and (b) collapses, my 87% claim was wrong and I must retract it.
Bitfinex CSV columns: MTS OPEN CLOSE HIGH LOW VOLUME -> open=col1, close=col2.
"""
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
print("="*100)
print("AUDIT: is the 87.01% real DIRECTION, or bid-ask bounce?")
print("ERA 2018-19 | identical model/features/walk-forward | only the TARGET changes")
print("="*100)

for bn,bf in [('NEOUSDT','NEO'),('LTCBTC','LTC'),('BTCUSDT','BTC')]:
    B=np.load('/tmp/ticks/min_%s.npy'%bn)
    a=load_1m(bf)
    if a is None: continue
    bt=(a[:,0]/1000.0).astype(np.int64)
    b_open=a[:,1]; b_close=a[:,2]        # MTS OPEN CLOSE HIGH LOW VOL
    nt=B[:,0].astype(np.int64)
    common,ia,ib=np.intersect1d(bt,nt,return_indices=True)
    if len(common)<50000: continue
    pb=b_close[ia]; po=b_open[ia]
    pn=B[ib,1]; of=B[ib,2]; vol=B[ib,3]
    _,ic,ig=np.intersect1d(common,BTCB[:,0].astype(np.int64),return_indices=True)
    btc_r=np.zeros(len(common)); btc_o=np.zeros(len(common))
    bp=BTCB[ig,1]; brr=np.zeros(len(bp)); brr[1:]=np.log(np.maximum(bp[1:],1e-12)/np.maximum(bp[:-1],1e-12))
    btc_r[ic]=brr; btc_o[ic]=BTCB[ig,2]

    lcl=np.log(np.maximum(pb,1e-12)); lop=np.log(np.maximum(po,1e-12))
    rb=np.zeros(len(pb)); rb[1:]=np.diff(lcl)                 # close->close (as in full.py)
    rn=np.zeros(len(pn)); rn[1:]=np.log(np.maximum(pn[1:],1e-12)/np.maximum(pn[:-1],1e-12))
    lr=lcl-np.log(np.maximum(pn,1e-12))*0 + (np.log(np.maximum(pn,1e-12))-lcl)  # binance-bitfinex
    lr=np.log(np.maximum(pn,1e-12))-lcl

    F={}
    for k in (10,30,60): F['disloc%d'%k]=lr-roll(lr,k)
    sd=roll(lr,60,'std'); F['disloc_z']=(lr-roll(lr,60))/np.maximum(sd,1e-12)
    F['binance_ret']=rn; F['binance_ret3']=roll(rn,3); F['binance_ofi']=of
    F['binance_ofi3']=roll(of,3); F['bfx_ret']=rb; F['bfx_ret3']=roll(rb,3)
    F['btc_ret']=btc_r; F['btc_ret3']=roll(btc_r,3); F['btc_ofi']=btc_o
    F['sig']=roll(rb,30,'std')
    lv=np.log(np.maximum(vol,1e-9))
    F['zvol']=(lv-roll(lv,60))/np.maximum(roll(lv,60,'std'),1e-12)
    F['disloc_x_sig']=F['disloc30']*np.nan_to_num(F['sig'])
    keys=sorted(F.keys())

    idx=np.arange(70,len(common)-2)
    g=(common[idx+1]-common[idx]==60)&(common[idx]-common[idx-1]==60)
    idx=idx[g]
    X=np.stack([F[k][idx] for k in keys],1)
    s30=F['sig'][idx]

    TARGETS={
      'CC close[i+1]/close[i]  (what I reported)': lcl[idx+1]-lcl[idx],
      'OC close[i+1]/OPEN[i+1] (TRADABLE)'       : lcl[idx+1]-lop[idx+1],
      'CO open[i+1]/close[i]   (gap = bounce)'   : lop[idx+1]-lcl[idx],
    }
    print()
    print(f"===== {bf} =====")
    print(f"{'target':<44}{'n_oos':>9}{'corr':>9}{'top10%':>9}{'top1%':>9}{'top0.5%':>9}")
    for tname,yv in TARGETS.items():
        ok=np.isfinite(yv)&np.isfinite(X).all(1)&np.isfinite(s30)&(s30>0)&(np.abs(yv/np.maximum(s30,1e-12))<20)
        Xo=X[ok]; y=yv[ok]; tt=common[idx][ok]; s=s30[ok]
        if len(y)<20000: print(f"{tname:<44}{'too few':>9}"); continue
        months=(tt-tt.min())/86400.0/30.44
        TOT=months.max(); edges=np.linspace(TOT*0.4,TOT,7)
        oof=np.full(len(y),np.nan)
        for i in range(6):
            trm=months<edges[i]; tem=(months>=edges[i])&(months<edges[i+1])
            if trm.sum()<5000 or tem.sum()<500: continue
            Xt=Xo[trm];Xe=Xo[tem];Bn=32
            bt2=np.zeros_like(Xt,dtype=np.int16);be=np.zeros_like(Xe,dtype=np.int16)
            for j in range(Xo.shape[1]):
                q=np.unique(np.quantile(Xt[:,j],np.linspace(0,1,Bn+1)[1:-1]))
                bt2[:,j]=np.searchsorted(q,Xt[:,j]);be[:,j]=np.searchsorted(q,Xe[:,j])
            m=Stumps(seed=i).fit(bt2,np.clip(y[trm]/s[trm],-5,5))
            oof[tem]=m.predict(be)
        v=np.isfinite(oof); pv=oof[v]; yv2=y[v]
        if v.sum()<1000: print(f"{tname:<44}{'no oos':>9}"); continue
        cc=np.corrcoef(pv,yv2)[0,1]
        row=f"{tname:<44}{int(v.sum()):>9}{cc:>+9.4f}"
        for fr in (0.10,0.01,0.005):
            k=max(50,int(len(pv)*fr))
            sel=np.argsort(-np.abs(pv))[:k]
            acc=100*(np.sign(pv[sel])==np.sign(yv2[sel])).mean()
            row+=f"{acc:>8.2f}%"
        print(row)
