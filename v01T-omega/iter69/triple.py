"""
iter69: CORRECTED SYSTEM - triple barrier, tradable by construction.

Every previous formula predicted sign(close[i+1]-open[i+1]): a 1-minute move of
~1.09bp against a 1.649bp spread. Unprofitable even with a perfect oracle.

CORRECTED:
  entry   : NEXT bar's OPEN (never the signal bar's close)
  target  : +a*sigma      stop: -b*sigma     sigma = trailing causal volatility
  resolve : walk forward through HIGH/LOW of subsequent bars
  tie     : if a bar touches both -> assume STOP (pessimistic)
  timeout : N bars -> exit at close
  costs   : charged both sides
  abstain : trade only the extreme tail of the signal

CRITICAL HONESTY CONTROL:
  For a driftless walk, P(target first) = b/(a+b). An 85% WR at a=0.5,b=3 is
  FREE (85.7%) and has ZERO expectancy. So the only meaningful metric is
      EDGE = P_observed - b/(a+b)
  and net R per trade after costs. Raw WR alone is reported but never as a claim.
"""
import numpy as np, os, sys

def roll(x,k):
    o=np.full(len(x),np.nan); v=np.nan_to_num(x)
    cs=np.cumsum(np.insert(v,0,0.0)); o[k-1:]=(cs[k:]-cs[:-k])/k; return o
def rstd(x,k):
    v=np.nan_to_num(x); o=np.full(len(x),np.nan)
    cs=np.cumsum(np.insert(v,0,0.0)); c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(cs[k:]-cs[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0)); return o
def z(x,k): return (x-roll(x,k))/np.maximum(rstd(x,k),1e-12)

def resolve(o,h,l,c,ts,i,side,tgt,stp,N):
    """Walk forward from bar i (entry at o[i]). Returns R multiple, bars held.
       Pessimistic: stop checked first when both touched in the same bar."""
    e=o[i]
    if e<=0: return None
    up=e*(1+tgt) if side>0 else e*(1+stp)
    dn=e*(1-stp) if side>0 else e*(1-tgt)
    for k in range(i,min(i+N,len(c))):
        if k>i and ts[k]-ts[k-1]!=60: break        # gap -> abandon
        if side>0:
            if l[k]<=dn: return -1.0,k-i+1
            if h[k]>=up: return  tgt/stp,k-i+1
        else:
            if h[k]>=up: return -1.0,k-i+1
            if l[k]<=dn: return  tgt/stp,k-i+1
    k=min(i+N-1,len(c)-1)
    r=(c[k]/e-1)*side/stp
    return r,k-i+1

def run(sym, A_TGT, B_STP, N, cost_bp, topfrac):
    A=np.load('/tmp/ticks/ohlc_%s.npy'%sym)
    ts=A[:,0].astype(np.int64)
    o,h,l,c=A[:,1],A[:,2],A[:,3],A[:,4]
    vol,ntr,ofi=A[:,5],A[:,6],A[:,7]
    vwap,maxtr,top10=A[:,10],A[:,11],A[:,12]
    upt,rev,tfi,spr=A[:,13],A[:,14],A[:,15],A[:,16]
    n=len(c)
    lc=np.log(np.maximum(c,1e-12))
    ret=np.zeros(n); ret[1:]=np.diff(lc)
    sig=rstd(ret,60)                                  # causal vol
    # ---- signal: independent families, all causal, all from the TAPE ----
    f_ofi   = z(ofi,240)
    f_tfi   = z(tfi,240)
    f_whale = z(maxtr/np.maximum(vol,1e-12),240)
    f_conc  = z(top10,240)
    f_act   = z(np.log(np.maximum(ntr,1)),240)
    S = f_ofi + f_tfi                                  # directional pressure
    GATE = (np.abs(f_ofi)>0)&np.isfinite(S)
    cut=int(n*0.6)
    av=np.abs(S)
    thr=np.nanquantile(av[:cut],1-topfrac)             # threshold FROZEN on train
    base=b_over=None
    out=[]
    for i in range(300,n-N-2):
        if not np.isfinite(S[i]) or av[i]<thr: continue
        if not np.isfinite(sig[i]) or sig[i]<=0: continue
        if ts[i+1]-ts[i]!=60: continue
        side=int(np.sign(S[i]))
        if side==0: continue
        tgt=A_TGT*sig[i]; stp=B_STP*sig[i]
        if tgt<=0 or stp<=0: continue
        r=resolve(o,h,l,c,ts,i+1,side,tgt,stp,N)
        if r is None: continue
        R,bars=r
        # costs in R units: round trip bp / (stop distance in bp)
        cR=(cost_bp*1e-4)/stp
        out.append((i,R,R-cR,bars,i>=cut))
    return np.array(out,dtype=float) if out else None

if __name__=='__main__':
    print("="*104)
    print("CORRECTED SYSTEM: TRIPLE BARRIER (entry next OPEN, path-resolved, pessimistic ties)")
    print("="*104)
    COST={'BTCUSDT':5.65,'LTCBTC':5.15,'NEOUSDT':16.80,'ETHBTC':5.0,'BNBUSDT':6.0}
    for sym in ('BTCUSDT','LTCBTC','NEOUSDT'):
        if not os.path.exists('/tmp/ticks/ohlc_%s.npy'%sym): continue
        print()
        print(f"##### {sym} #####")
        print(f"{'a(tgt)':>7}{'b(stop)':>8}{'N':>5}{'n_oos':>8}{'WR%':>8}{'baseline':>10}{'EDGE':>8}{'netR':>9}{'tot R':>9}")
        for (a,b) in ((1.0,1.0),(0.5,1.5),(0.5,3.0),(1.0,2.0),(2.0,1.0),(1.5,0.75)):
            for N in (30,120):
                res=run(sym,a,b,N,COST[sym],0.02)
                if res is None or len(res)<50: continue
                oos=res[res[:,4]==1]
                if len(oos)<50: continue
                wr=100*(oos[:,1]>0).mean()
                basew=100*b/(a+b)
                edge=wr-basew
                netR=oos[:,2].mean()
                print(f"{a:>7.2f}{b:>8.2f}{N:>5}{len(oos):>8}{wr:>7.2f}%{basew:>9.2f}%{edge:>+7.2f}{netR:>+9.4f}{oos[:,2].sum():>+9.1f}")
