"""iter59: is TSLA_1d (the ONE positive of 11 series) real, or the best of 11 coin flips?"""
import math
# From wf2026.py, ERA 2026, real bars, gross
res = {'BTC_4h':(578,49.31,-1.19),'DXY_4h':(163,53.99,-0.46),'HYPE_4h':(578,48.27,-5.89),
       'SOL_4h':(578,48.62,-0.64),'BTC_1d':(406,45.07,-26.00),'DXY_1d':(225,47.56,-1.44),
       'PLTR_1d':(223,46.64,-6.87),'QQQ_1d':(223,50.67,-0.38),'SOL_1d':(406,44.83,-9.75),
       'SPX_1d':(223,46.64,-8.14),'SPY_1d':(223,46.64,-4.96),'TSLA_1d':(223,60.09,44.63)}
print("MULTIPLE-COMPARISONS CHECK on the 11-series 2026 sweep")
print("="*70)
n,wr,_ = res['TSLA_1d']
k = round(wr/100*n)
p = 0.5
# exact binomial tail P(X>=k) under fair coin
tail = sum(math.comb(n,i) for i in range(k, n+1)) / 2**n
print(f"TSLA_1d: {k}/{n} wins = {wr:.2f}%")
print(f"one-sided binomial p (single test)       = {tail:.5f}")
m = len(res)
print(f"Bonferroni over {m} series tested          = {min(1.0, tail*m):.5f}")
fam = 1-(1-tail)**m
print(f"P(at least one of {m} this good | all noise) = {fam:.5f}")
print()
print(f"mean WR across all {m} series = {sum(v[1] for v in res.values())/m:.2f}%  (random = 50%)")
print(f"mean edge across all {m}       = {sum(v[2] for v in res.values())/m:.2f} bp")
print(f"positive-edge series          = {sum(1 for v in res.values() if v[2]>0)}/{m}")
print()
print("VERDICT:", "TSLA survives Bonferroni - worth a real OOS test" if tail*m<0.05
      else "TSLA does NOT survive multiple comparisons - it is the best of 11 coin flips")
print()
print("="*70)
print("AND EVEN IF IT WERE REAL: what does 60.09% WR buy at 1x?")
print("="*70)
tpm = 223/11.0
e = 44.63/10000
print(f"trades/month = {tpm:.1f}, edge = 44.63bp")
print(f"monthly ROI at 1x = {((1+e)**tpm-1)*100:.2f}%")
for L in (1,5,10,25,50,100):
    print(f"  L={L:>3}x -> {((1+e*L)**tpm-1)*100:>12,.1f}%/mo   "
          f"worst single trade needed to liquidate: {-100/L:.2f}%")
print()
print("TSLA 1d median |move| 2026 = 1.8906%. At L=50 a 2% adverse day = -100%.")
print("Real TSLA 2026 max 1d |move| exceeded that repeatedly -> liquidation.")
