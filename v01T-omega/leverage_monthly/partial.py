"""MY OWN BLOCKER: I counted PARTIAL months as months.
OOS starts 2018-11-28 and data ends 2019-11-17. So 2018-11 is ~3 days and
2019-11 is ~17 days. Those are exactly the two 'weakest months' that set my
required leverage. Check it."""
import numpy as np, datetime as dt
for nm in ('NEO','LTC'):
    t=np.load('/tmp/ticks/xext_%s.npy'%nm); p=np.load('/tmp/ticks/xex_%s.npy'%nm)
    v=np.isfinite(p); t=t[v]
    lab=np.array([dt.datetime.utcfromtimestamp(x).strftime('%Y-%m') for x in t])
    print("=== %s ==="%nm)
    for m in sorted(set(lab)):
        tt=t[lab==m]
        d0=dt.datetime.utcfromtimestamp(tt.min()); d1=dt.datetime.utcfromtimestamp(tt.max())
        span=(d1-d0).days+1
        import calendar
        full=calendar.monthrange(d0.year,d0.month)[1]
        flag=" <-- PARTIAL (%d of %d days)"%(span,full) if span<full*0.8 else ""
        print("  %s : %s -> %s  span %2dd of %2dd%s"%(m,d0.date(),d1.date(),span,full,flag))
    print()
