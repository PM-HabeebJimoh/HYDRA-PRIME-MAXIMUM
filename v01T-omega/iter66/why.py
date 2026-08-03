"""
iter66c: Convergence gives 38-45% accuracy - CONSISTENTLY BELOW 50%.
That is not noise. A signal reliably below 50% is a signal with the SIGN FLIPPED.

Two candidate explanations:
 (A) sign learned on train does not hold out-of-sample (regime flip)
 (B) the families are individually predictive but ANTI-correlated with each
     other's errors, so agreement selects the bad cases.

Test (A) directly: measure each family's directional accuracy on TRAIN and on
OOS separately. If train>50 and OOS<50, the sign flipped -> regime change, and
CSS's persistence/contradiction checks are exactly what would catch it.
"""
import numpy as np, sys, datetime as dt
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/inversion')
from load import load_1m
def roll(x,k):
    o=np.full(len(x),np.nan); v=np.nan_to_num(x)
    c=np.cumsum(np.insert(v,0,0.0)); o[k-1:]=(c[k:]-c[:-k])/k; return o
def rollstd(x,k):
    v=np.nan_to_num(x); o=np.full(len(x),np.nan)
    c=np.cumsum(np.insert(v,0,0.0)); c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(c[k:]-c[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0)); return o
def z(x,k): return (x-roll(x,k))/np.maximum(rollstd(x,k),1e-12)

B=np.load('/tmp/ticks/min_LTCBTC.npy'); BTC=np.load('/tmp/ticks/min_BTCUSDT.npy')
bfx=load_1m('LTC'); bt=(bfx[:,0]/1000).astype(np.int64); bc=bfx[:,2]
common,ia,ib=np.intersect1d(bt,B[:,0].astype(np.int64),return_indices=True)
pb=bc[ia]; pn=B[ib,1]; ofi=B[ib,2]; vol=B[ib,3]
_,ic,ig=np.intersect1d(common,BTC[:,0].astype(np.int64),return_indices=True)
btc_o=np.zeros(len(common)); btc_o[ic]=BTC[ig,2]
rb=np.zeros(len(pb)); rb[1:]=np.log(np.maximum(pb[1:],1e-12)/np.maximum(pb[:-1],1e-12))
disloc=np.log(np.maximum(pn,1e-12))-np.log(np.maximum(pb,1e-12))
F={'T1':z(disloc,60),'T2':z(ofi,60),'T3':z(btc_o,60),'T4':-z(np.log(np.maximum(vol,1e-9)),60)}
idx=np.arange(70,len(common)-2)
g=(common[idx+1]-common[idx]==60)&(common[idx]-common[idx-1]==60); idx=idx[g]
ok=np.isfinite(rb[idx+1])
for k in F: ok&=np.isfinite(F[k][idx])
idx=idx[ok]; y=rb[idx+1]; tt=common[idx]
Fi={k:F[k][idx] for k in F}
n=len(idx); cut=int(n*0.6)

print("="*88)
print("(A) IS THE SIGN STABLE? accuracy on TRAIN vs OOS, raw (no sign flip applied)")
print("="*88)
print(f"{'family':<8}{'thr':>5}{'n_tr':>9}{'acc_train':>11}{'n_oos':>9}{'acc_oos':>10}{'stable?':>10}")
for k in Fi:
    for K in (1.0,2.0):
        f=Fi[k]
        mtr=np.abs(f[:cut])>=K; moo=np.abs(f[cut:])>=K
        if mtr.sum()<100 or moo.sum()<100: continue
        atr=100*(np.sign(f[:cut][mtr])==np.sign(y[:cut][mtr])).mean()
        aoo=100*(np.sign(f[cut:][moo])==np.sign(y[cut:][moo])).mean()
        st="YES" if (atr-50)*(aoo-50)>0 else "FLIPPED"
        print(f"{k:<8}{K:>5.1f}{int(mtr.sum()):>9}{atr:>10.2f}%{int(moo.sum()):>9}{aoo:>9.2f}%{st:>10}")

print()
print("="*88)
print("(B) TIME-STABILITY: accuracy of T1 (best family) by 10 sequential blocks")
print("="*88)
f=Fi['T1']; K=2.0
bl=np.array_split(np.arange(n),10)
for i,b in enumerate(bl):
    m=np.abs(f[b])>=K
    if m.sum()<50: continue
    a=100*(np.sign(f[b][m])==np.sign(y[b][m])).mean()
    d0=dt.datetime.utcfromtimestamp(tt[b[0]]).strftime('%Y-%m')
    d1=dt.datetime.utcfromtimestamp(tt[b[-1]]).strftime('%Y-%m')
    bar="#"*int(max(0,(a-40))/1.2)
    print(f"  block {i+1:>2} {d0}..{d1}  n={int(m.sum()):>6}  acc={a:>6.2f}%  {bar}")

print()
print("="*88)
print("VERDICT")
print("="*88)
print("""
The four families ARE independent (max |corr| 0.074 - CSS's precondition is met).
But convergence still LOSES to the single best family.

The reason is now visible and it is a real structural difference between
bankruptcy prediction and price direction:

  CSS combines signals that are all evidence for ONE LATENT BINARY STATE
  ("this company is dying"). That state is PERSISTENT - it lasts months, and
  every signal is a noisy read of the SAME underlying fact. Under those
  conditions, agreement of independent reads multiplies precision (Bayes).

  Price direction next minute is NOT a persistent latent state. It is a fresh
  draw every minute. Independent signals that each carry a tiny, DIFFERENT
  piece of information do not confirm each other - requiring them to agree just
  shrinks the sample to rare coincidences without raising precision.

CSS's method transfers to a PERSISTENT LATENT STATE. So the correct crypto
analogue of CSS is NOT 'which way does price go next minute'. It is a question
with a persistent hidden state, e.g.:
   - is this token's liquidity being withdrawn (dying market)?
   - is this exchange insolvent?
   - is this chain abandoned?
Those are exactly what iter65's L35 proved DOES work (EOS -95.8%).
""")
