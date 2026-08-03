"""
iter69b: Two diagnostics from the first run.

1) THE 85% ILLUSION IS NOW PROVEN NUMERICALLY.
   a=0.5, b=3.0 gives WR 82.76% - close to the "85%" target - while the FREE
   baseline b/(a+b) is 85.71%. So that WR is BELOW random and loses -0.34R per
   trade. Any 85% claim without the barrier ratio is meaningless. Confirmed.

2) EDGE is NEGATIVE for the pressure signal (ofi+tfi) and POSITIVE (+1.74) when
   the barrier is inverted (a=2,b=1). That is the signature of a FLIPPED SIGN:
   at 1-minute horizon, aggressive flow MEAN-REVERTS rather than continues.
   Test that directly, learning the sign on TRAIN only.
"""
import numpy as np, os
exec(open('/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/iter69/triple.py').read().split("if __name__")[0])

def run2(sym,A_TGT,B_STP,N,cost_bp,topfrac,flip):
    A=np.load('/tmp/ticks/ohlc_%s.npy'%sym)
    ts=A[:,0].astype(np.int64)
    o,h,l,c=A[:,1],A[:,2],A[:,3],A[:,4]
    vol,ntr,ofi=A[:,5],A[:,6],A[:,7]
    maxtr,tfi=A[:,11],A[:,15]
    n=len(c); lc=np.log(np.maximum(c,1e-12))
    ret=np.zeros(n); ret[1:]=np.diff(lc); sig=rstd(ret,60)
    S=(z(ofi,240)+z(tfi,240))*flip
    cut=int(n*0.6); av=np.abs(S)
    thr=np.nanquantile(av[:cut],1-topfrac)
    rows=[]
    for i in range(300,n-N-2):
        if not np.isfinite(S[i]) or av[i]<thr: continue
        if not np.isfinite(sig[i]) or sig[i]<=0: continue
        if ts[i+1]-ts[i]!=60: continue
        side=int(np.sign(S[i]))
        if side==0: continue
        tgt=A_TGT*sig[i]; stp=B_STP*sig[i]
        r=resolve(o,h,l,c,ts,i+1,side,tgt,stp,N)
        if r is None: continue
        R,bars=r
        rows.append((R,R-(cost_bp*1e-4)/stp,i>=cut))
    return np.array(rows) if rows else None

COST={'BTCUSDT':5.65,'LTCBTC':5.15,'NEOUSDT':16.80}
print("="*96)
print("SIGN TEST: does 1-minute aggressive flow CONTINUE (+1) or MEAN-REVERT (-1)?")
print("="*96)
print(f"{'sym':<9}{'flip':>5}{'a':>5}{'b':>5}{'n_oos':>8}{'WR%':>8}{'base':>8}{'EDGE':>8}{'netR':>9}")
for sym in ('BTCUSDT',):
    if not os.path.exists('/tmp/ticks/ohlc_%s.npy'%sym): continue
    for flip in (1,-1):
        for (a,b) in ((1.0,1.0),(2.0,1.0),(3.0,1.0)):
            r=run2(sym,a,b,60,COST[sym],0.02,flip)
            if r is None: continue
            oos=r[r[:,2]==1]
            if len(oos)<50: continue
            wr=100*(oos[:,0]>0).mean(); bw=100*b/(a+b)
            print(f"{sym:<9}{flip:>5}{a:>5.1f}{b:>5.1f}{len(oos):>8}{wr:>7.2f}%{bw:>7.2f}%{wr-bw:>+7.2f}{oos[:,1].mean():>+9.4f}")
