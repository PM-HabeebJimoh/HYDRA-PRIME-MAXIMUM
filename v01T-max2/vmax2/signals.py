"""Signal definitions measured on real bars. Nothing here is fitted to the future."""
from .ohlc import stdev

def make(bars):
    C = [b['c'] for b in bars]

    def bb_pct(i, w=20):
        if i < w: return None
        sd, m = stdev(C[i-w+1:i+1], pop=True)
        return None if sd == 0 else (C[i] - (m - 2*sd)) / (4*sd) * 100

    def hv_ratio(i, short=10, long=30):
        if i < long + 1: return None
        r = [(C[k]-C[k-1])/C[k-1] for k in range(i-long+1, i+1)]
        a, _ = stdev(r[-short:], pop=False); b, _ = stdev(r, pop=False)
        return a/b if b else None

    def momentum(i, k):
        return None if i < k else (C[i]-C[i-k])/C[i-k]

    return dict(
        all        = lambda i: True,
        lowvol     = lambda i: (lambda h: h is not None and h < 0.7)(hv_ratio(i)),
        mom24      = lambda i: (lambda m: m is not None and m > 0)(momentum(i, 24)),
        bblow      = lambda i: (lambda x: x is not None and x < 10)(bb_pct(i)),
        v01t_gate  = lambda i: (lambda x, h: x is not None and h is not None
                                and (x < 10 or x > 90) and h < 0.8)(bb_pct(i), hv_ratio(i)),
        lowvol_mom = lambda i: (lambda h, m: h is not None and m is not None
                                and h < 0.7 and m > 0)(hv_ratio(i), momentum(i, 24)),
    ), bb_pct, hv_ratio, momentum
