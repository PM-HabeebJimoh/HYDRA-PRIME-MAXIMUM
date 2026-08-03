"""
iter67: build FULL OHLC + microstructure panels from the real Binance tick tape.
Existing min_*.npy only had close/OFI/volume. For candle-direction and OHLC-range
prediction I need true O,H,L,C plus the tape-derived fields you cannot see on a chart.

Columns produced (17):
 0 ts        minute epoch
 1 open      first trade price
 2 high      max
 3 low       min
 4 close     last
 5 vol       base volume
 6 ntr       trade count
 7 ofi       signed order-flow imbalance (buy-sell)/(buy+sell)  [aggressor flag]
 8 bvol      buy (taker-buy) volume
 9 svol      sell volume
10 vwap      volume weighted average price
11 maxtrade  largest single trade size   (whale print)
12 top10     share of volume in largest 10 trades (concentration)
13 upt       fraction of consecutive ticks that were up
14 rev       number of direction reversals in the minute (choppiness)
15 tfi       time-weighted flow: sum(sign*qty*(t-t0)/60)  (late-minute pressure)
16 spr       high-low range / vwap  (realised spread proxy)
"""
import numpy as np, zipfile, csv, io, glob, sys

def minute_ohlc(path):
    z=zipfile.ZipFile(path); name=z.namelist()[0]
    ts=[];px=[];qty=[];sa=[]
    with z.open(name) as fh:
        rd=csv.reader(io.TextIOWrapper(fh,'utf-8')); next(rd,None)
        for row in rd:
            if len(row)<5: continue
            try:
                ts.append(float(row[1])); px.append(float(row[2])); qty.append(float(row[3]))
            except ValueError: continue
            sa.append(row[4].strip().lower()=='true')
    if len(ts)<10: return None
    ts=np.array(ts); px=np.array(px); qty=np.array(qty); sa=np.array(sa)
    a=np.argsort(ts); ts,px,qty,sa=ts[a],px[a],qty[a],sa[a]
    unit=1000.0 if ts.max()>2e10 else 1.0
    T=ts/unit
    m=np.floor(T/60.0).astype(np.int64)
    # IsBuyerMaker True => the SELLER was the aggressor => sell
    sign=np.where(sa,-1.0,1.0)
    sv=sign*qty
    um,first=np.unique(m,return_index=True)
    if len(um)<5: return None
    grp=np.split(np.arange(len(T)),first[1:])
    out=np.zeros((len(um),17))
    for i,g in enumerate(grp):
        p=px[g]; q=qty[g]; s=sv[g]; tt=T[g]
        tot=q.sum()
        if tot<=0 or len(p)==0: continue
        out[i,0]=um[i]*60.0
        out[i,1]=p[0]; out[i,2]=p.max(); out[i,3]=p.min(); out[i,4]=p[-1]
        out[i,5]=tot; out[i,6]=len(g)
        out[i,7]=s.sum()/tot
        out[i,8]=q[s>0].sum(); out[i,9]=q[s<0].sum()
        out[i,10]=float((p*q).sum()/tot)
        out[i,11]=q.max()
        k=min(10,len(q)); out[i,12]=np.sort(q)[-k:].sum()/tot
        if len(p)>1:
            d=np.sign(np.diff(p))
            nz=d[d!=0]
            out[i,13]=float((d>0).mean())
            out[i,14]=float((np.diff(nz)!=0).sum()) if len(nz)>1 else 0.0
        w=(tt-um[i]*60.0)/60.0
        out[i,15]=float((s*w).sum()/tot)
        out[i,16]=float((p.max()-p.min())/max(out[i,10],1e-12))
    return out[out[:,5]>0]

if __name__=='__main__':
    sym=sys.argv[1]
    files=sorted(glob.glob('/tmp/ticks/cryptocurrency-ticks-data-master/data/%s/*.zip'%sym))
    allb=[]
    for i,f in enumerate(files):
        try:
            b=minute_ohlc(f)
            if b is not None and len(b): allb.append(b)
        except Exception: continue
        if i%150==0: print("  %s %d/%d"%(sym,i,len(files)),flush=True)
    A=np.concatenate(allb,0)
    A=A[np.argsort(A[:,0])]
    _,u=np.unique(A[:,0],return_index=True)
    A=A[np.sort(u)]
    np.save('/tmp/ticks/ohlc_%s.npy'%sym,A)
    print("%s -> %d minutes, %d cols"%(sym,len(A),A.shape[1]))
