"""
iter66: CSS v10.0 METHOD applied to DIRECTION.

Not one model with 15 price-derived features (that was my error - 15 ways of
measuring ONE thing). Instead: 4 INDEPENDENT signal families, each scored
separately, firing only on CONVERGENCE - exactly how CSS gets 92% precision
from individually-weak signals.

DATA (all real, no synthetic):
  /tmp/ticks/min_*.npy  built by crossflow/sync.py from the real Binance tick
  tape (Nucs/cryptocurrency-ticks-data) - columns: [ts, close, ofi, volume, ntrades?]
  Bitfinex 1m from Vitaly007 repo.

THE CSS DISCIPLINE:
  - each family from a DIFFERENT origin (venue / flow / other asset / absence)
  - score each separately, report its OWN precision
  - require >= K families to agree
  - persistence check
  - report whether convergence precision > best single family  <-- THE TEST
"""
import numpy as np, sys, datetime as dt
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/inversion')
from load import load_1m

def roll(x,k):
    o=np.full(len(x),np.nan); v=np.nan_to_num(x)
    c=np.cumsum(np.insert(v,0,0.0)); o[k-1:]=(c[k:]-c[:-k])/k
    return o
def rollstd(x,k):
    v=np.nan_to_num(x); o=np.full(len(x),np.nan)
    c=np.cumsum(np.insert(v,0,0.0)); c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(c[k:]-c[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0)); return o
def z(x,k):
    return (x-roll(x,k))/np.maximum(rollstd(x,k),1e-12)

print("Loading real 1m panels...")
B=np.load('/tmp/ticks/min_LTCBTC.npy')      # Binance LTC/BTC 1m w/ signed OFI
BTC=np.load('/tmp/ticks/min_BTCUSDT.npy')   # BTC hub
bfx=load_1m('LTC')
if bfx is None: print("no bitfinex"); sys.exit()
bt=(bfx[:,0]/1000).astype(np.int64); bc=bfx[:,2]
nt=B[:,0].astype(np.int64)
common,ia,ib=np.intersect1d(bt,nt,return_indices=True)
print(f"synced minutes: {len(common):,}")

pb=bc[ia]                 # bitfinex price (the thing we predict)
pn=B[ib,1]                # binance price
ofi=B[ib,2]               # signed order flow imbalance
vol=B[ib,3]               # volume
_,ic,ig=np.intersect1d(common,BTC[:,0].astype(np.int64),return_indices=True)
btc_r=np.zeros(len(common)); btc_o=np.zeros(len(common))
bp=BTC[ig,1]; br=np.zeros(len(bp)); br[1:]=np.log(np.maximum(bp[1:],1e-12)/np.maximum(bp[:-1],1e-12))
btc_r[ic]=br; btc_o[ic]=BTC[ig,2]

rb=np.zeros(len(pb)); rb[1:]=np.log(np.maximum(pb[1:],1e-12)/np.maximum(pb[:-1],1e-12))
disloc=np.log(np.maximum(pn,1e-12))-np.log(np.maximum(pb,1e-12))

# ---------------- FOUR INDEPENDENT FAMILIES (CSS Tiers) ----------------
# T1 SOVEREIGN : cross-venue dislocation  (origin: the OTHER exchange)
T1 = z(disloc,60)
# T2 CREDIT    : order-flow imbalance     (origin: traders' aggression, NOT price)
T2 = z(ofi,60)
# T3 OPERATIONAL: BTC hub lead            (origin: a DIFFERENT asset)
T3 = z(btc_o,60)
# T4 ABSENCE   : liquidity withdrawal     (origin: MAKERS LEAVING - the CSS innovation)
#   mandatory flow = volume. Its ABSENCE = z-score of log volume, negative.
lv=np.log(np.maximum(vol,1e-9))
T4 = -z(lv,60)             # high value = volume ABSENT

# target: next-minute Bitfinex return, normalised
sig30=rollstd(rb,30)
idx=np.arange(70,len(common)-2)
g=(common[idx+1]-common[idx]==60)&(common[idx]-common[idx-1]==60)
idx=idx[g]
y=rb[idx+1]
ok=np.isfinite(y)&np.isfinite(T1[idx])&np.isfinite(T2[idx])&np.isfinite(T3[idx])&np.isfinite(T4[idx])&np.isfinite(sig30[idx])&(sig30[idx]>0)
idx=idx[ok]; y=rb[idx+1]
t1,t2,t3,t4=T1[idx],T2[idx],T3[idx],T4[idx]
tt=common[idx]
print(f"usable samples: {len(idx):,}")

