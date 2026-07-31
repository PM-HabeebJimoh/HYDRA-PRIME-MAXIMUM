import json,sys,os,re,datetime as dt
def ingest(key,text):
    """Bitstamp: {"timestamp","open","high","low","close","volume"} objects."""
    objs=re.findall(r'\{"timestamp":\s*"(\d+)",\s*"open":\s*"([\d.]+)",\s*"high":\s*"([\d.]+)",\s*"low":\s*"([\d.]+)",\s*"close":\s*"([\d.]+)"',text)
    p=f"raw/{key}.json"; store=json.load(open(p)) if os.path.exists(p) else {}
    for t,o,h,l,c in objs:
        store[str(int(t))]=[float(l),float(h),float(o),float(c)]
    json.dump(store,open(p,"w"))
    return len(objs)
def report(key,step):
    store=json.load(open(f"raw/{key}.json"))
    ts=sorted(int(k) for k in store)
    f=lambda x: dt.datetime.utcfromtimestamp(x).strftime("%Y-%m-%d %H:%M")
    gaps=[(f(a),f(b)) for a,b in zip(ts,ts[1:]) if b-a!=step]
    print(f"{key}: {len(ts)} bars  {f(ts[0])} -> {f(ts[-1])}  gaps {len(gaps)}")
    if gaps: print("    first gaps:",gaps[:5])
