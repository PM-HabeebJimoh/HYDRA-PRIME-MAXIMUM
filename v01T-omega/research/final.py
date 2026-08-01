"""DEFINITIVE: what does 1000%/mo REQUIRE, and how far is the best real config?"""
import numpy as np, datetime as dt, glob, os
best='/tmp/v82/grid_tf5_pull_bb40_T3_S1_H12.npy'
E=np.load(best); E=E[np.argsort(E[:,0])]
R=E[:,2]; mo=(E[:,1].max()-E[:,0].min())/86400000/30.44
n=len(R); se=R.std(ddof=1)/np.sqrt(n); t=R.mean()/se
print("BEST EXECUTABLE CONFIG (bb<40 pullback, T3/S1, hold 12, 5m)")
print("  n=%d  %.1f months  meanR %+.5f  sd %.4f  t=%+.2f  WR %.2f%%"%(n,mo,R.mean(),R.std(ddof=1),t,100*(R>0).mean()))

# OOS
SP=dt.datetime(2020,1,1).timestamp()*1000
tr=R[E[:,1]<SP]; te=R[E[:,0]>=SP]
print("  OOS: train n=%d %+.5f (t=%+.2f) | TEST n=%d %+.5f (t=%+.2f)"%(
    len(tr),tr.mean(),tr.mean()/(tr.std(ddof=1)/np.sqrt(len(tr))),
    len(te),te.mean(),te.mean()/(te.std(ddof=1)/np.sqrt(len(te)))))
# per symbol
pos=sum(1 for s in np.unique(E[:,3]) if R[E[:,3]==s].mean()>0)
print("  positive on %d of %d symbols"%(pos,len(np.unique(E[:,3]))))
# multiple testing: 360 configs in grid
print("  multiple testing: 360 configs planned, Bonferroni |t|>%.2f -> %s"%(
    3.4,"PASSES" if abs(t)>3.4 else "FAILS"))

print("\n=== THE EXACT ARITHMETIC OF 1000%/MONTH ===")
S_mo=t/np.sqrt(mo)
print("realised monthly Sharpe = t/sqrt(months) = %.2f/%.2f = %.4f"%(t,np.sqrt(mo),S_mo))
need=np.sqrt(np.log(11)/(2*0.04))
print("required monthly Sharpe for 1000%% at DD 4%% = sqrt(ln(11)/0.08) = %.4f"%need)
print("SHORTFALL = %.2fx in Sharpe"%(need/S_mo))
print("Sharpe scales as sqrt(N) -> need %.0fx more INDEPENDENT trades/streams"%((need/S_mo)**2))
print()
tpm=n/mo
print("current %.0f trades/month -> would need %.0f trades/month"%(tpm,tpm*(need/S_mo)**2))
print("at 5m bars, 13 symbols, that is %.0f bars/month available"%(288*30.44*13))
print("REQUIRED %.0f > AVAILABLE %.0f  -> IMPOSSIBLE by factor %.1fx"%(
    tpm*(need/S_mo)**2, 288*30.44*13, tpm*(need/S_mo)**2/(288*30.44*13)))
print()
print("=== ALTERNATIVE: raise edge instead of count ===")
print("ROI at DD4 with current edge: +0.24%/mo")
print("to reach 1000%/mo at DD4 need Sharpe %.2fx higher = edge %.2fx higher"%(need/S_mo,need/S_mo))
print("i.e. meanR must go %+.5f -> %+.5f R per trade"%(R.mean(),R.mean()*need/S_mo))
print("that is %.1f%% of the stop distance per trade, on EVERY trade, after costs."%(100*R.mean()*need/S_mo))
print()
print("=== WHAT DD WOULD 1000% REQUIRE AT THE MEASURED SHARPE? ===")
D=np.log(11)/(2*S_mo**2)
print("D = ln(11)/(2*S^2) = %.3f = %.0f%% drawdown"%(D,100*D))
print("i.e. you would need to accept a %.0f%% drawdown - account destruction."%(100*D))
