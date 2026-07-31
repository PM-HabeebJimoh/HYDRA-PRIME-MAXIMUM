import json,sys,os,re,datetime as dt
# Bitfinex: [MTS, OPEN, CLOSE, HIGH, LOW, VOL]
key=sys.argv[1]; step=int(sys.argv[2])
txt=sys.stdin.read()
rows=re.findall(r'\[(\d{13}),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),',txt)
p=f"raw/{key}.json"; store=json.load(open(p)) if os.path.exists(p) else {}
for ms,o,c,h,l in rows:
    t=int(ms)//1000
    store[str(t)]=[float(l),float(h),float(o),float(c)]
json.dump(store,open(p,"w"))
ts=sorted(int(k) for k in store)
f=lambda x: dt.datetime.utcfromtimestamp(x).strftime("%Y-%m-%d %H:%M")
gaps=[(f(a),f(b)) for a,b in zip(ts,ts[1:]) if b-a!=step]
print(f"+{len(rows)} -> {key}: {len(ts)} bars  {f(ts[0])} -> {f(ts[-1])}  gaps {len(gaps)}")
if gaps: print("   ",gaps[:4])
