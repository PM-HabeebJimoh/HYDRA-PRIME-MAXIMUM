"""t=+604 is impossible. Audit my own fix.py. A straddle payoff of |move|
is ALWAYS >= 0 -- that is the bug: I priced the PAYOFF but never the PREMIUM.

A real long straddle costs money up front (option premium, or in perp terms,
the two stops you WILL eat). |move| - fee is not the P&L. It ignores that you
must PAY for optionality."""
import numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
S=np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)),'sig_moves.npy'))
print("="*74); print("THE BUG IN MY OWN 'FIX'"); print("="*74)
print("fix.py computed:  payoff = |move at exit| - fee")
print("|move| >= 0 ALWAYS. So payoff is positive whenever |move| > fee.")
print("That is not a strategy - it is the statement 'prices move'.")
print()
print("A LONG STRADDLE IS NOT FREE. To be long volatility you must pay:")
print("  - options: the premium (theta)")
print("  - perps  : you cannot be long vol with two perp legs at all -")
print("             long+short perp = ZERO net exposure, exactly.")
print()
print("PROOF that a stopless perp straddle is identically flat:")
entry=100.0
for exit_ in (95.0,100.0,103.7,120.0):
    L=(exit_-entry); Sh=(entry-exit_)
    print("   exit %7.2f -> long %+7.3f  short %+7.3f  NET %+.10f"%(exit_,L,Sh,L+Sh))
print()
print("=> long+short perp of equal size has ZERO P&L on ANY path.")
print("   The ONLY thing that makes v01T's straddle non-zero is the STOP,")
print("   which closes one leg early and breaks the symmetry.")
print("   Remove the stop and you remove the entire strategy.")
print()
print("="*74); print("SO THE REAL QUESTION"); print("="*74)
print("Can the +0.192%% vol premium be harvested at all?")
print("  premium (squeeze vs baseline) = 0.1921%% of price")
print("  cost of 4 taker legs @6.5bp   = 0.2600%% of price")
print("  => 0.74x. NO.")
print()
print("With options you would pay implied vol, which is ALREADY priced off")
print("realised vol. The 0.19%% edge must exceed the bid/ask on the option,")
print("which for BTC 4h options is far wider than 0.19%.")
