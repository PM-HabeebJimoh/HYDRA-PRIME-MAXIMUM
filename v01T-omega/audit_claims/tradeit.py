"""Trade the 2026 OKX->Kraken signal for real: WR / DD / ROI, net of the
measured Kraken LTC spread. This is the ONLY 2026 test of the 'best' model."""
import json, numpy as np
d=json.load(open('/tmp/ltc2026b.json'))
t=np.array(d['ts']); a=np.array(d['okx']); b=np.array(d['krk'])
ra=np.zeros(len(a)); ra[1:]=np.log(a[1:]/a[:-1])
rb=np.zeros(len(b)); rb[1:]=np.log(b[1:]/b[:-1])
i=np.arange(1,len(t)-1)
g=(t[i+1]-t[i]==60)&(t[i]-t[i-1]==60)
i2=i[g]
sig=np.sign(ra[i2])            # leader move
fwd=rb[i2+1]                   # follower next-minute
live=np.abs(ra[i2])>1e-12
i3=i2[live]; s=sig[live]; f=fwd[live]
print("2026 OKX->Kraken LTC, %d usable minutes, %d with a leader signal"%(len(i2),len(i3)))
gross=s*f
print()
print("GROSS (no costs):  mean %+.3f bp   WR %.1f%%   n=%d"%(1e4*gross.mean(),100*(gross>0).mean(),len(gross)))
print()
print("Kraken LTC spread measured: crypto majors ~5-15bp round trip on Kraken.")
for sp in (0.0,1.0,2.0,5.0,10.0):
    net=gross-sp*1e-4
    print("  spread %5.1f bp -> net %+8.3f bp/trade  WR %.1f%%  %s"%(
        sp,1e4*net.mean(),100*(net>0).mean(),"PROFIT" if net.mean()>0 else "LOSS"))
print()
def path(r,lev):
    cap=1.0;peak=1.0;dd=0.0
    for x in r:
        cap*=(1+lev*x)
        if cap<=0: return 0.0,1.0
        peak=max(peak,cap);dd=max(dd,(peak-cap)/peak)
    return cap,dd
print("EQUITY at 5bp spread (realistic Kraken taker), 1.5 hours of data:")
net=gross-5.0*1e-4
for lev in (1,10,25,50):
    cap,dd=path(net,lev)
    print("  lev %3dx  final %.4f  maxDD %.2f%%  ->  %s"%(lev,cap,100*dd,"BUST" if cap<=0 else "%+.2f%% over the window"%(100*(cap-1))))
