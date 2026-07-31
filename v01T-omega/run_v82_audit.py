import math
print("="*64); print("V82.LOWDD SELF-CONSISTENCY AUDIT (using only the doc's own numbers)"); print("="*64)
cap0=10_000; pnl=244_000_000; N=1_070_000; months=78
term=cap0+pnl; mult=term/cap0
print(f"start ${cap0:,}  total PnL ${pnl:,}  -> terminal ${term:,.0f} = {mult:,.1f}x")
print(f"months {months}, trades {N:,} ({N/months:,.0f}/mo)")

lg=math.log(mult)
print(f"\ntotal log growth ln({mult:,.0f}) = {lg:.3f}")
print(f"monthly ROI implied = {100*(mult**(1/months)-1):.2f}%/mo   <-- doc implies this")

r_real=lg/N
print(f"\nIMPLIED mean return per trade = {lg:.3f}/{N:,} = {100*r_real:.6f}%")
R=0.001
print(f"in R units (R = 0.1% risk)     = {r_real/R:.4f}R")

print(f"\nDOC CLAIMS expectancy         = +0.4400R  (0.48*2 - 0.52*1)")
print(f"discrepancy factor            = {0.44/(r_real/R):,.0f}x")

r_claim=0.44*R
print(f"\nif +0.44R were true over {N:,} trades:")
print(f"  ln(final/start) = {N*math.log(1+r_claim):,.0f}  -> e^{N*math.log(1+r_claim):,.0f}")
print("  that is not a number of dollars that can exist.")

print("\n" + "-"*64)
print("WHAT WIN RATE DOES THE REALIZED PnL IMPLY? (2:1 payoff)")
p=(r_real/R+1)/3
print(f"  p*2R - (1-p)*1R = {r_real/R:.4f}R  ->  p = {100*p:.2f}%")
print(f"  driftless random walk, +2a before -a  ->  p = {100/3:.2f}%")
print(f"  EXCESS OVER COIN FLIP = {100*p-100/3:+.2f} percentage points")
print(f"  doc claims 48% (excess +14.67 pts)")

print("\n" + "-"*64)
print("OVERLAP CHECK")
epics=8; days=months*21.7
tpd=N/days; tpde=tpd/epics
bars=288
print(f"  {tpd:,.0f} trades/day total, {tpde:,.1f}/day/EPIC")
print(f"  5m bars/day = {bars}; hold = 12 bars")
print(f"  max NON-overlapping trades/day/EPIC = {bars/12:.0f}")
print(f"  claimed {tpde:.1f} > {bars/12:.0f}  -> positions MUST overlap")
print(f"  mean concurrent positions/EPIC = {tpde*12/bars:.2f}")
print(f"  -> true risk/EPIC = {tpde*12/bars*0.1:.2f}% not 0.10%")

print("\n" + "-"*64)
print("COST SENSITIVITY (none modelled in the doc)")
print(f"  realized edge = {r_real/R:.4f}R = {100*r_real:.6f}% of capital/trade")
print(f"  1 R = 1x ATR(5m). cost of c% of the STOP distance = c/100 R")
for c in (1,2,5,10,25):
    net=r_real/R - c/100
    print(f"   spread+slip = {c:5.1f}% of stop -> net {net:+.4f}R  {'PROFIT' if net>0 else 'LOSS'}")
print(f"\n  breakeven cost = {100*r_real/R:.2f}% of the stop distance.")
