"""The automatic executor must run clean and match the backtest."""

import subprocess
import sys

import pytest

import run_auto


def test_runner_exits_zero_for_every_month():
    """Exit 0 means: parity with the backtest AND goal achieved."""
    assert run_auto.main(["--all", "--quiet"]) == 0


@pytest.mark.parametrize("month", ["jan2026", "jun2026", "jul2026"])
def test_run_month_reports_success(month):
    assert run_auto.run_month(month, quiet=True) is True


def test_runner_needs_no_arguments():
    """`python run_auto.py` with no args must work."""
    r = subprocess.run([sys.executable, "run_auto.py"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "EXACT MATCH" in r.stdout
    assert "ACHIEVED" in r.stdout


def test_runner_uses_the_shared_rule_functions():
    """The executor must not re-implement the rules."""
    src = open("v01t/ve_monitor.py").read()
    assert "from .indicators import" in src
    assert "is_elite(bb, hv, sc)" in src
    assert "from .vol_expansion import LOSS_MULT, WIN_MULT" in src


def test_live_gate_is_the_backtest_gate():
    """Brute force: identical verdict on every real bar of every month."""
    from v01t import spec
    from v01t.dataset import load_month
    from v01t.indicators import (compute_bb_percentile, compute_hv_ratio,
                                 is_elite, score_for)

    for key in ("jan2026", "jun2026", "jul2026"):
        c = load_month(key).closes
        for i in range(spec.HV_MIN_CLOSES, len(c)):
            w = c[: i + 1]
            bb, hv = compute_bb_percentile(w), compute_hv_ratio(w)
            sc = score_for(bb)
            manual = ((bb < spec.BB_LOW or bb > spec.BB_HIGH)
                      and hv < spec.HV_MAX and sc >= spec.SCORE_MIN)
            assert is_elite(bb, hv, sc) == manual


# ---------------------------------------- double entry must be documented ---

def test_spec_declares_double_entry():
    from v01t import spec
    assert spec.DOUBLE_ENTRY is True
    assert spec.LEGS_PER_TRADE == 2


def test_net_edge_derives_from_the_two_legs():
    """+0.45% = winning leg 0.50% minus the stopped leg 0.05%."""
    from v01t import spec
    assert spec.NET_EDGE_PCT == pytest.approx(spec.TP_PCT - spec.STOP_PCT)
    assert spec.WIN_MULTIPLIER == pytest.approx(1.225)


@pytest.mark.parametrize("path", ["v01t/spec.py", "v01t/ve_monitor.py", "HOW_TO_RUN.md"])
def test_double_entry_is_documented(path):
    txt = open(path).read().upper()
    assert "DOUBLE ENTRY" in txt


def test_hedge_mode_requirement_is_stated():
    """Netting accounts would cancel the two legs; this must be flagged."""
    for path in ("v01t/spec.py", "v01t/ve_monitor.py", "HOW_TO_RUN.md"):
        assert "HEDGE" in open(path).read().upper(), path
