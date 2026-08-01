"""80%+ reached. Now: is it STABLE, and does it SURVIVE THE SPREAD?
Bitfinex taker = 20bp/side historically; but a limit/maker fill = 0-10bp.
Test both. Also per-month stability."""
import numpy as np
for bf,sp_taker in (('NEO',40.0),('LTC',40.0),('BTC',40.0)):
    try:
        p=np.load('/tmp/ticks/xex_%s.npy'%bf); y=np.load('/tmp/ticks/xexy_%s.npy'%bf); t=np.load('/tmp/ticks/xext_%s.npy'%bf)
    except Exception: continue
    v=np.isfinite(p); pv=p[v];yv=y[v];tv=t[v]
    mb=((tv-tv.min())/86400.0/30.44).astype(int)
    print()
    print("=== %s ==="%bf)
    print("PER-MONTH at top 1%%:")
    accs=[];bps=[]
    for m in range(mb.max()+1):
        z=mb==m
        if z.sum()<3000: continue
        p2=pv[z];y2=yv[z]
        k=max(20,int(len(p2)*0.01))
        sel=np.argsort(-np.abs(p2))[:k]
        a=100*(np.sign(p2[sel])==np.sign(y2[sel])).mean()
        b=1e4*(np.sign(p2[sel])*y2[sel]).mean()
        accs.append(a);bps.append(b)
        print("   m%-3d n=%6d ACC %6.2f%%  %+8.2f bp"%(m,z.sum(),a,b))
    accs=np.array(accs);bps=np.array(bps)
    if len(accs):
        print("   mean ACC %.2f%%  min %.2f%%  months>=80%%: %d/%d  mean bp %+.2f"%(
            accs.mean(),accs.min(),(accs>=80).sum(),len(accs),bps.mean()))
    print("NET OF COST:")
    print("   %-10s %8s %8s %10s %10s %10s"%("slice","n","ACC","gross","net@0bp","net@40bp"))
    for fr in (0.02,0.01,0.005,0.002,0.001):
        k=max(50,int(len(pv)*fr))
        sel=np.argsort(-np.abs(pv))[:k]
        acc=100*(np.sign(pv[sel])==np.sign(yv[sel])).mean()
        g=1e4*(np.sign(pv[sel])*yv[sel]).mean()
        print("   top %-6s %8d %7.2f%% %+9.3f %+9.3f %+9.3f %s"%(
            "%.1f%%"%(100*fr),k,acc,g,g,g-sp_taker,"PROFIT@taker" if g>sp_taker else ""))
