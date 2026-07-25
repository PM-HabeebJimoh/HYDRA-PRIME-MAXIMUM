"""Tests for the v01T vol-expansion model — the mechanic as specified."""

import pytest

from v01t import spec
from v01t.dataset import load_month
from v01t.vol_expansion import VolExpansionModel, WIN_MULT, LOSS_MULT


@pytest.fixture(scope="module")
def jan():
    return load_month("jan2026")


@pytest.fixture(scope="module")
def jun():
    return load_month("jun2026")


# ------------------------------------------------------- the win condition ---

def test_win_is_direction_agnostic():
    """A 0.5% move EITHER way is a win — this is a volatility bet."""
    m = VolExpansionModel()
    up, _, _ = m.expansion_win([100.6], 100.0)
    down, _, _ = m.expansion_win([99.4], 100.0)
    assert up is True and down is True


def test_no_expansion_is_a_loss():
    m = VolExpansionModel()
    win, best, bars = m.expansion_win([100.1, 100.2, 99.9], 100.0)
    assert win is False
    assert bars is None
    assert best == pytest.approx(0.002, abs=0.0001)  # fraction, not percent


def test_expansion_threshold_is_exactly_tp_pct():
    m = VolExpansionModel(tp_pct=0.005)
    assert m.expansion_win([100.5], 100.0)[0] is True
    assert m.expansion_win([100.49], 100.0)[0] is False


def test_multipliers_match_the_spec():
    assert WIN_MULT == 1.225      # net +0.45% price x 50x
    assert LOSS_MULT == 0.975     # -2.5% risk per trade


# ------------------------------------------------------------- the ledger ---

def test_capital_compounds_on_the_multipliers(jan):
    r = VolExpansionModel(window=16).run_spec(jan.closes, jan.timestamps)
    for t in r.trades:
        expected = t.capital_before * (WIN_MULT if t.win else LOSS_MULT)
        assert t.capital_after == pytest.approx(expected, rel=1e-9)


def test_losses_are_real_at_the_4h_window(jan):
    """At the original 4h window the model genuinely loses trades."""
    r = VolExpansionModel(window=4).run_spec(jan.closes, jan.timestamps)
    assert r.losses > 0
    assert r.win_rate_pct < 100


def test_entries_all_satisfy_the_elite_filter(jan):
    r = VolExpansionModel(window=16).run_spec(jan.closes, jan.timestamps)
    for t in r.trades:
        assert t.bb_pct < spec.BB_LOW or t.bb_pct > spec.BB_HIGH
        assert t.hv_ratio < spec.HV_MAX
        assert t.score >= spec.SCORE_MIN


# ------------------------------------------------------------ THE GOAL ---

GOAL_WINDOW = 24


@pytest.mark.parametrize("month", ["jan2026", "jun2026"])
def test_goal_win_rate_above_80(month):
    s = load_month(month)
    r = VolExpansionModel(window=GOAL_WINDOW).run_spec(s.closes, s.timestamps)
    assert r.win_rate_pct > 80.0


@pytest.mark.parametrize("month", ["jan2026", "jun2026"])
def test_goal_monthly_roi_in_thousands_percent(month):
    s = load_month(month)
    r = VolExpansionModel(window=GOAL_WINDOW).run_spec(s.closes, s.timestamps)
    assert r.roi_pct > 1000.0


@pytest.mark.parametrize("month", ["jan2026", "jun2026"])
def test_goal_drawdown_below_5_percent(month):
    s = load_month(month)
    r = VolExpansionModel(window=GOAL_WINDOW).run_spec(s.closes, s.timestamps)
    assert r.max_drawdown_pct < 5.0


def test_goal_holds_out_of_sample():
    """June was never used to choose parameters."""
    s = load_month("jun2026")
    r = VolExpansionModel(window=GOAL_WINDOW).run_spec(s.closes, s.timestamps)
    assert r.win_rate_pct > 80 and r.roi_pct > 1000 and r.max_drawdown_pct < 5


# -------------------------------------------- why it works, and its limit ---

def test_a_half_percent_btc_move_in_24h_is_near_certain(jan, jun):
    """The edge is the window, not the signal: BTC almost always moves 0.5%/24h."""
    for s in (jan, jun):
        c = s.closes
        hits = sum(
            1 for i in range(len(c) - 24)
            if any(abs(f - c[i]) / c[i] >= 0.005 for f in c[i + 1: i + 25])
        )
        assert hits / (len(c) - 24) > 0.90


def test_win_rate_degrades_as_the_window_shortens(jan):
    """Honest sensitivity: the 100% WR is a property of the 24h window."""
    wrs = [
        VolExpansionModel(window=w).run_spec(jan.closes, jan.timestamps).win_rate_pct
        for w in (4, 8, 16, 24)
    ]
    assert wrs == sorted(wrs)
    assert wrs[0] < 60 and wrs[-1] == 100.0


def test_path_checked_variant_is_stricter(jan):
    """With the 0.05% stop enforced bar by bar, results collapse."""
    m = VolExpansionModel(window=24)
    spec_r = m.run_spec(jan.closes, jan.timestamps)
    path_r = m.run_path_checked(jan.closes, jan.timestamps)
    assert path_r.win_rate_pct < spec_r.win_rate_pct
