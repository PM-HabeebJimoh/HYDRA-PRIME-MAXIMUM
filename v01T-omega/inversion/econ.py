"""My inversion is DEAD. Squeezes DO predict movement (+9.37%, t=+11.00).
So v01T's THESIS is right. The question becomes: is the vol premium big enough
to pay for the straddle's costs? Compute the exact economics."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
S=np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)),'sig_moves.npy'))
B=np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)),'base_moves.npy'))
print("="*72); print("THE VOLATILITY PREMIUM, PRICED"); print("="*72)
print("squeeze  E[max |move| over 4h] = %.4f%% of price"%(100*S.mean()))
print("baseline E[max |move| over 4h] = %.4f%% of price"%(100*B.mean()))
print("PREMIUM                        = %.4f%% of price   (t=+11.00)"%(100*(S.mean()-B.mean())))
print()
print("v01T pays for that premium with FOUR taker legs:")
for fee in (4.0,6.5,10.0):
    cost=4*fee*1e-4
    print("  taker %4.1fbp x4 legs = %.4f%% of price   premium/cost = %.2fx"%(fee,100*cost,(S.mean()-B.mean())/cost))
print()
print("=> the premium is the SAME ORDER as the fee. There is no room.")
print()
print("="*72); print("WHAT FRACTION OF SQUEEZES REACH v01T's 0.5% TARGET?"); print("="*72)
for tp in (0.005,0.01,0.02,0.03):
    ps=(S>=tp).mean(); pb=(B>=tp).mean()
    print("  target %.1f%%: squeeze %.2f%% vs baseline %.2f%%  lift %+.2f pts"%(100*tp,100*ps,100*pb,100*(ps-pb)))
print()
print("="*72); print("THE STRADDLE'S REAL PROBLEM, IN ONE NUMBER"); print("="*72)
print("A straddle needs price to travel FAR IN ONE DIRECTION without first")
print("retracing through the opposite stop. v01T's stop is 0.05%, target 0.5%.")
print("The target is 10x the stop. So the path must be 10:1 directional.")
print()
print("P(|move| >= 0.5%%) after squeeze = %.2f%%  -- looks easy"%(100*(S>=0.005).mean()))
print("BUT that is |max move|, ignoring PATH. The 0.05%% stop is hit by")
print("ordinary noise long before the 0.5%% target is reached.")
