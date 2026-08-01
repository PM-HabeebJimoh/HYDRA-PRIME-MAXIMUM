"""Is +0.200% real, or an artifact of using TRAILING vol as the premium proxy?
KEY SUSPICION: the v01T gate requires HV<0.8 = short-vol BELOW long-vol.
That is MEAN REVERSION IN VOL by construction. If trailing vol is elevated
relative to forward vol simply because the gate selects it, the 'edge' is
tautological. Test by decomposing."""
from load import load_1m, resample
from vrp import bb_hv
import numpy as np
H=4
SYMS=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
rows={'sq_tr':[], 'sq_fw':[], 'ns_tr':[], 'ns_fw':[]}
for nm in SYMS:
    raw=load_1m(nm)
    if raw is None or len(raw)<50000: continue
    f=resample(raw,60); c=f[:,2]
    if len(c)<200: continue
    bb,hv=bb_hv(c); n=len(c)
    i=np.arange(H+20,n-H-1); e0=c[i]
    fwd=np.zeros(len(i))
    for k in range(1,H+1): fwd=np.maximum(fwd,np.abs(c[i+k]-e0)/e0)
    base=c[i-H]; tr=np.zeros(len(i))
    for k in range(H-1,-1,-1): tr=np.maximum(tr,np.abs(c[i-k]-base)/base)
    sq=np.nan_to_num(((bb[i]<10)|(bb[i]>90))&(hv[i]<0.8),nan=False).astype(bool)
    rows['sq_tr'].append(100*tr[sq]); rows['sq_fw'].append(100*fwd[sq])
    rows['ns_tr'].append(100*tr[~sq]); rows['ns_fw'].append(100*fwd[~sq])
R={k:np.concatenate(v) for k,v in rows.items()}
print("="*74); print("DECOMPOSITION: is the edge from HIGH premium or LOW realised vol?"); print("="*74)
print("%-14s %12s %12s %12s"%("","trailing%","forward%","diff"))
print("%-14s %12.5f %12.5f %+12.5f"%("SQUEEZE",R['sq_tr'].mean(),R['sq_fw'].mean(),R['sq_tr'].mean()-R['sq_fw'].mean()))
print("%-14s %12.5f %12.5f %+12.5f"%("NON-SQUEEZE",R['ns_tr'].mean(),R['ns_fw'].mean(),R['ns_tr'].mean()-R['ns_fw'].mean()))
print()
print("Squeeze trailing vol vs control: %+.5f%% (%.2fx)"%(R['sq_tr'].mean()-R['ns_tr'].mean(),R['sq_tr'].mean()/R['ns_tr'].mean()))
print("Squeeze forward  vol vs control: %+.5f%% (%.2fx)"%(R['sq_fw'].mean()-R['ns_fw'].mean(),R['sq_fw'].mean()/R['ns_fw'].mean()))
print()
if R['sq_tr'].mean()>R['ns_tr'].mean() and R['sq_fw'].mean()>=R['ns_fw'].mean():
    print("*** THE EDGE IS ENTIRELY IN THE PREMIUM PROXY ***")
    print("Squeeze bars have HIGHER trailing vol AND HIGHER forward vol.")
    print("Selling 'trailing vol' only wins because trailing > forward MECHANICALLY:")
    print("the gate selects bars where recent vol spiked then compressed (HV<0.8).")
    print("A real option seller does NOT get paid trailing vol - they get paid IV,")
    print("which already prices the compression. This edge is NOT harvestable.")
