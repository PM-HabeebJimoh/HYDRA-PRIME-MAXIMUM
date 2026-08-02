"""
iter59 / Q2: "Why have you NOT achieved >500% constant monthly ROI?"

Answer it by measurement, not by argument. Run an honest walk-forward direction
model on REAL 2026 bars and report WR / DD / monthly ROI PER INSTRUMENT.

ERA 2026. VENUE: market-data-mirror (Coinbase/Kraken/Yahoo aggregation), real bars.
TIMEFRAME 4h and 1d. MODEL: walk-forward decision stumps, same family as the
2018-19 direction model, retrained every step, strictly causal.
NO synthetic / assumed / dummy data anywhere.
"""
import csv, glob, os, math

DIR = '/tmp/market-data-mirror-main/data'

def load(f):
    rows = list(csv.DictReader(open(f)))
    return [(r['date'], float(r['open']), float(r['high']), float(r['low']), float(r['close'])) for r in rows]

def feats(d, i):
    """Features usable at the CLOSE of bar i. Predict return of bar i+1 (open->close)."""
    c = [x[4] for x in d]; h=[x[2] for x in d]; l=[x[3] for x in d]; o=[x[1] for x in d]
    if i < 21: return None
    r1 = c[i]/c[i-1]-1
    r3 = c[i]/c[i-3]-1
    r10 = c[i]/c[i-10]-1
    rng = (h[i]-l[i])/c[i] if c[i] else 0
    body = (c[i]-o[i])/c[i] if c[i] else 0
    vol10 = math.sqrt(sum((c[j]/c[j-1]-1)**2 for j in range(i-9,i+1))/10)
    vol20 = math.sqrt(sum((c[j]/c[j-1]-1)**2 for j in range(i-19,i+1))/20)
    ma5 = sum(c[i-4:i+1])/5; ma20 = sum(c[i-19:i+1])/20
    return [r1, r3, r10, rng, body, vol10/(vol20+1e-12)-1, c[i]/ma5-1, c[i]/ma20-1, ma5/ma20-1]

NF = 9

def fit_stump(X, y, w):
    """Best single-feature threshold stump minimising weighted error. Returns (f,thr,sign)."""
    best = None
    for f in range(NF):
        vals = sorted(set(x[f] for x in X))
        if len(vals) < 4: continue
        cands = [ (vals[int(p*(len(vals)-1))]) for p in (0.2,0.35,0.5,0.65,0.8) ]
        for thr in cands:
            for sg in (1,-1):
                err = sum(wi for xi,yi,wi in zip(X,y,w)
                          if (sg if xi[f] > thr else -sg) != yi)
                if best is None or err < best[0]:
                    best = (err, f, thr, sg)
    return best

def predict(st, x):
    _, f, thr, sg = st
    return sg if x[f] > thr else -sg

def run(name, d, train=120, tf='4h'):
    """Walk-forward: at each i, train stump ensemble on the last `train` completed
    samples, predict bar i+1. Strictly causal - sample j uses feats(j) and outcome j+1,
    and we only include j+1 <= i."""
    rows = []
    for i in range(21, len(d)-1):
        F = feats(d, i)
        if F is None: continue
        nxt = d[i+1][4]/d[i+1][1] - 1     # enter at NEXT bar's OPEN, exit at its CLOSE
        rows.append((i, F, nxt))
    if len(rows) < train + 30: return None

    trades = []
    for k in range(train, len(rows)):
        tr = rows[max(0,k-train):k-1]      # k-1: outcome of sample k-1 needs bar k, unknown
        X=[r[1] for r in tr]; y=[1 if r[2]>0 else -1 for r in tr]
        if len(set(y))<2: continue
        w=[1.0]*len(X)
        ens=[]
        for _ in range(3):                                  # 3-round boosting
            st=fit_stump(X,y,w)
            if st is None: break
            err=st[0]/sum(w)
            err=min(max(err,1e-6),1-1e-6)
            a=0.5*math.log((1-err)/err)
            ens.append((a,st))
            w=[wi*math.exp(-a*yi*predict(st,xi)) for xi,yi,wi in zip(X,y,w)]
            s=sum(w); w=[x/s*len(w) for x in w]
        if not ens: continue
        score=sum(a*predict(st,rows[k][1]) for a,st in ens)
        if score==0: continue
        sig = 1 if score>0 else -1
        trades.append((rows[k][0], sig, sig*rows[k][2], d[rows[k][0]+1][0]))
    return trades

def report(name, trades, tf):
    if not trades: 
        print(f"{name:<12} -- insufficient"); return
    rets=[t[2] for t in trades]
    wr=100*sum(1 for r in rets if r>0)/len(rets)
    eq=1.0; peak=1.0; dd=0.0
    for r in rets:
        eq*= (1+r); peak=max(peak,eq); dd=max(dd,(peak-eq)/peak)
    total=(eq-1)*100
    bpm = 180 if tf=='4h' else 30.4
    months=len(trades)/bpm
    mo = ((eq)**(1/months)-1)*100 if months>0 and eq>0 else -100
    mean_bp = sum(rets)/len(rets)*10000
    print(f"{name:<12} n={len(trades):>4}  WR={wr:>5.2f}%  DD={dd*100:>6.2f}%  "
          f"ROI/mo={mo:>9.2f}%  edge={mean_bp:>8.2f}bp  total={total:>10.1f}%")
    return wr, dd*100, mo, mean_bp

print("="*94)
print("ERA 2026 | REAL BARS | WALK-FORWARD DIRECTION MODEL | GROSS (zero cost, best case)")
print("="*94)
res={}
for f in sorted(glob.glob(f'{DIR}/*_4h.csv')):
    name=os.path.basename(f).replace('_4h.csv','')
    d=load(f)
    if len(d)<200: continue
    t=run(name,d,train=120,tf='4h')
    if t: res[name+'_4h']=(report(name+' 4h',t,'4h'), t)
print()
for f in sorted(glob.glob(f'{DIR}/*_1d.csv')):
    name=os.path.basename(f).replace('_1d.csv','')
    d=[x for x in load(f) if x[0][:4] in ('2025','2026')]
    if len(d)<250: continue
    t=run(name,d,train=150,tf='1d')
    if t: res[name+'_1d']=(report(name+' 1d',t,'1d'), t)

print()
print("="*94)
print("MONTHLY BREAKDOWN, best series by edge (2026, gross)")
print("="*94)
if res:
    best=max(res.items(), key=lambda kv: kv[1][0][3] if kv[1][0] else -1e9)
    nm, ((wr,dd,mo,ed), trades) = best
    print(f"series: {nm}   overall edge {ed:.2f}bp")
    bym={}
    for _,sig,r,dt in trades:
        bym.setdefault(dt[:7],[]).append(r)
    print(f"{'month':<9} {'n':>4} {'WR':>7} {'ROI':>12} {'>=5000%?':>9}")
    for m in sorted(bym):
        rr=bym[m]; e=1.0
        for r in rr: e*=(1+r)
        w=100*sum(1 for r in rr if r>0)/len(rr)
        print(f"{m:<9} {len(rr):>4} {w:>6.2f}% {(e-1)*100:>11.2f}% {'YES' if (e-1)*100>=5000 else 'no':>9}")
