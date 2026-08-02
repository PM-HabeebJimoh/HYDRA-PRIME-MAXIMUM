"""
iter60: the ENTIRE problem is now one number.

At 1-minute frequency, 80% WR, L=1:
   required NET move = 0.69 bp
   real 2026 BTC 1m median move = 1.090 bp  (Bitfinex, measured)
   => budget for ALL costs = 1.090 - 0.69 = 0.400 bp round trip

So: >500%/mo at 80% accuracy with NO LEVERAGE is achievable in 2026
IF AND ONLY IF total round-trip cost <= 0.400 bp. Nothing else matters.
Check that against real 2026 fee schedules.
"""
med = 1.090      # bp, measured 2026 BTC 1m open->close, Bitfinex
req = 0.69       # bp, required net at WR80 / N=43200 / L=1

print("="*76)
print("THE WHOLE PROBLEM, ONE NUMBER")
print("="*76)
print(f"real 2026 BTC 1m median move   {med:>7.3f} bp")
print(f"needed net at WR80%, L=1       {req:>7.3f} bp")
print(f"TOTAL COST BUDGET              {med-req:>7.3f} bp round trip")
print()
print("REAL 2026 fee schedules (round trip = 2 x per-side, + spread if taker):")
print()
rows = [
 ("Bitfinex taker (0.20%)",           2*20.0,   1.649, "no"),
 ("Bitfinex maker (0.10%)",           2*10.0,   0.0,   "no"),
 ("Binance VIP0 taker (0.10%)",       2*10.0,   1.649, "no"),
 ("Binance VIP9 taker (0.02%)",       2*2.0,    1.649, "no"),
 ("Binance VIP9 maker (0.00%)",       0.0,      0.0,   "yes"),
 ("Kraken Pro taker (0.10%)",         2*10.0,   1.649, "no"),
 ("Kraken Pro maker top-tier (0.00%)",0.0,      0.0,   "yes"),
 ("CME futures (per-contract)",       2*0.20,   0.5,   "no"),
 ("Maker REBATE venue (-0.005%)",     2*-0.5,   0.0,   "yes"),
]
print(f"{'venue / tier':<36} {'fee_rt':>8} {'spread':>8} {'TOTAL':>9} {'verdict':>9}")
best=None
for name, fee_bp, spread, feasible in rows:
    tot = fee_bp + spread
    ok = tot <= (med-req)
    print(f"{name:<36} {fee_bp:>8.2f} {spread:>8.3f} {tot:>9.3f} {'PASS' if ok else 'FAIL':>9}")
    if ok and (best is None or tot<best[1]): best=(name,tot)
print()
if best:
    name,tot = best
    net = med - tot
    e = net/1e4*0.6
    mo = ((1+e)**43200-1)*100
    print(f"CHEAPEST PASSING: {name}  total {tot:.3f} bp")
    print(f"   net move {net:.3f} bp -> edge {e*1e4:.3f} bp/trade")
    print(f"   monthly ROI at L=1, WR80%, 43200 trades = {mo:,.0f}%")
else:
    print("NO venue passes.")
print()
print("="*76)
print("BUT: 'maker' means you POST and WAIT. Two consequences I must not hide:")
print("="*76)
print(" 1. FILL RATE. A resting order fills only when price comes to you.")
print("    You do not get 43,200 fills/month, you get (fill_rate x 43,200).")
print(" 2. ADVERSE SELECTION. The fills you DO get are the ones where price")
print("    kept going against you. Maker WR is systematically BELOW taker WR.")
print()
print("Required trades/mo to still hit 500% at various realistic fill rates,")
print("using the maker net edge above:")
e = (med-0.0)/1e4*0.6
import math
need_N = math.log(6)/math.log(1+e)
print(f"   trades needed at maker edge {e*1e4:.3f}bp: {need_N:,.0f}/month")
print(f"   available 1m bars/month:                43,200")
print(f"   => required FILL RATE:                  {need_N/43200*100:.1f}%")
print()
print("So the honest remaining question is not accuracy and not leverage.")
print(f"It is: can you fill {need_N/43200*100:.1f}% of posted 1m orders at 80% WR")
print("while paying zero fees? THAT is the last blocker, and it is a real")
print("microstructure question, not one in my head.")
