"""
Instrument registry helper
"""
import config

class InstrumentRegistry:
    def __init__(self):
        self.instruments = config.INSTRUMENTS

    def get_all(self):
        return list(self.instruments.keys())

    def get_by_type(self, t):
        return [k for k,v in self.instruments.items() if v.get("type")==t]

    def count(self):
        return len(self.instruments)

    def summary(self):
        from collections import Counter
        types = Counter([v.get("type") for v in self.instruments.values()])
        return dict(types)
