"""Is -1.5R cap REAL or a fantasy? And what is the hard ceiling?"""
import numpy as np
A=np.load('/tmp/v82/events.npy'); P=A[A[:,4]==0]; R=P[:,2]
print("HONESTY CHECK on the -1.5R tail cap")
print("  trades worse than -1.5R: %d of %d = %.3f%%"%((R<-1.5).sum(),len(R),100*(R<-1.5).mean()))
print("  their total R: %.0f ; capping recovers %.0f R = %.4f R/trade"%(
    R[R<-1.5].sum(), R[R<-1.5].sum()-(-1.5*(R<-1.5).sum()), (R[R<-1.5].sum()+1.5*(R<-1.5).sum())/len(R)))
print()
print("  These losses are GAP-THROUGH fills: price opened past the stop.")
print("  A -1.5R cap means you were filled at -1.5R when the market was at -44R.")
print("  NOBODY fills you there. The counterparty would have to eat -42.5R.")
print("  => the cap is NOT free. It must be BOUGHT.")
print()
print("  Real instruments that cap loss:")
print("   - guaranteed stop-loss (GSLO): brokers charge a premium per trade")
print("   - long option instead of stop: pay theta")
print("  Cost of the cap, breakeven: it recovers %.4f R/trade,"%((R[R<-1.5].sum()+1.5*(R<-1.5).sum())/len(R)))
print("  so ANY premium above that per trade makes it a net loss.")
rec=(R[R<-1.5].sum()+1.5*(R<-1.5).sum())/len(R)
print("  premium budget = %.4f R = %.3f%% of the stop distance per trade."%(rec,100*abs(rec)))
print()
print("VERDICT: capping is worth at most %.4f R/trade. Typical GSLO premium is"%abs(rec))
print("  0.3-1.0%% of notional, i.e. ~0.3-1.0 R on a 1-ATR stop. That is 10-30x")
print("  MORE than the benefit. The -1.5R cap is NOT purchasable at a profit.")
print("  => 165%% is NOT achievable. The honest number stays ~100%%/mo.")
print()
# hard ceiling from the goal law using REALISED equity Sharpe
print("HARD CEILING, from realised monthly equity Sharpe")
t0=P[:,0].min(); mb=((P[:,0]-t0)/86400000/30.44).astype(int)
rows=[]
for m in sorted(set(mb)):
    v=R[mb==m]
    if len(v)>=50: rows.append(v.sum())
s=np.array(rows); S=s.mean()/s.std(ddof=1)
print("  monthly sum-R Sharpe = %.3f"%S)
print("  ln(1+ROI) = 2*D*S^2, D=0.04 -> ROI = %.2f%%/mo"%(100*(np.exp(2*0.04*S**2)-1)))
need=np.sqrt(np.log(11)/0.08)
print("  need S=%.3f for 1000%%. have %.3f. shortfall %.2fx -> need %.1fx more independent months/streams"%(
    need,S,need/S,(need/S)**2))
