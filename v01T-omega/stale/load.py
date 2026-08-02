import numpy as np, glob, os
def load_1m(sym, root='/tmp/v7/fromBitFinex'):
    rows=[]
    for f in sorted(glob.glob(f'{root}/{sym}/*.csv')):
        with open(f) as fh:
            fh.readline()
            for line in fh:
                p=line.strip().split('\t')
                if len(p)<6: continue
                try: rows.append((int(p[0]),float(p[1]),float(p[2]),float(p[3]),float(p[4]),float(p[5])))
                except: pass
    if not rows: return None
    a=np.array(rows,dtype=float)
    a=a[np.argsort(a[:,0])]
    _,idx=np.unique(a[:,0],return_index=True)
    a=a[np.sort(idx)]
    # sanity: drop absurd prints (>20x jump vs median) - real data hygiene
    med=np.median(a[:,2])
    keep=(a[:,2]>med/50)&(a[:,2]<med*50)&(a[:,3]>=a[:,4])
    return a[keep]

def resample(a, minutes):
    """a: MTS,OPEN,CLOSE,HIGH,LOW,VOL -> OHLC bars of `minutes`, gap-aware."""
    ms=minutes*60000
    b=(a[:,0]//ms).astype(np.int64)
    out=[]
    start=0
    for i in range(1,len(a)+1):
        if i==len(a) or b[i]!=b[start]:
            seg=a[start:i]
            out.append((b[start]*ms, seg[0,1], seg[-1,2], seg[:,3].max(), seg[:,4].min(), seg[:,5].sum(), len(seg)))
            start=i
    return np.array(out,dtype=float)