# split: first 60% train (to pick thresholds), last 40% OOS
n=len(idx); cut=int(n*0.6)
def prec(mask,yy):
    if mask.sum()<30: return np.nan,0
    s=np.sign(yy[mask]); pos=(s>0).mean()
    return max(pos,1-pos)*100, int(mask.sum())

print()
print("="*84)
print("STEP 1: PRECISION OF EACH FAMILY ALONE (out-of-sample, last 40%)")
print("="*84)
yo=y[cut:]
fams={'T1 cross-venue':t1[cut:],'T2 order-flow':t2[cut:],'T3 BTC-hub':t3[cut:],'T4 ABSENCE':t4[cut:]}
K=2.0
print(f"{'family':<18}{'n fired':>9}{'directional acc':>18}")
single={}
for nm,f in fams.items():
    m=np.abs(f)>=K
    # directional prediction: sign of the family score
    if m.sum()>30:
        acc=100*(np.sign(f[m])==np.sign(yo[m])).mean()
    else: acc=np.nan
    single[nm]=acc
    print(f"{nm:<18}{int(m.sum()):>9}{acc:>17.2f}%")

print()
print("="*84)
print("STEP 2: CONVERGENCE (the CSS rule) - require K families to AGREE on direction")
print("="*84)
# each family votes: +1/-1 if |z|>=thr else 0.  Direction convention learned on TRAIN.
def votes(arr,thr,sign):
    v=np.zeros(len(arr))
    v[arr>=thr]= sign
    v[arr<=-thr]=-sign
    return v

# learn each family's directional SIGN on the TRAIN half only (no lookahead)
ytr=y[:cut]
signs={}
for nm,f in (('T1',t1),('T2',t2),('T3',t3),('T4',t4)):
    ftr=f[:cut]; m=np.abs(ftr)>=K
    if m.sum()<50: signs[nm]=1; continue
    agree=(np.sign(ftr[m])==np.sign(ytr[m])).mean()
    signs[nm]= 1 if agree>=0.5 else -1
print("learned signs (train only):",signs)

V = (votes(t1[cut:],K,signs['T1']) + votes(t2[cut:],K,signs['T2'])
   + votes(t3[cut:],K,signs['T3']) + votes(t4[cut:],K,signs['T4']))
NACT = ((np.abs(t1[cut:])>=K).astype(int)+(np.abs(t2[cut:])>=K).astype(int)
      + (np.abs(t3[cut:])>=K).astype(int)+(np.abs(t4[cut:])>=K).astype(int))

print()
print(f"{'rule':<34}{'n fired':>9}{'ACCURACY':>12}{'mean bp':>11}")
best_single=max([v for v in single.values() if np.isfinite(v)])
for need in (1,2,3,4):
    m=(np.abs(V)>=need)&(NACT>=need)
    if m.sum()<20:
        print(f"{'>= '+str(need)+' families agree':<34}{int(m.sum()):>9}{'--':>12}")
        continue
    acc=100*(np.sign(V[m])==np.sign(yo[m])).mean()
    bp=1e4*(np.sign(V[m])*yo[m]).mean()
    print(f"{'>= '+str(need)+' families agree':<34}{int(m.sum()):>9}{acc:>11.2f}%{bp:>+10.3f}")

print()
print("="*84)
print("STEP 3: THE CSS CLAIM - does convergence beat the best single family?")
print("="*84)
print(f"best single family OOS accuracy : {best_single:.2f}%")
m3=(np.abs(V)>=3)&(NACT>=3)
if m3.sum()>=20:
    a3=100*(np.sign(V[m3])==np.sign(yo[m3])).mean()
    print(f"3+ family convergence accuracy  : {a3:.2f}%   (n={int(m3.sum())})")
    print(f"LIFT FROM CONVERGENCE           : {a3-best_single:+.2f} points")
    print()
    if a3>best_single+1:
        print(">>> CSS METHOD TRANSFERS: convergence beats any single signal.")
    else:
        print(">>> NO LIFT: the families are NOT independent enough on this data.")
