"""Price a REAL 4h ATM straddle at each squeeze using Black-Scholes with IV set
from trailing realised vol, then settle it on the ACTUAL forward path.
This is the honest test of the option route I earlier dismissed without measuring."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import load_1m, resample
import numpy as np
from still import bb_hv_vec, SY
W=4
SQ=math.sqrt(2*math.pi)

def bs_straddle(S,sig_T):
    """ATM straddle price, r=0. Exact: 2*S*(N(d)-0.5) with d=sig_T/2.
    Excellent approx 0.7979*S*sig_T."""
    return 2*S*(0.5*math.erf((sig_T/2)/math.sqrt(2)))

def run(iv_mult, W=4, gate=True):
    net=[]
    for s in SY:
        a=load_1m(s)
        if a is None or len(a)<50000: continue
        f=resample(a,60); c=f[:,2]
        if len(c)<200: continue
        bb,hv=bb_hv_vec(c)
        sc=np.where(bb<10,92,np.where(bb>90,85,72))
        el=((bb<10)|(bb>90))&(hv<0.8)&(sc>=85)
        r=np.zeros(len(c)); r[1:]=c[1:]/c[:-1]-1
        N=len(c); sig=np.full(N,np.nan)
        cx=np.cumsum(np.insert(r,0,0.0)); cx2=np.cumsum(np.insert(r*r,0,0.0))
        k=5; m=(cx[k:]-cx[:-k])/k; v=(cx2[k:]-cx2[:-k])/k-m*m
        sig[k-1:]=np.sqrt(np.maximum(v,0.0)*k/(k-1))
        for i in range(30,N-W-1):
            if gate and not el[i]: continue
            sg=sig[i]
            if not np.isfinite(sg) or sg<=0: continue
            e=i+1                      # executable: next bar
            S0=f[e,1]
            iv_T=sg*math.sqrt(W)*iv_mult
            prem=bs_straddle(S0,iv_T)
            payoff=abs(c[min(e+W-1,N-1)]-S0)   # European settle at expiry
            net.append((payoff-prem)/S0)
    return np.array(net)

print("REAL 4h ATM STRADDLE — bought at each squeeze, settled on the real path")
print("IV is set to trailing realised vol x multiplier (the vol risk premium).")
print()
print("%-34s %8s %12s %9s"%("scenario","n","mean %S","t"))
for mult,lbl in ((1.00,'IV = realised (no VRP)'),(1.10,'IV = 1.10x (10% VRP)'),
                 (1.25,'IV = 1.25x (25% VRP)'),(1.50,'IV = 1.50x (50% VRP)'),
                 (1.5630,'IV = 1.5630x (breakeven)')):
    x=run(mult)
    se=x.std(ddof=1)/np.sqrt(len(x))
    print("%-34s %8d %+11.4f%% %+9.2f"%(lbl,len(x),100*x.mean(),x.mean()/se))
print()
print("CONTROL — same option bought at NON-squeeze bars (IV=1.25x):")
xb=run(1.25,gate=False)
se=xb.std(ddof=1)/np.sqrt(len(xb))
print("%-34s %8d %+11.4f%% %+9.2f"%("all bars",len(xb),100*xb.mean(),xb.mean()/se))
