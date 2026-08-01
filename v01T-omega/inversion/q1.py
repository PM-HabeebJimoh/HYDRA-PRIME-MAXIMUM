"""Vol Q1 breakeven 1.5520x CLEARS a 1.25x market. Before believing it:
is it a handful of jackpots, or a real repeatable edge? And what are WR/DD/ROI?"""
import numpy as np, math, os
D=np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)),'opt_rows.npy'))
s20,s5,hv,atband,el,pay,sym=D.T
W=4
def Nd(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def prem_of(s): return 2*(Nd(s/2)-Nd(-s/2))
band=atband>0.5
q=np.nanquantile(s20[band],[0,.2])
m=band&(s20>=q[0])&(s20<q[1])
IVM=1.25
prem=np.array([prem_of(x) for x in s20[m]*math.sqrt(W)*IVM])
net=pay[m]-prem
# RETURN ON PREMIUM = the actual P&L per dollar of option bought
ret=net/prem
print("VOL Q1, band-only, IV=1.25x (a realistic market price)")
print("  n = %d"%len(ret))
print("  WIN RATE          = %.2f%%"%(100*(ret>0).mean()))
print("  mean return on premium = %+.2f%%"%(100*ret.mean()))
print("  median                 = %+.2f%%"%(100*np.median(ret)))
print("  t = %+.2f"%(ret.mean()/(ret.std(ddof=1)/np.sqrt(len(ret)))))
print()
print("  CONCENTRATION CHECK — remove the best trades:")
s=np.sort(ret)[::-1]
for k in (0,1,5,10,50,100):
    if k<len(s):
        print("    drop top %4d: mean %+.2f%%"%(k,100*s[k:].mean()))
print()
print("  loss is capped at -100%% of premium (option expires worthless):")
print("    worst %.2f%%   best %+.1f%%"%(100*ret.min(),100*ret.max()))
print("    fraction total loss (-100%%): %.2f%%"%(100*(ret<=-0.999).mean()))
