"""ALL THREE BUGS FIXED + the control that defeats circularity.

fix 1: correct ATM straddle price 2S(N(d1)-N(d2))  [was 2x too cheap]
fix 2: settle at e+W, matching the W-bar option
fix 3: THE KEY - price IV off LONG-window vol (20-bar), not the 5-bar vol that
       the HV<0.8 gate deliberately selects to be low. Using 5-bar vol is
       circular. A real market maker quotes off a longer, stabler estimate.

CONTROL: compare against bars matched on the SAME low 5-bar vol but WITHOUT
the Bollinger band condition. If v01T's edge is just 'low recent vol mean-
reverts', the control captures it and the gate adds nothing."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import load_1m, resample
import numpy as np
from still import bb_hv_vec, SY
W=4
def Nd(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def straddle_price(S,sig_T):
    return 2*S*(Nd(sig_T/2)-Nd(-sig_T/2))

def harvest():
    rows=[]
    for si,s in enumerate(SY):
        a=load_1m(s)
        if a is None or len(a)<50000: continue
        f=resample(a,60); c=f[:,2]
        if len(c)<200: continue
        bb,hv=bb_hv_vec(c)
        r=np.zeros(len(c)); r[1:]=c[1:]/c[:-1]-1
        N=len(c)
        def rstd(k):
            o=np.full(N,np.nan)
            cx=np.cumsum(np.insert(r,0,0.0)); cx2=np.cumsum(np.insert(r*r,0,0.0))
            m=(cx[k:]-cx[:-k])/k; v=(cx2[k:]-cx2[:-k])/k-m*m
            o[k-1:]=np.sqrt(np.maximum(v,0.0)*k/(k-1)); return o
        s5=rstd(5); s20=rstd(20)
        sc=np.where(bb<10,92,np.where(bb>90,85,72))
        atband=(bb<10)|(bb>90)
        el=atband&(hv<0.8)&(sc>=85)
        for i in range(30,N-W-2):
            if not np.isfinite(s20[i]) or s20[i]<=0: continue
            if not np.isfinite(s5[i]): continue
            e=i+1; S0=f[e,1]
            j=min(e+W,N-1)
            payoff=abs(c[j]-S0)
            rows.append((s20[i],s5[i],hv[i],float(atband[i]),float(el[i]),payoff/S0,si))
    return np.array(rows)

D=harvest()
np.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),'opt_rows.npy'),D)
s20,s5,hv,atband,el,pay,sym=D.T
print("harvested %d bars"%len(D))
print()
print("="*80)
print("CORRECT PRICING: IV from 20-bar vol (not the selected 5-bar), correct BS, settle at e+W")
print("="*80)
print("%-46s %8s %12s %9s"%("group","n","mean %S","t"))
def rep(mask,lbl,mult):
    iv=s20[mask]*math.sqrt(W)*mult
    prem=np.array([straddle_price(1.0,x) for x in iv])
    net=pay[mask]-prem
    se=net.std(ddof=1)/np.sqrt(len(net))
    print("%-46s %8d %+11.4f%% %+9.2f"%(lbl,len(net),100*net.mean(),net.mean()/se))
    return net
for mult,tag in ((1.0,'IV=1.00x realised'),(1.25,'IV=1.25x (25% VRP)')):
    print("--- %s ---"%tag)
    a=rep(el>0.5,"v01T squeeze (band + HV<0.8)",mult)
    b=rep((el<0.5)&(hv<0.8),"CONTROL: HV<0.8 only, NO band",mult)
    cc=rep((el<0.5)&(atband>0.5),"CONTROL: band only, NO HV",mult)
    d=rep(np.ones(len(D),bool),"ALL BARS",mult)
    se=np.sqrt(a.var(ddof=1)/len(a)+b.var(ddof=1)/len(b))
    print("   >>> v01T vs HV-only control: %+.4f%%  t=%+.2f"%(100*(a.mean()-b.mean()),(a.mean()-b.mean())/se))
    print()
