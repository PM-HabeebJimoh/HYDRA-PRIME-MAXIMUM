"""It survives OOS and liquidation. The remaining question is the one I got
wrong in iter41 and caught in iter42: WHAT IS THE NOTIONAL?

At leverage L, capital C controls C*L of notional. Capacity limits NOTIONAL,
not capital. So HIGHER leverage means LESS capital for the same notional -
leverage does NOT increase dollar PnL, it only increases ROI%."""
import numpy as np
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}; FEE=4.0
NOT={'BTC':166767,'NEO':12303,'LTC':2}
def get(nm,sf=0.005):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm); y=np.load('/tmp/ticks/xexy_%s.npy'%nm); t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    k=int(len(p)*sf); sel=np.argsort(-np.abs(p))[:k]; sel=sel[np.argsort(t[sel])]
    return np.sign(p[sel])*y[sel]-(SPREAD[nm]+FEE)*1e-4, t[sel]
print("THE KEY IDENTITY: PnL = NOTIONAL x net_edge x trades. Leverage is absent.")
print()
print("%-5s %6s %12s %11s %10s %13s %14s"%("asset","lev","notional@10%","capital","trades/mo","ROI/mo","PnL/month"))
for nm in ('NEO','LTC','BTC'):
    r,t=get(nm); mo=(t.max()-t.min())/86400.0/30.44; tpm=len(r)/mo
    notional=NOT[nm]*0.10
    for lev in (10,25,50):
        capital=notional/lev
        cap=1.0
        for x in r: cap*=(1.0+lev*x)
        roi=cap**(1/mo)-1 if cap>0 else -1
        pnl=notional*r.mean()*tpm
        print("%-5s %5dx %12s %11s %10.1f %+12.2f%% %14s"%(
            nm,lev,"${:,.0f}".format(notional),"${:,.0f}".format(capital),tpm,100*roi,"${:,.0f}".format(pnl)))
    print()
tot=0
for nm in ('NEO','LTC','BTC'):
    r,t=get(nm); mo=(t.max()-t.min())/86400.0/30.44
    tot+=NOT[nm]*0.10*r.mean()*(len(r)/mo)
print("TOTAL dollar PnL across all 3 assets, ANY leverage: ${:,.0f}/month".format(tot))
print()
print("Leverage changes the DENOMINATOR (capital), never the NUMERATOR (PnL).")
print("50x on NEO = +1234%/mo... on ${:,.0f} of capital = ${:,.0f}/month.".format(
    NOT['NEO']*0.10/50, NOT['NEO']*0.10*get('NEO')[0].mean()*(len(get('NEO')[0])/((get('NEO')[1].max()-get('NEO')[1].min())/86400.0/30.44))))
