"""
iter67e: WHERE DOES 85% ACTUALLY LIVE?

Facts established this iteration on real data:
  * close-to-close signals look strong but are BID-ASK BOUNCE (NEO 59.28% -> 44.83%)
  * tradable (open->close) 1-minute direction tops out ~56% OOS
  * NEO's signs INVERT out-of-sample -> regime instability

So 85% is NOT available on next-1-minute direction. Where is it available?
Test the two axes that actually move accuracy:
   (1) HORIZON  - accuracy rises with horizon as noise averages out
   (2) SELECTIVITY - accuracy rises as you take fewer, more extreme signals
Map the full surface and find every cell that reaches 85%.

Also test the EASIER, MORE USEFUL target the user offered: "OHLC RANGES".
Predicting whether the next candle's RANGE is large/small is far more
predictable than its direction - volatility is persistent, direction is not.
"""
import numpy as np, os
def roll(x,k):
    o=np.full(len(x),np.nan); v=np.nan_to_num(x)
    cs=np.cumsum(np.insert(v,0,0.0)); o[k-1:]=(cs[k:]-cs[:-k])/k; return o
def rstd(x,k):
    v=np.nan_to_num(x); o=np.full(len(x),np.nan)
    cs=np.cumsum(np.insert(v,0,0.0)); c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(cs[k:]-cs[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0)); return o
def z(x,k): return (x-roll(x,k))/np.maximum(rstd(x,k),1e-12)

sym='BTCUSDT'
A=np.load('/tmp/ticks/ohlc_%s.npy'%sym)
ts=A[:,0].astype(np.int64)
o,h,l,c,vol,ntr=A[:,1],A[:,2],A[:,3],A[:,4],A[:,5],A[:,6]
vwap,spr=A[:,10],A[:,16]
lc=np.log(np.maximum(c,1e-12)); lo=np.log(np.maximum(o,1e-12))
n=len(c); cut=int(n*0.6)

print("="*92)
print("AXIS 1: DIRECTION accuracy vs HORIZON and SELECTIVITY (BTCUSDT, tradable, OOS)")
print("="*92)
sig=-z((c-o)/np.maximum(vwap,1e-12),240)     # sign learned earlier
print(f"{'horizon':>8}"+"".join(f"{'top'+str(p)+'%':>10}" for p in (100,10,2,1,0.5,0.1)))
for H in (1,5,15,60,240):
    # tradable: enter next open, exit close H bars later
    yy=np.full(n,np.nan)
    if H==1: yy[:-1]=lc[1:]-lo[1:]
    else:
        yy[:-H]=lc[H-1+1:len(lc)-0][:n-H] if False else np.nan
        idx=np.arange(n-H-1)
        yy[idx]=lc[idx+H]-lo[idx+1]
    contig=np.zeros(n,bool)
    contig[:n-H-1]=(ts[H+1:n]-ts[1:n-H]==60*H)
    m0=contig&np.isfinite(yy)&np.isfinite(sig)
    m0[:cut]=False
    row=f"{H:>8}"
    av=np.abs(sig)
    for p in (100,10,2,1,0.5,0.1):
        if m0.sum()<200: row+=f"{'--':>10}"; continue
        thr=np.quantile(av[m0],1-p/100.0)
        mm=m0&(av>=thr)
        if mm.sum()<50: row+=f"{'--':>10}"; continue
        acc=100*(np.sign(sig[mm])==np.sign(yy[mm])).mean()
        row+=f"{acc:>9.2f}%"
    print(row)

print()
print("="*92)
print("AXIS 2: RANGE / VOLATILITY prediction - the target that IS predictable")
print("="*92)
rng=(h-l)/np.maximum(vwap,1e-12)
lr=np.log(np.maximum(rng,1e-12))
nxt=np.full(n,np.nan); nxt[:-1]=lr[1:]
contig=np.zeros(n,bool); contig[:-1]=(ts[1:]-ts[:-1]==60)
# predictor: trailing range + activity
pred=0.5*z(lr,60)+0.3*z(np.log(np.maximum(vol,1e-9)),60)+0.2*z(np.log(np.maximum(ntr,1)),60)
m=contig&np.isfinite(nxt)&np.isfinite(pred); m[:cut]=False
med=np.nanmedian(lr[:cut])
lab=(nxt>med)          # is next range ABOVE median?
print(f"n OOS = {int(m.sum()):,}")
print(f"{'rule':<34}{'n':>9}{'accuracy':>11}")
acc=100*((pred[m]>0)==lab[m]).mean()
print(f"{'pred>0 -> range above median':<34}{int(m.sum()):>9}{acc:>10.2f}%")
av=np.abs(pred)
for p in (10,5,2,1):
    thr=np.quantile(av[m],1-p/100.0)
    mm=m&(av>=thr)
    if mm.sum()<50: continue
    a=100*((pred[mm]>0)==lab[mm]).mean()
    print(f"{'top %.0f%% most extreme'%p:<34}{int(mm.sum()):>9}{a:>10.2f}%")
print()
print("Also: can we predict the RANGE MAGNITUDE (regression)?")
mm=m&np.isfinite(pred)
cc=np.corrcoef(pred[mm],nxt[mm])[0,1]
print(f"  corr(prediction, next log-range) = {cc:+.4f}   R^2 = {cc*cc*100:.2f}%")
