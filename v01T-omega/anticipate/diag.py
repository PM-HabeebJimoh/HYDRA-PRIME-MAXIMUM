"""+11.31%/mo at DD4. Need >700%. Diagnose EXACTLY what binds, via the goal law
ln(1+ROI) = 2*D*Sharpe^2  ->  required monthly Sharpe for 700% = sqrt(ln(8)/0.08)"""
import numpy as np, math
d=np.load('feat.npz',allow_pickle=True)
y=d['y'];t0=d['t0'];t1=d['t1']
oof=np.load('oof.npy'); v=np.isfinite(oof)
y=y[v];t0=t0[v];t1=t1[v];p=oof[v]
mo=(t1.max()-t0.min())/86400000/30.44
need700=math.sqrt(math.log(8.0)/(2*0.04))
need1000=math.sqrt(math.log(11.0)/(2*0.04))
print("required monthly Sharpe @DD4: 700%% -> %.3f   1000%% -> %.3f"%(need700,need1000))
print()
print("%-8s %8s %9s %8s %10s %9s %10s"%("slice","n","tr/mo","meanR","sd","Sharpe_mo","impliedROI"))
for frac in (0.25,0.10,0.05,0.02):
    k=int(len(p)*frac); idx=np.argsort(-p)[:k]
    r=y[idx]; n=len(r); tpm=n/mo
    # monthly Sharpe if trades were independent
    S=r.mean()/r.std(ddof=1)*math.sqrt(tpm)
    roi=math.exp(2*0.04*S*S)-1
    print("top %-4s %8d %8.1f %+7.2f%% %9.2f %9.3f %+9.1f%%"%(
        "%.0f%%"%(100*frac),n,tpm,100*r.mean(),r.std(ddof=1),S,100*roi))
print()
print("^ that assumes INDEPENDENCE. Reality is lower. Measured ROI was +11.31%.")
print()
# what actually limits: measure realized monthly Sharpe from equity
k=int(len(p)*0.10); idx=np.argsort(-p)[:k]; idx=idx[np.argsort(t0[idx])]
r=y[idx]; T0=t0[idx]
mb=((T0-T0.min())/86400000/30.44).astype(int)
ms=[]
for m in range(mb.max()+1):
    s=r[mb==m]
    if len(s)>=10: ms.append(s.mean()*len(s))   # monthly sum of returns
ms=np.array(ms)
print("monthly sum-of-returns: mean %.2f sd %.2f  REALISED monthly Sharpe %.3f"%(
    ms.mean(),ms.std(ddof=1),ms.mean()/ms.std(ddof=1)))
S=ms.mean()/ms.std(ddof=1)
print("=> ROI at DD4 = %.2f%%  (matches the simulation)"%(100*(math.exp(2*0.04*S*S)-1)))
print()
print("GAP ANALYSIS for 700%%:")
print("  have Sharpe %.3f, need %.3f -> %.2fx"%(S,need700,need700/S))
print("  Sharpe ~ sqrt(N_independent) -> need %.1fx more independent trades"%((need700/S)**2))
print("  current %.0f trades/mo -> need %.0f/mo"%(k/mo,(k/mo)*(need700/S)**2))
print()
print("  OR raise per-trade edge by %.2fx at same count"%(need700/S))
