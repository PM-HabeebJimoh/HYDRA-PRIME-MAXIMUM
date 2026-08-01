"""THE REPLACEMENT: stop being a price TAKER. Become the LIQUIDITY PROVIDER.

Every model in 39 iterations asked: "predict direction, then CROSS the spread."
Result, always: gross edge slightly SMALLER than the toll.
  iter39 NEO: +35.28bp gross vs 40bp taker = -4.72bp. 88% of cost recovered.

INVERT IT. The spread is not a cost to be beaten - it is REVENUE to be collected.
A market maker EARNS the spread on every round trip instead of paying it.
That is a +80bp swing on NEO (stop paying 40, start earning 40).

The reason market making fails is ADVERSE SELECTION: you get filled by informed
traders right before price moves against you. That is precisely, exactly, the
thing my 87%-accurate cross-exchange model predicts.

So the 87% signal is NOT a trading signal. It is an ADVERSE SELECTION FILTER.
  - model says price about to RISE  -> quote the BID (buy cheap, don't sell)
  - model says price about to FALL  -> quote the ASK (sell rich, don't buy)
  - model uncertain                 -> quote BOTH (pure spread capture)
  - model says violent move         -> QUOTE NOTHING (step aside)

HONEST FILL SIMULATION from real executions with aggressor flags:
  my resting BID at price P fills only if a SELLER-aggressor print occurs at
  price <= P. That seller crossed to hit my bid. Conservative: require the
  print to trade strictly THROUGH my quote, so I am never assumed to win a
  queue race at the touch.
"""
import numpy as np, zipfile, csv, io, glob, sys, os

def load_day(path):
    z=zipfile.ZipFile(path); name=z.namelist()[0]
    ts=[];px=[];qty=[];sa=[]
    with z.open(name) as fh:
        rd=csv.reader(io.TextIOWrapper(fh,'utf-8')); next(rd,None)
        for row in rd:
            if len(row)<5: continue
            try: ts.append(float(row[1]));px.append(float(row[2]));qty.append(float(row[3]))
            except ValueError: continue
            sa.append(row[4].strip().lower()=='true')
    if not ts: return None
    a=np.argsort(np.array(ts))
    return np.array(ts)[a],np.array(px)[a],np.array(qty)[a],np.array(sa)[a]

def simulate(path, half_spread_bp, skew_fn=None, max_inv=5.0, fee_bp=0.0):
    """Post two-sided quotes each minute; hold inventory; mark to market.
    Returns per-minute pnl decomposition."""
    d=load_day(path)
    if d is None: return None
    ts,px,qty,sa=d
    unit=1000.0 if ts.max()>2e10 else 1.0
    T=ts/unit
    m=np.floor(T/60.0).astype(np.int64)
    um,first=np.unique(m,return_index=True)
    if len(um)<60: return None
    grp=np.split(np.arange(len(T)),first[1:])
    inv=0.0; cash=0.0; rows=[]
    for gi,g in enumerate(grp):
        p=px[g]; q=qty[g]; s=sa[g]      # s True => SELLER aggressor (hits bids)
        mid=p[0]
        hs=mid*half_spread_bp*1e-4
        bid=mid-hs; ask=mid+hs
        skew=0.0
        if skew_fn is not None: skew=skew_fn(gi)
        # skew: +1 => only bid (want to buy), -1 => only ask, 0 => both
        want_bid = skew>=-0.5
        want_ask = skew<=0.5
        # inventory limits
        if inv>=max_inv: want_bid=False
        if inv<=-max_inv: want_ask=False
        filled_b=0.0; filled_a=0.0
        # conservative: fill only when a print trades strictly THROUGH the quote
        if want_bid:
            hit = s & (p < bid)
            filled_b = min(qty[g][hit].sum(), 1.0) if hit.any() else 0.0
        if want_ask:
            lift = (~s) & (p > ask)
            filled_a = min(qty[g][lift].sum(), 1.0) if lift.any() else 0.0
        if filled_b>0:
            cash-= filled_b*bid*(1+fee_bp*1e-4); inv+=filled_b
        if filled_a>0:
            cash+= filled_a*ask*(1-fee_bp*1e-4); inv-=filled_a
        close=p[-1]
        rows.append((um[gi]*60.0, cash+inv*close, inv, filled_b, filled_a, close, mid))
    return np.array(rows)

if __name__=='__main__':
    SYM=sys.argv[1] if len(sys.argv)>1 else 'NEOUSDT'
    files=sorted(glob.glob('/tmp/ticks/cryptocurrency-ticks-data-master/data/%s/*.zip'%SYM))[:120]
    print("=== %s : PASSIVE MARKET MAKING, %d days, NO directional filter ==="%(SYM,len(files)))
    print("%-10s %10s %12s %12s %10s"%("half-spr","days","tot fills","pnl/day","pnl/fill(bp)"))
    for hs in (5.0,10.0,20.0,40.0):
        tot=0.0; nf=0; nd=0; px0=None
        for f in files:
            r=simulate(f,hs)
            if r is None or len(r)<60: continue
            pnl=r[-1,1]-r[0,1]
            tot+=pnl; nf+=r[:,3].sum()+r[:,4].sum(); nd+=1
            if px0 is None: px0=r[0,5]
        if nd==0: continue
        bp=1e4*(tot/max(nf,1))/max(px0,1e-9)
        print("%-10.1f %10d %12.1f %12.4f %10.2f"%(hs,nd,nf,tot/nd,bp))
