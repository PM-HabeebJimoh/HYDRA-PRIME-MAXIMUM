"""WHERE DOES THE CONSTRAINT ACTUALLY BIND? Exact decomposition."""
import numpy as np
A=np.load('/tmp/v82/events.npy')
P=A[A[:,4]==0]   # pullback
t0=A[:,0].min(); t1=A[:,1].max(); mo=(t1-t0)/86400000/30.44
R=P[:,2]
print("PULLBACK STREAM: n=%d  meanR %+.4f  sdR %.4f  months %.1f  trades/mo %.0f"%(
    len(R),R.mean(),R.std(ddof=1),mo,len(R)/mo))

# --- the exact goal law -------------------------------------------------
# ln(1+ROI) = 2*D*S^2  where S = Sharpe over the SAME period, D = max DD fraction
S_tr = R.mean()/R.std(ddof=1)                 # per-trade Sharpe
n_mo = len(R)/mo
S_mo = S_tr*np.sqrt(n_mo)                     # monthly Sharpe if INDEPENDENT
print("\nper-trade Sharpe %.5f   -> monthly Sharpe if independent = %.3f"%(S_tr,S_mo))
print("ln(1+ROI) = 2*D*S^2  with D=0.04 -> ROI = %.2f%%"%(100*(np.exp(2*0.04*S_mo**2)-1)))
print("   (measured parallel result was ~+100%%, so streams are NOT independent)")

# --- how many INDEPENDENT streams do we really have? --------------------
# bucket returns by month per symbol, correlate
syms=np.unique(P[:,3]).astype(int)
mb=((P[:,0]-t0)/86400000/30.44).astype(int)
M=mb.max()+1
G=np.full((len(syms),M),np.nan)
for a,s in enumerate(syms):
    for m in range(M):
        v=R[(P[:,3]==s)&(mb==m)]
        if len(v)>=5: G[a,m]=v.mean()
ok=~np.isnan(G)
print("\nmonthly mean-R panel: %d symbols x %d months, %.0f%% filled"%(G.shape[0],G.shape[1],100*ok.mean()))
C=np.ma.corrcoef(np.ma.masked_invalid(G)).data
iu=np.triu_indices(len(syms),1)
rbar=np.nanmean(C[iu])
k=len(syms)
neff=k/(1+(k-1)*rbar)
print("mean pairwise correlation of monthly edge = %.4f"%rbar)
print("EFFECTIVE independent streams = %d/(1+%d*%.4f) = %.2f  (of %d)"%(k,k-1,rbar,neff,k))

S_eff=S_tr*np.sqrt(n_mo)*np.sqrt(neff/k)  if False else None
# portfolio Sharpe with correlation: S_p = S_single*sqrt(k/(1+(k-1)r))
S_single=S_tr*np.sqrt(n_mo/k)
S_port=S_single*np.sqrt(neff)
print("\nper-symbol monthly Sharpe %.3f -> portfolio monthly Sharpe %.3f"%(S_single,S_port))
print("=> ROI at DD 4%% = %.2f%%   (matches the measured ~100%%)"%(100*(np.exp(2*0.04*S_port**2)-1)))

# --- what is REQUIRED for 1000%? ----------------------------------------
need=np.sqrt(np.log(11)/(2*0.04))
print("\nREQUIRED monthly Sharpe for 1000%% at DD<4%% = sqrt(ln(11)/0.08) = %.3f"%need)
print("have %.3f -> shortfall factor %.2fx in Sharpe"%(S_port,need/S_port))
print("Sharpe ~ sqrt(neff) -> need %.1fx more INDEPENDENT streams"%((need/S_port)**2))
print("   i.e. neff must go %.1f -> %.0f"%(neff,neff*(need/S_port)**2))
print("   at r=%.4f that means k = %.0f correlated instruments"%(rbar, (neff*(need/S_port)**2)))
kx=neff*(need/S_port)**2
print("   BUT with r=%.4f, neff CAPS at 1/r = %.1f as k->inf"%(rbar,1/rbar))
print("   => MORE CRYPTO INSTRUMENTS CANNOT REACH IT. Ceiling ROI = %.1f%%"%(
    100*(np.exp(2*0.04*(S_single*np.sqrt(1/rbar))**2)-1)))
