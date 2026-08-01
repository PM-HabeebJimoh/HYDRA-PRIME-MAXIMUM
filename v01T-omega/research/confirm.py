"""The entire remaining 'edge' was same-bar fill. Confirm and quantify."""
import numpy as np
a=np.load('/tmp/v82/ev_close_same_bar.npy'); b=np.load('/tmp/v82/ev_next_open.npy')
for nm,A in (('same-bar close fill (iter29)',a),('next-open fill (executable)',b)):
    R=A[:,2]; se=R.std(ddof=1)/np.sqrt(len(R))
    print("%-32s n=%6d meanR %+.4f SE %.4f t=%+6.2f WR %.2f%%"%(nm,len(R),R.mean(),se,R.mean()/se,100*(R>0).mean()))
R=b[:,2]
rng=np.random.default_rng(0)
bs=np.array([rng.choice(R,len(R),replace=True).mean() for _ in range(2000)])
print("\nexecutable edge bootstrap: 95%% CI %+.4f to %+.4f  P(mean>=0)=%.4f"%(
    np.percentile(bs,2.5),np.percentile(bs,97.5),(bs>=0).mean()))
print("\nper-symbol (executable):")
pos=0
for s in np.unique(b[:,3]).astype(int):
    v=R[b[:,3]==s]
    if len(v)<200: continue
    if v.mean()>0: pos+=1
    print("   sym %2d n=%6d meanR %+.4f"%(s,len(v),v.mean()))
print("positive on %d of 13 symbols"%pos)
print("\n25%% is the random baseline for a 3:1 barrier. We have %.2f%%."%(100*(R>0).mean()))
