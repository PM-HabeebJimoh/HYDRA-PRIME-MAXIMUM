"""The 2026 signal looks STRONG. Before believing it: is n=88 enough?
Bootstrap and significance-test it properly."""
import json, numpy as np
d=json.load(open('/tmp/ltc2026.json'))
t=np.array(d['ts']); a=np.array(d['okx']); b=np.array(d['krk'])
ra=np.zeros(len(a)); ra[1:]=np.log(a[1:]/a[:-1])
rb=np.zeros(len(b)); rb[1:]=np.log(b[1:]/b[:-1])
idx=np.arange(1,len(t)-1)
g=(t[idx+1]-t[idx]==60)&(t[idx]-t[idx-1]==60)
i2=idx[g]
x=ra[i2]; ynext=rb[i2+1]
n=len(x)
c=np.corrcoef(x,ynext)[0,1]
# t-stat for a correlation
tstat=c*np.sqrt((n-2)/(1-c*c))
print("OKX(t) -> Kraken(t+1): corr %+.4f  n=%d  t=%.2f"%(c,n,tstat))
rng=np.random.default_rng(0)
bs=np.array([np.corrcoef(*np.array([(x[i],ynext[i]) for i in rng.integers(0,n,n)]).T)[0,1] for _ in range(2000)])
print("bootstrap 95%% CI: %+.4f to %+.4f"%(np.percentile(bs,2.5),np.percentile(bs,97.5)))
print("P(corr<=0) = %.4f"%(bs<=0).mean())
print()
# directional accuracy CI
nz=(np.abs(x)>1e-9)&(np.abs(ynext)>1e-9)
hit=(np.sign(x[nz])==np.sign(ynext[nz]))
k=hit.sum(); N=nz.sum()
p=k/N
se=np.sqrt(p*(1-p)/N)
print("directional accuracy %.2f%%  (%d of %d)"%(100*p,k,N))
print("95%% CI: %.1f%% to %.1f%%"%(100*(p-1.96*se),100*(p+1.96*se)))
print()
print("SAMPLE SIZE REALITY")
print("  2018-19 model: 253,036 OOS observations")
print("  this 2026 test:      %d observations, %d directional"%(n,N))
print("  ratio: %.0f x smaller"%(253036/n))
print()
print("VERDICT: the SIGN and STRUCTURE match 2018-19 (leader->follower asymmetry")
print("26.7x, dislocation mean-reverts). But n=%d cannot support a monthly ROI"%N)
print("claim. It is 1.5 hours of data, not a backtest.")
