"""Parse Bitfinex liquidation prints saved from fetch_page into JSON."""
import re,json,sys
txt=open('/tmp/liq_raw.txt').read()
# each record: ["pos", ID, MTS, null, "SYMBOL", AMOUNT, BASE_PRICE, null, IS_MATCH, IS_MARKET_SOLD, null, PRICE_ACQUIRED]
pat=re.compile(r'\["pos",(\d+),(\d{13}),null,"([^"]+)",(-?[\d.eE+-]+),([\d.eE+-]+),null,(\d),(\d),null,([\d.eE+-]+|null)\]')
rows=[]
for m in pat.finditer(txt):
    _id,mts,sym,amt,base,ismatch,ismkt,acq=m.groups()
    rows.append(dict(id=int(_id),mts=int(mts),sym=sym,amt=float(amt),
                     base=float(base),is_match=int(ismatch),is_mkt=int(ismkt),
                     acq=(None if acq=='null' else float(acq))))
seen=set();u=[]
for r in rows:
    k=(r['id'],r['mts'],r['amt'])
    if k in seen: continue
    seen.add(k);u.append(r)
json.dump(u,open('/tmp/liq.json','w'))
print("records",len(u))
from collections import Counter
c=Counter(r['sym'] for r in u)
for s,n in c.most_common(12): print(f"  {s:<22} {n}")
