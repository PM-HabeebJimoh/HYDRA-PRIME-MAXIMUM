"""Pull real 2026 Bitfinex PERP data via the public API using urllib.
If direct egress is blocked this fails loudly rather than silently faking."""
import json, urllib.request, time, sys, os
PAIRS=['tXLMF0:USTF0','tBTCF0:USTF0','tETHF0:USTF0','tTRXF0:USTF0','tXRPF0:USTF0',
       'tLTCF0:USTF0','tEOSF0:USTF0','tXAUTF0:USTF0','tDOGEF0:USTF0','tSOLF0:USTF0']
TF='1h'
START=1767225600000      # 2026-01-01
END=1798761600000        # 2027-01-01
os.makedirs('/tmp/y26',exist_ok=True)
for p in PAIRS:
    out=[]; cur=START
    nm=p.split(':')[0][1:]
    fn='/tmp/y26/%s_%s.json'%(nm,TF)
    if os.path.exists(fn): print('skip',nm); continue
    while cur<END:
        url=('https://api-pub.bitfinex.com/v2/candles/trade:%s:%s/hist'
             '?start=%d&limit=10000&sort=1'%(TF,p,cur))
        try:
            with urllib.request.urlopen(url,timeout=30) as r:
                d=json.loads(r.read().decode())
        except Exception as e:
            print('FAIL',nm,e); break
        if not isinstance(d,list) or not d: break
        if isinstance(d[0],str): print('ERR',nm,d); break
        out+=d
        last=d[-1][0]
        if last<=cur or len(d)<2: break
        cur=last+1
        time.sleep(0.2)
    if out:
        seen={}; 
        for r in out: seen[r[0]]=r
        rows=[seen[k] for k in sorted(seen)]
        rows=[r for r in rows if START<=r[0]<END]
        json.dump(rows,open(fn,'w'))
        print('%-8s %6d bars'%(nm,len(rows)))
