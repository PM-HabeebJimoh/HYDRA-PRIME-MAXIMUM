"""ORDER-FLOW FEATURES — the layer BENEATH the candle.

A candle is a lossy summary: it keeps O/H/L/C/V and throws away WHO traded,
in what SIZE, in what SEQUENCE, and with what URGENCY. That discarded
information is causally UPSTREAM of the price move it later produces.

For each hour we reconstruct, from raw executions:

  ORDER FLOW IMBALANCE  signed volume (aggressor buy +, aggressor sell -)
  TRADE INTENSITY       arrivals/sec, and its acceleration
  SIZE DISTRIBUTION     mean/max clip, large-trade share  -> institutional footprint
  KYLE'S LAMBDA         price impact per unit signed flow -> liquidity depth
  VPIN                  volume-synchronised prob. of informed trading (toxicity)
  EFFECTIVE SPREAD      measured from real ask-prints vs bid-prints
  TICK RUNS             consecutive same-aggressor streaks -> sweeping/iceberg
  QUOTE PRESSURE        share of volume at best-price match
  TRADE AUTOCORR        persistence of signed flow -> order splitting

These are what a market maker sees BEFORE the candle prints.
Strictly causal: hour h features -> predict hour h+1..h+4 outcome.
"""
import numpy as np, zipfile, csv, io, os, glob, sys

def load_day(path):
    z=zipfile.ZipFile(path); name=z.namelist()[0]
    ts=[];px=[];qty=[];sa=[];bp=[]
    with z.open(name) as fh:
        rd=csv.reader(io.TextIOWrapper(fh,'utf-8'))
        hdr=next(rd,None)
        for row in rd:
            if len(row)<5: continue
            try:
                ts.append(float(row[1])); px.append(float(row[2])); qty.append(float(row[3]))
            except ValueError: continue
            sa.append(row[4].strip().lower()=='true')
            bp.append(row[7].strip().lower()=='true' if len(row)>7 else False)
    if not ts: return None
    a=np.argsort(np.array(ts))
    return (np.array(ts)[a],np.array(px)[a],np.array(qty)[a],
            np.array(sa)[a],np.array(bp)[a])

def hour_features(ts,px,qty,sa,bp):
    """Aggregate raw ticks into hourly microstructure features."""
    if len(ts)<50: return None
    t0=ts[0]
    # ts may be seconds or ms
    unit = 1000.0 if ts.max()>2e10 else 1.0
    hr=np.floor(ts/(3600.0*unit)).astype(np.int64)
    out={}
    sign=np.where(sa,-1.0,1.0)           # buyer aggressor=+1, seller aggressor=-1
    sv=sign*qty
    uh=np.unique(hr)
    rows=[]
    for h in uh:
        m=hr==h
        if m.sum()<30: continue
        P=px[m]; Q=qty[m]; S=sign[m]; SV=sv[m]; T=ts[m]/unit; B=bp[m]
        vol=Q.sum()
        if vol<=0: continue
        ofi=SV.sum()/vol                                   # order flow imbalance
        n=len(P)
        dur=max(T[-1]-T[0],1.0)
        intensity=n/dur                                    # trades per second
        # size distribution
        mean_clip=Q.mean(); max_clip=Q.max()
        big=Q>=np.quantile(Q,0.99)
        big_share=Q[big].sum()/vol
        big_ofi=(S[big]*Q[big]).sum()/max(Q[big].sum(),1e-9)  # are whales buying?
        # Kyle's lambda: regress price change on signed volume, in sub-buckets
        k=max(10,n//20)
        idx=np.arange(0,n,k)
        dp=[];dv=[]
        for i in range(len(idx)-1):
            s0,s1=idx[i],idx[i+1]
            dp.append((P[s1-1]-P[s0])/max(P[s0],1e-12))
            dv.append(SV[s0:s1].sum())
        lam=np.nan
        if len(dp)>4:
            dp=np.array(dp);dv=np.array(dv)
            if dv.std()>0: lam=np.polyfit(dv,dp,1)[0]*1e6
        # VPIN-style toxicity: |imbalance| over volume buckets
        nb=10; bs=vol/nb
        cum=np.cumsum(Q); edges=np.searchsorted(cum,np.arange(1,nb)*bs)
        parts=np.split(np.arange(n),edges)
        vp=[]
        for p_ in parts:
            if len(p_)<2: continue
            vp.append(abs((S[p_]*Q[p_]).sum())/max(Q[p_].sum(),1e-9))
        vpin=np.mean(vp) if vp else np.nan
        # effective spread from real prints
        pb=P[S>0]; ps=P[S<0]
        espread=np.nan
        if len(pb)>5 and len(ps)>5:
            mid=0.5*(pb.mean()+ps.mean())
            espread=(pb.mean()-ps.mean())/mid*1e4
        # aggressor runs
        ch=np.diff(S)!=0
        runs=(ch.sum()+1)/n                                 # low => long sweeps
        # signed-flow autocorrelation (order splitting)
        ac=np.nan
        if n>20 and S.std()>0: ac=np.corrcoef(S[:-1],S[1:])[0,1]
        bestshare=B.mean() if len(B)==n else np.nan
        rows.append((h*3600.0,ofi,intensity,mean_clip,max_clip/max(mean_clip,1e-9),
                     big_share,big_ofi,lam,vpin,espread,runs,ac,bestshare,vol,n,P[-1]))
    return np.array(rows) if rows else None

if __name__=='__main__':
    sym=sys.argv[1]
    base='/tmp/ticks/cryptocurrency-ticks-data-master/data/%s'%sym
    files=sorted(glob.glob(base+'/*.zip'))
    allr=[]
    for i,f in enumerate(files):
        try:
            d=load_day(f)
            if d is None: continue
            r=hour_features(*d)
            if r is not None: allr.append(r)
        except Exception as e:
            continue
        if i%100==0: print("  %s %d/%d"%(sym,i,len(files)),flush=True)
    if allr:
        A=np.concatenate(allr,0)
        A=A[np.argsort(A[:,0])]
        np.save('/tmp/ticks/of_%s.npy'%sym,A)
        print("%s -> %d hours"%(sym,len(A)))
