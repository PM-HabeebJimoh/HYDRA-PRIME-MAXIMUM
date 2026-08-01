"""WR 57.44% on a 3:1 barrier vs 25% random is +32 points. That is enormous.
Enormous edges in backtests are usually LOOKAHEAD. Hunt it."""
from load import *; from v82 import *
import numpy as np, bisect, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega')
from omega.indicators import bb_percent

a=load_1m('XLM'); f=resample(a,5); h=resample(a,60)
print("BAR CONSTRUCTION CHECK — the resampler")
print("  cols: MTS,OPEN,CLOSE,HIGH,LOW,VOL,count")
print("  first 3 5m bars:")
for i in range(3): print("   ",f[i][:6])
# Is the 5m bar's CLOSE the last 1m close inside the bucket? yes by construction.
# CRITICAL: does bar i's HIGH/LOW include data AFTER its close? No.
# But: is the ENTRY at C[i] executable at the TIME of bar i's close? yes.
# THE REAL RISK: the 1H forecast index. bisect_right(ht, f[i,0]) - 1
ht=list(h[:,0])
print("\n1H ALIGNMENT CHECK — the classic lookahead")
for i in (500,5000,50000):
    t=f[i,0]; k=bisect.bisect_right(ht,t)-1
    print("   5m bar t=%d -> 1H bar k=%d starting t=%d"%(t,k,h[k,0]))
    print("      1H bar k SPANS [%d, %d)"%(h[k,0],h[k,0]+3600000))
    print("      is 5m bar inside that 1H bar? %s"%(h[k,0]<=t<h[k,0]+3600000))
    print("      *** 1H bar k's CLOSE is only known at %d, but we use it at %d ***"%(h[k,0]+3600000,t))
    print("      LOOKAHEAD = %.1f minutes"%((h[k,0]+3600000-t)/60000))
print("\nTHIS IS THE BUG. compute_1h_forecast uses h[k,2] = the CLOSE of the")
print("1H bar that is STILL FORMING. trend_up, streak and ret_3bar all depend")
print("on that close. At 5m bar t we cannot know the 1H close until the hour ends.")
print("\nV82's own spec does this too (bisect_right - 1). It is in the original.")
print("Average lookahead = 30 minutes of future information.")
