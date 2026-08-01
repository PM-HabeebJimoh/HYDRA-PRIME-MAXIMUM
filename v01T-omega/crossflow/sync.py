"""CROSS-ASSET FLOW: BTC's tape as the CAUSE of an alt's chart move.

Prior iterations asked "does THIS asset's flow predict THIS asset's price?"
Answer: no, flow IS the move (contemporaneous +0.2263, forward ~0).

The right question is DIFFERENT: does BTC's aggressive order flow predict
the ALT's price BEFORE the alt's own chart reacts? BTC is the causal hub of
crypto. Information arrives in BTC first and propagates outward. That is a
genuine upstream signal - it happens before the alt's candle exists.

Build 1-MINUTE synchronised panel across all 7 symbols with signed flow.
"""
import numpy as np, zipfile, csv, io, glob, os, sys
SYMS=['BTCUSDT','BNBUSDT','NEOUSDT','QTUMUSDT','ETHBTC','LTCBTC','BCCUSDT']
def load_day(path):
    z=zipfile.ZipFile(path); name=z.namelist()[0]
    ts=[];px=[];qty=[];sa=[]
    with z.open(name) as fh:
        rd=csv.reader(io.TextIOWrapper(fh,'utf-8')); next(rd,None)
        for row in rd:
            if len(row)<5: continue
            try: ts.append(float(row[1]));px.append(float(row[2]));qty.append(float(row[3]))
            except ValueError: continue
            sa.append(row[4].strip().lower()=='true')
    if not ts: return None
    a=np.argsort(np.array(ts))
    return np.array(ts)[a],np.array(px)[a],np.array(qty)[a],np.array(sa)[a]

def minute_bars(path):
    d=load_day(path)
    if d is None: return None
    ts,px,qty,sa=d
    unit=1000.0 if ts.max()>2e10 else 1.0
    T=ts/unit
    m=np.floor(T/60.0).astype(np.int64)
    sign=np.where(sa,-1.0,1.0); sv=sign*qty
    um,first=np.unique(m,return_index=True)
    if len(um)<10: return None
    grp=np.split(np.arange(len(T)),first[1:])
    out=np.zeros((len(um),6))
    for i,g in enumerate(grp):
        q=qty[g].sum()
        out[i,0]=um[i]*60.0
        out[i,1]=px[g][-1]                    # close
        out[i,2]=sv[g].sum()/max(q,1e-12)     # OFI
        out[i,3]=q                            # volume
        out[i,4]=len(g)                       # trade count
        out[i,5]=abs(sv[g]).sum()/max(q,1e-12)
    return out

if __name__=='__main__':
    sym=sys.argv[1]
    files=sorted(glob.glob('/tmp/ticks/cryptocurrency-ticks-data-master/data/%s/*.zip'%sym))
    allb=[]
    for i,f in enumerate(files):
        try:
            b=minute_bars(f)
            if b is not None: allb.append(b)
        except Exception: continue
        if i%150==0: print("  %s %d/%d"%(sym,i,len(files)),flush=True)
    if allb:
        A=np.concatenate(allb,0); A=A[np.argsort(A[:,0])]
        _,u=np.unique(A[:,0],return_index=True); A=A[np.sort(u)]
        np.save('/tmp/ticks/min_%s.npy'%sym,A)
        print("%s -> %d minutes"%(sym,len(A)))
