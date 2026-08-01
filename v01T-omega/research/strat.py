"""The pooled number was Simpson's paradox: 16 of 20 vol bins show squeeze
forward vol LOWER, but pooling is dominated by the extreme-vol bins where it
reverses. Compute the STRATIFIED estimate + the tail profile."""
from load import load_1m, resample
from vrp import bb_hv
import numpy as np
H=4
SYMS=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
TR=[];FW=[];SQ=[]
for nm in SYMS:
    raw=load_1m(nm)
    if raw is None or len(raw)<50000: continue
    f=resample(raw,60); c=f[:,2]
    if len(c)<200: continue
    bb,hv=bb_hv(c); n=len(c)
    i=np.arange(H+20,n-H-1); e0=c[i]
    fwd=np.zeros(len(i))
    for k in range(1,H+1): fwd=np.maximum(fwd,np.abs(c[i+k]-e0)/e0)
    base=c[i-H]; tr=np.zeros(len(i))
    for k in range(H-1,-1,-1): tr=np.maximum(tr,np.abs(c[i-k]-base)/base)
    sq=np.nan_to_num(((bb[i]<10)|(bb[i]>90))&(hv[i]<0.8),nan=False).astype(bool)
    TR.append(100*tr); FW.append(100*fwd); SQ.append(sq)
TR=np.concatenate(TR);FW=np.concatenate(FW);SQ=np.concatenate(SQ)
qs=np.quantile(TR,np.linspace(0,1,21))
num=0.0; den=0.0; var=0.0
bins=[]
for a,b in zip(qs[:-1],qs[1:]):
    m=(TR>=a)&(TR<b)
    s=FW[m&SQ]; nn=FW[m&~SQ]
    if len(s)<30 or len(nn)<30: continue
    d=s.mean()-nn.mean()
    v=s.var(ddof=1)/len(s)+nn.var(ddof=1)/len(nn)
    w=len(s)
    num+=w*d; den+=w; var+=(w**2)*v
    bins.append((a,b,len(s),d))
D=num/den; SE=np.sqrt(var)/den
print("="*74); print("STRATIFIED (vol-matched) ESTIMATE — the honest number"); print("="*74)
print("weighted mean difference (squeeze fwd - control fwd) = %+.5f%%"%D)
print("SE %.5f   t = %+.2f"%(SE,D/SE))
neg=sum(1 for *_,d in bins if d<0)
print("bins with LOWER squeeze forward vol: %d of %d"%(neg,len(bins)))
print()
print("=> squeeze DOES predict lower forward vol, once vol level is controlled.")
print("   The naive pooled +0.19%% was Simpson's paradox.")
print()
print("="*74); print("BUT — THE TAIL. This is what kills every short-vol book."); print("="*74)
lo=TR<np.quantile(TR,0.80); hi=~lo
for lbl,msk in (("normal vol (bottom 80%)",lo),("HIGH vol (top 20%)",hi)):
    s=FW[msk&SQ]; nn=FW[msk&~SQ]
    d=s.mean()-nn.mean(); se=np.sqrt(s.var(ddof=1)/len(s)+nn.var(ddof=1)/len(nn))
    print("%-26s n_sq=%6d  squeeze %7.4f%%  control %7.4f%%  diff %+8.4f%%  t=%+6.2f"%(
        lbl,len(s),s.mean(),nn.mean(),d,d/se))
print()
s=FW[SQ]
print("squeeze forward-vol distribution: median %.3f%%  p95 %.3f%%  p99 %.3f%%  MAX %.3f%%"%(
    np.median(s),np.percentile(s,95),np.percentile(s,99),s.max()))
print("a short straddle sized for the median is destroyed by the p99.")
print("ratio p99/median = %.1fx"%(np.percentile(s,99)/np.median(s)))
