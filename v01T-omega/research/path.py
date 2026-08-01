"""Monthly EDGE Sharpe is 5.00, but realised equity Sharpe was 1.383.
The loss is between 'edge per trade' and 'equity path'. Locate it exactly."""
import numpy as np
A=np.load('/tmp/v82/events.npy'); P=A[A[:,4]==0]
t0=A[:,0].min(); R=P[:,2]
mb=((P[:,0]-t0)/86400000/30.44).astype(int)
rows=[]
for m in sorted(set(mb)):
    v=R[mb==m]
    if len(v)>=50: rows.append((m,len(v),v.mean(),v.sum()))
rows=np.array(rows)
print("months %d ; mean trades/mo %.0f"%(len(rows),rows[:,1].mean()))
print("monthly mean-R : mean %+.4f sd %.4f Sharpe %.3f  (edge is VERY stable)"%(
    rows[:,2].mean(),rows[:,2].std(ddof=1),rows[:,2].mean()/rows[:,2].std(ddof=1)))
# monthly SUM of R = what actually drives equity at fixed fractional risk
print("monthly SUM-R  : mean %+.1f  sd %.1f  Sharpe %.3f"%(
    rows[:,3].mean(),rows[:,3].std(ddof=1),rows[:,3].mean()/rows[:,3].std(ddof=1)))
print("  -> trade COUNT varies a lot: sd/mean of count = %.3f"%(rows[:,1].std(ddof=1)/rows[:,1].mean()))
print()
print("KEY: at fixed fractional risk f, monthly log-return ~ f * sum(R).")
print("     So the Sharpe that matters is on SUM-R = %.3f, not mean-R = %.3f"%(
    rows[:,3].mean()/rows[:,3].std(ddof=1), rows[:,2].mean()/rows[:,2].std(ddof=1)))
print()
# The DD is driven by the worst DRAWDOWN WITHIN a month, not month-end marks.
print("Now the real killer: INTRA-MONTH drawdown.")
# simulate at tiny f, measure DD and monthly ROI
def sim(f):
    n=len(P); t_o=P[:,0]; t_c=P[:,1]
    ev=np.concatenate([np.stack([t_o,np.zeros(n),np.arange(n)],1),
                       np.stack([t_c,np.ones(n),np.arange(n)],1)])
    ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
    cap=1.0;peak=1.0;dd=0.0;staked=np.zeros(n);live=np.zeros(n,bool)
    for k in range(len(ev)):
        ty=ev[k,1]; i=int(ev[k,2])
        if ty==0: staked[i]=cap*f; live[i]=True
        else:
            if live[i]:
                cap+=staked[i]*R[i]; live[i]=False
                if cap<=0: return 0,1
                peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
    return cap,dd
mo=(P[:,1].max()-t0)/86400000/30.44
print("%-12s %10s %12s"%("risk f","maxDD%","ROI/mo"))
for f in (0.0001,0.0005,0.001,0.002,0.005):
    c,dd=sim(f)
    print("%-12s %10.3f %+11.2f%%"%(f"{100*f:.3f}%",100*dd,100*(c**(1/mo)-1) if c>0 else -100))
print()
print("Note DD grows ~linearly in f while ROI grows ~exponentially.")
print("That asymmetry is what a DD cap exploits. Check the ACTUAL worst month:")
worst=rows[np.argmin(rows[:,2])]
print("  worst month idx %d: n=%d meanR %+.4f sumR %+.1f"%(worst[0],worst[1],worst[2],worst[3]))
print("  -> even the WORST of 95 months is positive. DD comes from WITHIN-month runs.")
