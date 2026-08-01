"""Direction at 4h is ~zero. Is that fundamental, or wrong horizon?
Order flow impact decays fast - test 5min to 24h. Also test the RAW univariate
relationship (no model): does signed OFI predict signed forward return at all?"""
import numpy as np, math, glob, os
print("RAW UNIVARIATE: corr(OFI at hour h, signed return over next k hours)")
print("%-10s"%"symbol", "".join("%9s"%("+%dh"%k) for k in (1,2,4,8,12,24)))
allc={k:[] for k in (1,2,4,8,12,24)}
for f in sorted(glob.glob('/tmp/ticks/of_*.npy')):
    A=np.load(f); nm=os.path.basename(f)[3:-4]
    t=A[:,0]; c=A[:,15]; ofi=A[:,1]; N=len(A)
    line=[]
    for k in (1,2,4,8,12,24):
        idx=np.arange(0,N-k-1)
        good=(t[idx+k]-t[idx])==3600.0*k
        i2=idx[good]
        if len(i2)<500: line.append(np.nan); continue
        fwd=np.log(np.maximum(c[i2+k],1e-12)/np.maximum(c[i2],1e-12))
        o=ofi[i2]
        m=np.isfinite(fwd)&np.isfinite(o)
        cc=np.corrcoef(o[m],fwd[m])[0,1]
        line.append(cc); allc[k].append(cc)
    print("%-10s"%nm, "".join("%+9.4f"%x for x in line))
print("%-10s"%"MEAN", "".join("%+9.4f"%np.mean(allc[k]) for k in (1,2,4,8,12,24)))
print()
print("CONTEMPORANEOUS check: corr(OFI at h, return DURING h) - should be strongly +")
cs=[]
for f in sorted(glob.glob('/tmp/ticks/of_*.npy')):
    A=np.load(f); c=A[:,15]; ofi=A[:,1]; N=len(A)
    r=np.zeros(N); r[1:]=np.log(np.maximum(c[1:],1e-12)/np.maximum(c[:-1],1e-12))
    m=np.isfinite(r)&np.isfinite(ofi)
    cs.append(np.corrcoef(ofi[m],r[m])[0,1])
print("  mean contemporaneous corr = %+.4f"%np.mean(cs))
print()
print("=> if contemporaneous is strong but forward is ~0, flow moves price INSTANTLY.")
print("   The information is already IN the price by the time the hour closes.")
