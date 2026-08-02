"""BTC: median move 0.03bp but MEAN 0.51bp -> 16x gap. And +0.3386 autocorr
with strong vol clustering. That says BTC is DEAD most minutes and EXPLOSIVE
in bursts. A strategy that trades every minute dies on the spread.
One that trades ONLY the active minutes may not. Test it."""
import json, numpy as np
d=json.load(open('/tmp/krk_btc.json'))
ts=np.array(sorted(int(k) for k in d)); px=np.array([d[str(t)] for t in ts])
r=np.zeros(len(px)); r[1:]=np.log(px[1:]/px[:-1])
i=np.arange(1,len(ts)-1)
g=(ts[i+1]-ts[i]==60)&(ts[i]-ts[i-1]==60)
i2=i[g]
a=np.abs(r[i2]); nxt=np.abs(r[i2+1]); SP=1.649e-4
print("BTCUSD Kraken 2026, n=%d"%len(i2))
print()
print("THE DISTRIBUTION IS THE STORY")
for q in (50,60,70,80,90,95,99):
    print("  p%-3d |move| = %8.4f bp"%(q,1e4*np.percentile(a,q)))
print("  max      = %8.4f bp"%(1e4*a.max()))
print()
print("CONDITIONAL: if THIS minute is active, is the NEXT minute active?")
print("%-28s %8s %14s %12s"%("condition","n","med next |mv|","vs spread"))
for q in (0,50,70,80,90):
    thr=np.percentile(a,q)
    m=a>=thr
    if m.sum()<5: continue
    mn=1e4*np.median(nxt[m])
    print("  %-26s %8d %13.4f %11.2fx"%("this minute >= p%d"%q,m.sum(),mn,mn/(1e4*SP)))
print()
print("BEST CASE: trade only after the top decile of activity")
thr=np.percentile(a,90); m=a>=thr
sel=nxt[m]
print("  n=%d   median next move %.4f bp   mean %.4f bp"%(len(sel),1e4*np.median(sel),1e4*sel.mean()))
print("  spread 1.649 bp -> median ratio %.2fx, mean ratio %.2fx"%(
    1e4*np.median(sel)/1.649, 1e4*sel.mean()/1.649))
print()
print("  Even conditioning on maximum activity, the FOLLOWING minute's")
print("  median move must exceed 1.649bp to pay the round trip.")
