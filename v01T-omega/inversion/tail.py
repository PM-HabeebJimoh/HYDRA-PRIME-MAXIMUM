"""1.0979x breakeven was an AVERAGE. Averages hide convexity.
A long straddle is a lottery: mostly small losses, rare huge wins.
Ask instead: WHICH SUBSET has breakeven IV high enough to clear a 1.25x market?"""
import numpy as np, math, os
D=np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)),'opt_rows.npy'))
s20,s5,hv,atband,el,pay,sym=D.T
W=4
def Nd(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def prem_of(sig_T): return 2*(Nd(sig_T/2)-Nd(-sig_T/2))
def breakeven(mask):
    if mask.sum()<200: return None
    lo,hi=0.5,5.0
    for _ in range(60):
        m=(lo+hi)/2
        net=pay[mask]-np.array([prem_of(x) for x in s20[mask]*math.sqrt(W)*m])
        if net.mean()>0: lo=m
        else: hi=m
    return lo
band=atband>0.5
print("="*78); print("IS THE EDGE CONCENTRATED? breakeven IV by sub-population"); print("="*78)
print("baseline: band-only breakeven = %.4fx  (market 1.1-1.4x)"%breakeven(band))
print()
# 1. by how EXTREME the band break is
print("--- by trailing vol level (s20 quintile) ---")
q=np.nanquantile(s20[band],[0,.2,.4,.6,.8,1.0])
for i in range(5):
    m=band&(s20>=q[i])&(s20<q[i+1])
    b=breakeven(m)
    if b: print("  vol Q%d  n=%6d  breakeven %.4fx  %s"%(i+1,m.sum(),b,"CLEARS 1.25" if b>1.25 else ""))
print()
print("--- by HV ratio bucket (v01T uses <0.8) ---")
for lo,hi in ((0,0.6),(0.6,0.8),(0.8,1.0),(1.0,1.3),(1.3,99)):
    m=band&(hv>=lo)&(hv<hi)
    b=breakeven(m)
    if b: print("  HV %.1f-%.1f  n=%6d  breakeven %.4fx  %s"%(lo,hi,m.sum(),b,"CLEARS 1.25" if b>1.25 else ""))
print()
print("--- by instrument ---")
SY=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
best=[]
for i,s in enumerate(SY):
    m=band&(sym==i)
    b=breakeven(m)
    if b:
        best.append((b,s,m.sum()))
        print("  %-5s n=%6d  breakeven %.4fx  %s"%(s,m.sum(),b,"CLEARS 1.25" if b>1.25 else ""))
best.sort(reverse=True)
print()
print("BEST: %s at %.4fx"%(best[0][1],best[0][0]))
