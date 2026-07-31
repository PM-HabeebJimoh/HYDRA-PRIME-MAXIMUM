"""Out-of-sample: choose config on 2018-2019, test untouched on 2020-2021.
Also per-symbol holdout: tune on 12 symbols, test on the 13th."""
from load import *; from v82 import *
from hybrid import ddsolve
from tune import harvest
import numpy as np, datetime as dt

syms=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
D={}
for s in syms:
    a=load_1m(s)
    if a is None or len(a)<50000: continue
    D[s]=(resample(a,5),resample(a,60))

SPLIT=int(dt.datetime(2020,1,1).timestamp()*1000)
def split_ev(ev):
    return [e for e in ev if e[1]<SPLIT],[e for e in ev if e[0]>=SPLIT]

CFG=[(10,9.9,3.0),(20,9.9,3.0),(30,9.9,3.0),(40,9.9,3.0),(30,9.9,2.0),(40,9.9,2.0)]
print('TIME SPLIT: train <2020, test >=2020 (untouched)')
print('%-18s | %30s | %30s'%('config','TRAIN (2018-2019)','TEST (2020-2021)'))
print('%-18s | %7s %7s %7s %7s | %7s %7s %7s %7s'%('','n','WR%','meanR','ROI','n','WR%','meanR','ROI'))
res=[]
for (b,hv,tm) in CFG:
    ev=[]
    for s,(f,h) in D.items(): ev+=harvest(f,h,b,hv,tm,use_hv=False)
    ev.sort(); tr,te=split_ev(ev)
    a=ddsolve(tr); c=ddsolve(te)
    if not a or not c: continue
    lbl='bb<%d T%.0f'%(b,tm)
    print('%-18s | %7d %7.2f %+7.4f %+6.1f%% | %7d %7.2f %+7.4f %+6.1f%%'%(
        lbl,a['n'],a['wr'],a['meanR'],100*a['roi'],c['n'],c['wr'],c['meanR'],100*c['roi']))
    res.append((a['roi'],lbl,a,c))
res.sort(reverse=True)
w=res[0]
print('\nconfig chosen ONLY on train: %s'%w[1])
print('  its TEST result: WR %.2f%%  meanR %+.4f  ROI %+.2f%%/mo  n=%d'%(w[3]['wr'],w[3]['meanR'],100*w[3]['roi'],w[3]['n']))

print('\nPER-SYMBOL HOLDOUT (config bb<40 T3 fixed, each symbol alone)')
print('%-6s %8s %7s %8s %7s %10s'%('sym','n','WR%','meanR','t','ROI/mo@DD4'))
allr=[]
for s,(f,h) in D.items():
    ev=harvest(f,h,40,9.9,3.0,use_hv=False); ev.sort()
    r=ddsolve(ev)
    if not r: continue
    allr.append(r['meanR'])
    print('%-6s %8d %7.2f %+8.4f %7.1f %+9.2f%%'%(s,r['n'],r['wr'],r['meanR'],r['t'],100*r['roi']))
print('\npositive meanR on %d of %d symbols; median meanR %+.4f'%(sum(1 for x in allr if x>0),len(allr),np.median(allr)))
