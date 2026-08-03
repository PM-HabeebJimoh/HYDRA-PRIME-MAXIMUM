"""
iter69d: THE CORRECTED, TRADABLE SYSTEM.

Design constraints now derived from data, not guessed:
  * cost 5.65bp = 0.92x the 1-min sigma -> 1-min barriers are unviable
  * need stop >= 10*sigma(1m) ~ 61bp so cost is <10% of R
  * that implies a HORIZON of hours, not one candle

So: barriers in absolute bp (not 1-min sigma), horizon up to 1440 bars,
entry next OPEN, path-resolved, pessimistic ties, costs charged,
threshold frozen on TRAIN, edge measured against b/(a+b).
"""
import numpy as np, os
exec(open('/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/iter69/triple.py').read().split("def resolve")[0])

def resolve_bp(o,h,l,c,ts,i,side,tgt_bp,stp_bp,N):
    e=o[i]
    if e<=0: return None
    up=e*(1+tgt_bp*1e-4) if side>0 else e*(1+stp_bp*1e-4)
    dn=e*(1-stp_bp*1e-4) if side>0 else e*(1-tgt_bp*1e-4)
    for k in range(i,min(i+N,len(c))):
        if k>i and ts[k]-ts[k-1]!=60: break
        if side>0:
            if l[k]<=dn: return -1.0,k-i+1
            if h[k]>=up: return tgt_bp/stp_bp,k-i+1
        else:
            if h[k]>=up: return -1.0,k-i+1
            if l[k]<=dn: return tgt_bp/stp_bp,k-i+1
    k=min(i+N-1,len(c)-1)
    return (c[k]/e-1)*1e4*side/stp_bp, k-i+1

def run(sym,tgt_bp,stp_bp,N,cost_bp,topfrac):
    A=np.load('/tmp/ticks/ohlc_%s.npy'%sym)
    ts=A[:,0].astype(np.int64)
    o,h,l,c=A[:,1],A[:,2],A[:,3],A[:,4]
    vol,ntr,ofi=A[:,5],A[:,6],A[:,7]
    maxtr,tfi=A[:,11],A[:,15]
    n=len(c)
    S=z(ofi,240)+z(tfi,240)
    cut=int(n*0.6); av=np.abs(S)
    thr=np.nanquantile(av[:cut],1-topfrac)
    rows=[]; last=-10**9
    for i in range(300,n-2):
        if not np.isfinite(S[i]) or av[i]<thr: continue
        if ts[i+1]-ts[i]!=60: continue
        if i<last: continue                      # NO OVERLAP - one position at a time
        side=int(np.sign(S[i]))
        if side==0: continue
        r=resolve_bp(o,h,l,c,ts,i+1,side,tgt_bp,stp_bp,N)
        if r is None: continue
        R,bars=r
        last=i+bars
        rows.append((R,R-(cost_bp)/stp_bp,i>=cut,bars))
    return np.array(rows) if rows else None

COST={'BTCUSDT':5.65,'LTCBTC':5.15,'NEOUSDT':16.80}
print("="*110)
print("CORRECTED TRADABLE SYSTEM | barriers in bp | non-overlapping | entry next OPEN | pessimistic")
print("="*110)
for sym in ('BTCUSDT','LTCBTC'):
    p='/tmp/ticks/ohlc_%s.npy'%sym
    if not os.path.exists(p): continue
    print()
    print(f"##### {sym}  (cost {COST[sym]}bp round trip) #####")
    print(f"{'tgt bp':>8}{'stop bp':>9}{'N':>6}{'n_oos':>7}{'WR%':>8}{'base%':>8}{'EDGE':>7}{'netR':>9}{'totR':>9}{'cost/R':>8}")
    for (t,s) in ((60,60),(120,60),(60,120),(180,60),(60,180),(240,120),(120,240)):
        for N in (240,1440):
            r=run(sym,t,s,N,COST[sym],0.02)
            if r is None: continue
            oos=r[r[:,2]==1]
            if len(oos)<40: continue
            wr=100*(oos[:,0]>0).mean(); bw=100*s/(t+s)
            print(f"{t:>8}{s:>9}{N:>6}{len(oos):>7}{wr:>7.2f}%{bw:>7.2f}%{wr-bw:>+7.2f}"
                  f"{oos[:,1].mean():>+9.4f}{oos[:,1].sum():>+9.1f}{COST[sym]/s:>8.3f}")
