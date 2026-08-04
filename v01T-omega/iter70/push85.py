"""
iter70d: The grid found ZERO configs at WR>=85%, but 295 with positive skill
AND net-positive after costs (best: LTCBTC flow_fast 400/200 N720, edge +18.70,
netR +0.2096, p_bonf < 1e-5).

Now answer the user's question directly: CAN we reach 85% WR?
Geometry says yes - P(win)=b/(a+b), so b/(a+b)=0.85 needs b/a = 5.67.
Test extreme asymmetric barriers with the REAL signal on top, and check whether
the observed WR beats the free baseline AND stays net-positive.

This is the decisive test: if the best real edge (+18.7 points) is applied to a
geometry whose baseline is 85%, we would land at ~100%. If instead WR collapses
to the baseline, the edge does not survive at that geometry.
"""
import numpy as np, os, math, json
exec(open('/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/iter70/fast.py').read().split("COST=")[0])
COST={'BTCUSDT':5.65,'LTCBTC':5.15}
# geometries with high FREE baseline
BAR=[(50,300),(40,280),(60,340),(30,270),(100,600),(50,450),(80,720),(20,340),
     (60,540),(40,360),(100,900),(25,475)]
TOPS=[0.02,0.01,0.005,0.002]
HOR=[240,720]
SIGS=['flow_fast','flow','multiscale','conc','flow_tfi']
out=[]
HUB=load('BTCUSDT'); hubz=np.nan_to_num(z(HUB['ofi'],240))
for sym in ('LTCBTC','BTCUSDT'):
    if not os.path.exists('/tmp/ticks/ohlc_%s.npy'%sym): continue
    D=load(sym); n=len(D['c']); cut=int(n*0.6)
    hub=None
    if sym!='BTCUSDT':
        _,ia,ib=np.intersect1d(D['ts'],HUB['ts'],return_indices=True)
        hh=np.zeros(n); hh[ia]=hubz[ib]; hub=hh
    S=build_signals(D,hub)
    for (t,s) in BAR:
        for N in HOR:
            RL,BL=outcomes(D['o'],D['h'],D['l'],D['c'],D['ts'],t,s,N,+1)
            RS,BS=outcomes(D['o'],D['h'],D['l'],D['c'],D['ts'],t,s,N,-1)
            for nm in SIGS:
                if nm not in S: continue
                sg=np.nan_to_num(S[nm]); av=np.abs(sg)
                trv=av[:cut]; trv=trv[np.isfinite(trv)&(trv>0)]
                if len(trv)<1000: continue
                for tf in TOPS:
                    thr=np.quantile(trv,1-tf)
                    mask=(av>=thr); mask[:1000]=False
                    Ru=np.where(sg>0,RL,RS); Bu=np.where(sg>0,BL,BS)
                    sel=sweep(mask,Ru,Bu); sel=sel[sel>=cut]
                    if len(sel)<200: continue
                    R=Ru[sel]; net=R-COST[sym]/s
                    wr=100*(R>0).mean(); base=100*s/(t+s)
                    out.append(dict(sym=sym,sig=nm,tgt=t,stp=s,N=N,top=tf,
                        n=int(len(sel)),wr=wr,base=base,edge=wr-base,
                        netR=float(net.mean()),totR=float(net.sum())))
print("="*100)
print("PUSH TO 85%: extreme asymmetric barriers (high free baseline) + best real signals")
print("="*100)
print(f"{'sym':<9}{'sig':<12}{'tgt':>5}{'stp':>5}{'N':>6}{'top':>7}{'n':>6}{'WR%':>8}{'base%':>8}{'EDGE':>8}{'netR':>9}")
hi=[r for r in out if r['wr']>=85]
for r in sorted(out,key=lambda x:-x['wr'])[:20]:
    print(f"{r['sym']:<9}{r['sig']:<12}{r['tgt']:>5}{r['stp']:>5}{r['N']:>6}{r['top']:>7.3f}"
          f"{r['n']:>6}{r['wr']:>7.2f}%{r['base']:>7.2f}%{r['edge']:>+8.2f}{r['netR']:>+9.4f}")
print()
print(f"configs reaching WR>=85%: {len(hi)}")
pos=[r for r in hi if r['edge']>0]; posn=[r for r in hi if r['netR']>0]
print(f"  with positive skill    : {len(pos)}")
print(f"  net-positive after cost: {len(posn)}")
if posn:
    print("  >>> BOTH 85%+ AND PROFITABLE:")
    for r in sorted(posn,key=lambda x:-x['netR'])[:10]:
        print(f"    {r['sym']} {r['sig']} {r['tgt']}/{r['stp']} N{r['N']} top{r['top']} n={r['n']} "
              f"WR={r['wr']:.2f}% base={r['base']:.2f}% edge={r['edge']:+.2f} netR={r['netR']:+.4f}")
json.dump(out,open('/tmp/push85.json','w'))
