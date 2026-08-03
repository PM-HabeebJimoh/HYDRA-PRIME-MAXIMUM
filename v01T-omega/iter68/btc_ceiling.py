"""
iter68b: The audit says BTC is the ONLY pair with real tradable direction edge:
   NEO  CC 86.98% -> OC 57.21%   (gap/bounce carried it: CO 89.77%)
   LTC  CC 81.34% -> OC 51.46%   (gap carried it: CO 84.11%)
   BTC  CC 74.06% -> OC 68.69%   (gap only 57.97% -> the edge is REAL)

So: how far can the TRADABLE (open->close) BTC direction accuracy go with
selectivity? Does it reach 80%? Map it finely and report the honest ceiling,
with binomial confidence intervals so small-n slices cannot fool me again
(that was the iter53 error: 80% on n=20, CI 62.5-97.5%).
"""
import numpy as np, sys, math
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/inversion')
from load import load_1m
exec(open('/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/iter68/audit87.py').read().split("BTCB=np.load")[0].split('"""')[2])

BTCB=np.load('/tmp/ticks/min_BTCUSDT.npy')
B=np.load('/tmp/ticks/min_BTCUSDT.npy'); a=load_1m('BTC')
bt=(a[:,0]/1000.0).astype(np.int64); b_open=a[:,1]; b_close=a[:,2]
nt=B[:,0].astype(np.int64)
common,ia,ib=np.intersect1d(bt,nt,return_indices=True)
pb=b_close[ia]; po=b_open[ia]; pn=B[ib,1]; of=B[ib,2]; vol=B[ib,3]
_,ic,ig=np.intersect1d(common,BTCB[:,0].astype(np.int64),return_indices=True)
btc_r=np.zeros(len(common)); btc_o=np.zeros(len(common))
bp=BTCB[ig,1]; brr=np.zeros(len(bp)); brr[1:]=np.log(np.maximum(bp[1:],1e-12)/np.maximum(bp[:-1],1e-12))
btc_r[ic]=brr; btc_o[ic]=BTCB[ig,2]
lcl=np.log(np.maximum(pb,1e-12)); lop=np.log(np.maximum(po,1e-12))
rb=np.zeros(len(pb)); rb[1:]=np.diff(lcl)
rn=np.zeros(len(pn)); rn[1:]=np.log(np.maximum(pn[1:],1e-12)/np.maximum(pn[:-1],1e-12))
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
g=(common[idx+1]-common[idx]==60)&(common[idx]-common[idx-1]==60); idx=idx[g]
X=np.stack([F[k][idx] for k in keys],1); s30=F['sig'][idx]
y=lcl[idx+1]-lop[idx+1]     # TRADABLE
ok=np.isfinite(y)&np.isfinite(X).all(1)&np.isfinite(s30)&(s30>0)&(np.abs(y/np.maximum(s30,1e-12))<20)
X=X[ok]; y=y[ok]; tt=common[idx][ok]; s=s30[ok]
months=(tt-tt.min())/86400.0/30.44; TOT=months.max(); edges=np.linspace(TOT*0.4,TOT,7)
oof=np.full(len(y),np.nan)
for i in range(6):
    trm=months<edges[i]; tem=(months>=edges[i])&(months<edges[i+1])
    if trm.sum()<5000 or tem.sum()<500: continue
    Xt=X[trm];Xe=X[tem];Bn=32
    bt2=np.zeros_like(Xt,dtype=np.int16);be=np.zeros_like(Xe,dtype=np.int16)
    for j in range(X.shape[1]):
        q=np.unique(np.quantile(Xt[:,j],np.linspace(0,1,Bn+1)[1:-1]))
        bt2[:,j]=np.searchsorted(q,Xt[:,j]);be[:,j]=np.searchsorted(q,Xe[:,j])
    m=Stumps(seed=i).fit(bt2,np.clip(y[trm]/s[trm],-5,5))
    oof[tem]=m.predict(be)
v=np.isfinite(oof); pv=oof[v]; yv=y[v]
print("="*84)
print("BTC | TRADABLE direction (enter next OPEN, exit next CLOSE) | ERA 2018-19 OOS")
print("="*84)
print(f"n_oos={v.sum():,}  corr={np.corrcoef(pv,yv)[0,1]:+.4f}")
print(f"{'slice':<12}{'n':>8}{'ACCURACY':>11}{'95% CI':>18}{'>=80%?':>8}")
for fr in (1.0,0.10,0.05,0.02,0.01,0.005,0.002,0.001,0.0005):
    k=max(30,int(len(pv)*fr))
    sel=np.argsort(-np.abs(pv))[:k]
    w=int((np.sign(pv[sel])==np.sign(yv[sel])).sum()); n=len(sel)
    acc=100*w/n
    se=math.sqrt(acc/100*(1-acc/100)/n)*100
    lo,hi=acc-1.96*se,acc+1.96*se
    print(f"{'top %.2f%%'%(100*fr):<12}{n:>8}{acc:>10.2f}%{('[%.1f, %.1f]'%(lo,hi)):>18}{('YES' if lo>=80 else 'no'):>8}")
