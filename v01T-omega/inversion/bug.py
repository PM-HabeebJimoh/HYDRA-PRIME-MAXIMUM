"""Control says buying straddles at RANDOM bars earns +0.53% (t=+181).
That cannot be true - it would be free money. Find my bug."""
import math, numpy as np
print("="*72); print("BUG HUNT: is my BS straddle price correct?"); print("="*72)
S=100.0
for sig_T in (0.01,0.02,0.05,0.10):
    exact=2*S*(0.5*math.erf((sig_T/2)/math.sqrt(2)))
    approx=0.7979*S*sig_T
    # E|move| for lognormal-ish: S*sig*sqrt(2/pi) = 0.7979*S*sig
    print("sig_T=%.3f  my price %.5f  correct ATM straddle %.5f  ratio %.4f"%(
        sig_T,exact,approx,exact/approx))
print()
print("THE BUG: erf(x/sqrt(2)) IS ALREADY 2*N(x)-1.")
print("  N(d)-0.5 = 0.5*erf(d/sqrt2)  =>  2S*(N(d)-0.5) = S*erf(d/sqrt2)")
print("  I wrote 2*S*(0.5*erf(...)) = S*erf(...) -- that IS right for 2S(N(d)-.5)")
print("  BUT the ATM straddle formula is 2S*N(d1)-2S*N(-d1)... let me verify")
print()
print("Correct ATM straddle (r=0, S=K):")
print("  d1 = +sig_T/2, d2 = -sig_T/2")
print("  call = S*N(d1) - S*N(d2);  put = S*N(-d2) - S*N(-d1)")
print("  straddle = call+put = 2S*(N(d1)-N(d2))")
for sig_T in (0.01,0.02,0.05,0.10):
    d1=sig_T/2; d2=-sig_T/2
    Nd=lambda x:0.5*(1+math.erf(x/math.sqrt(2)))
    correct=2*S*(Nd(d1)-Nd(d2))
    mine=2*S*(0.5*math.erf((sig_T/2)/math.sqrt(2)))
    print("  sig_T=%.3f  CORRECT %.5f  MINE %.5f  ratio %.4f"%(sig_T,correct,mine,mine/correct))
print()
print("=> my price is HALF the correct straddle price. I under-charged premium 2x.")
print()
print("="*72); print("SECOND BUG: settlement"); print("="*72)
print("I settled at |c[e+W-1] - S0| -- the close W-1 bars later.")
print("But I priced a W-bar option. Off-by-one shortens the option I sold myself.")
print()
print("="*72); print("THIRD AND WORST: sigma is computed from returns INCLUDING bar i,")
print("and I enter at bar i+1 open. That is fine. BUT trailing 5-bar realised vol")
print("SYSTEMATICALLY UNDERSTATES forward vol at a squeeze BY CONSTRUCTION -")
print("HV<0.8 SELECTS bars where recent vol is low relative to its own past.")
print("Pricing an option off a deliberately-selected LOW vol estimate and then")
print("observing higher realised vol is CIRCULAR. Mean reversion in vol alone")
print("produces this, with no predictive content whatsoever.")
