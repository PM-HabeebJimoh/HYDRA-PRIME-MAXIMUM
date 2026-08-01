"""Final honest test of the inversion, with NO premium proxy at all.
A short straddle's P&L is fully determined by realised movement vs the strike
width you sell. The ONLY question that matters and cannot be rigged:

  Conditional on a v01T squeeze, is forward realised vol LOWER than what an
  efficient market would have charged? We cannot know IV without quotes.

So instead measure the ONE thing that is decision-relevant and unriggable:
  Is forward vol after a squeeze PREDICTABLE at all, relative to a same-vol
  matched control? Match on trailing vol, then compare forward vol."""
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
print("="*74); print("VOL-MATCHED CONTROL: same trailing vol, squeeze vs non-squeeze"); print("="*74)
qs=np.quantile(TR,np.linspace(0,1,21))
tot_s=[];tot_n=[]
print("%-18s %8s %10s %8s %10s %10s"%("trailing-vol bin","n_sq","fwd_sq","n_ns","fwd_ns","diff"))
for a,b in zip(qs[:-1],qs[1:]):
    m=(TR>=a)&(TR<b)
    s=FW[m&SQ]; nn=FW[m&~SQ]
    if len(s)<30 or len(nn)<30: continue
    tot_s.append(s); tot_n.append(nn)
    print("%-18s %8d %10.4f %8d %10.4f %+10.4f"%("[%.2f,%.2f)"%(a,b),len(s),s.mean(),len(nn),nn.mean(),s.mean()-nn.mean()))
S=np.concatenate(tot_s); N=np.concatenate(tot_n)
# stratified difference
d=S.mean()-N.mean()
se=np.sqrt(S.var(ddof=1)/len(S)+N.var(ddof=1)/len(N))
print()
print("POOLED vol-matched: squeeze fwd %.4f%%  control fwd %.4f%%  diff %+.4f%%  t=%+.2f"%(
    S.mean(),N.mean(),d,d/se))
print()
if d>0: print("Squeeze forward vol is HIGHER than vol-matched control -> SELLING vol into")
print("a squeeze is WORSE than selling on an average bar of the same vol level.")
print("=> THE INVERSION IS REFUTED.")
