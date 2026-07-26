/* ==========================================================================
   v01T Terminal — application controller
   Vanilla ES2019, no build step, no dependencies. Progressive enhancement:
   the server renders the shell and static figures; this layer adds routing,
   live polling and interaction.
   ========================================================================== */
(function () {
  "use strict";

  /* ------------------------------------------------------------- helpers */
  var $  = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  function fmt(n, d) {
    if (n === null || n === undefined || isNaN(n)) return "—";
    return Number(n).toLocaleString(undefined, {
      minimumFractionDigits: d === undefined ? 0 : d,
      maximumFractionDigits: d === undefined ? 0 : d
    });
  }
  function money(n) { return "$" + fmt(n, 2); }
  function pct(n, d) { return fmt(n, d === undefined ? 2 : d) + "%"; }
  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function api(path) {
    return fetch(path, { headers: { Accept: "application/json" } })
      .then(function (r) {
        if (!r.ok) throw new Error(path + " → HTTP " + r.status);
        return r.json();
      });
  }

  function rowsInto(tbody, html, colspan, emptyMsg) {
    if (!tbody) return;
    tbody.innerHTML = html || '<tr><td colspan="' + colspan + '">' +
      '<div class="empty"><div class="empty-icon">◌</div><span>' +
      esc(emptyMsg || "No data yet") + "</span></div></td></tr>";
  }

  function goalBadge(g) {
    var ok = g && (g.all_passed !== undefined ? g.all_passed
      : (g.wr_above_80 && g.roi_thousands_pct && g.dd_below_5));
    return ok ? '<span class="badge pass">pass</span>'
              : '<span class="badge fail">fail</span>';
  }

  /* --------------------------------------------------------------- toast */
  function toast(msg, kind) {
    var host = $("#toasts");
    if (!host) return;
    var el = document.createElement("div");
    el.className = "toast" + (kind ? " " + kind : "");
    el.textContent = msg;
    host.appendChild(el);
    setTimeout(function () {
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 200);
    }, 3600);
  }

  /* -------------------------------------------------------------- router */
  var TITLES = {
    overview: "Overview", backtest: "Backtest", trades: "Trade Ledger",
    signals: "Signals", monitor: "Live Monitor", execution: "Auto Trading",
    risk: "Risk & Sizing", model: "Model Spec", api: "API & Health"
  };
  var loaded = {};

  function show(view) {
    if (!TITLES[view]) view = "overview";
    $$(".view").forEach(function (v) { v.classList.remove("active"); });
    var el = $("#view-" + view);
    if (el) el.classList.add("active");

    $$(".nav-item").forEach(function (b) {
      var on = b.dataset.view === view;
      if (on) { b.setAttribute("aria-current", "page"); }
      else { b.removeAttribute("aria-current"); }
    });

    var t = $("#viewTitle");
    if (t) t.textContent = TITLES[view];
    document.title = "v01T Terminal — " + TITLES[view];
    if (location.hash.slice(1) !== view) history.replaceState(null, "", "#" + view);

    $("#rail").classList.remove("open");
    var main = $("#main"); if (main) main.scrollTop = 0;

    if (!loaded[view]) { loaded[view] = true; hydrate(view); }
  }

  $$(".nav-item").forEach(function (b) {
    b.addEventListener("click", function () { show(b.dataset.view); });
  });
  window.addEventListener("hashchange", function () { show(location.hash.slice(1)); });

  /* ------------------------------------------------------------ hydrate */
  function hydrate(view) {
    if (view === "overview") loadOverview();
    if (view === "backtest") loadBacktest();
    if (view === "trades")   loadTrades();
    if (view === "signals")  loadSignals();
    if (view === "monitor")  loadMonitor();
    if (view === "execution") loadExecution();
    if (view === "risk")     { loadCosts(); calcSize(); }
    if (view === "api")      loadHealth();
  }

  function monthRow(x, withWL) {
    return "<tr><td><strong>" + esc(x.month) + "</strong></td>" +
      '<td class="num mono">' + fmt(x.bars) + "</td>" +
      '<td class="num mono">' + fmt(x.trades) + "</td>" +
      (withWL ? '<td class="num mono"><span class="pos">' + fmt(x.wins) +
                '</span> / <span class="' + (x.losses ? "neg" : "muted") + '">' +
                fmt(x.losses) + "</span></td>" : "") +
      '<td class="num mono pos">' + pct(x.win_rate_pct, 1) + "</td>" +
      '<td class="num mono pos">' + pct(x.roi_pct, 0) + "</td>" +
      '<td class="num mono">' + pct(x.max_drawdown_pct) + "</td>" +
      "<td>" + goalBadge(x.goal) + "</td></tr>";
  }

  /* ------------------------------------------------------------ overview */
  function loadOverview() {
    api("/api/backtest").then(function (d) {
      rowsInto($("#overviewMonths"),
        (d.default_accounting || []).map(function (x) { return monthRow(x, false); }).join(""), 7);
    }).catch(function (e) {
      rowsInto($("#overviewMonths"), "", 7, e.message);
    });

    var host = $("#equityChart");
    if (!host) return;
    var month = host.dataset.month || (window.V01T && window.V01T.defaultMonth) || "jul2026";
    api("/api/backtest/" + month + "/trades?limit=1000").then(function (d) {
      drawEquity(host, (d.trades || []).map(function (t) { return t.capital_after; }));
    }).catch(function () { host.innerHTML = '<div class="empty">Chart unavailable</div>'; });
  }

  /* Equity curve on a log scale — linear would render every early trade flat. */
  function drawEquity(host, series) {
    if (!series || series.length < 2) {
      host.innerHTML = '<div class="empty"><span>Not enough trades to plot</span></div>';
      return;
    }
    var W = 640, H = 220, P = { t: 12, r: 12, b: 24, l: 58 };
    var logs = series.map(function (v) { return Math.log10(Math.max(v, 1e-9)); });
    var lo = Math.min.apply(null, logs), hi = Math.max.apply(null, logs);
    if (hi === lo) hi = lo + 1;

    var x = function (i) { return P.l + (i / (series.length - 1)) * (W - P.l - P.r); };
    var y = function (i) { return P.t + (1 - (logs[i] - lo) / (hi - lo)) * (H - P.t - P.b); };

    var line = series.map(function (_, i) { return (i ? "L" : "M") + x(i).toFixed(1) + " " + y(i).toFixed(1); }).join(" ");
    var area = line + " L" + x(series.length - 1).toFixed(1) + " " + (H - P.b) + " L" + P.l + " " + (H - P.b) + " Z";

    var grid = "", labels = "";
    for (var g = 0; g <= 4; g++) {
      var gy = P.t + (g / 4) * (H - P.t - P.b);
      var val = Math.pow(10, hi - (g / 4) * (hi - lo));
      grid += '<line class="chart-grid" x1="' + P.l + '" y1="' + gy.toFixed(1) + '" x2="' + (W - P.r) + '" y2="' + gy.toFixed(1) + '"/>';
      labels += '<text class="chart-axis" x="' + (P.l - 6) + '" y="' + (gy + 3).toFixed(1) + '" text-anchor="end">' +
        (val >= 1e6 ? (val / 1e6).toFixed(1) + "M" : val >= 1e3 ? (val / 1e3).toFixed(0) + "k" : val.toFixed(0)) + "</text>";
    }

    host.innerHTML =
      '<svg class="chart" viewBox="0 0 ' + W + " " + H + '" role="img" preserveAspectRatio="none" ' +
      'aria-label="Equity curve, log scale, ' + series.length + ' trades, final ' + money(series[series.length - 1]) + '">' +
      '<defs><linearGradient id="eqFill" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="#10b981" stop-opacity=".26"/>' +
      '<stop offset="100%" stop-color="#10b981" stop-opacity="0"/></linearGradient></defs>' +
      grid + labels +
      '<path class="chart-area" d="' + area + '"/><path class="chart-line" d="' + line + '"/>' +
      "</svg>" +
      '<div class="metric-foot" style="text-align:right">log scale · ' + series.length +
      " trades · final <span class='pos mono'>" + money(series[series.length - 1]) + "</span></div>";
  }

  /* ------------------------------------------------------------ backtest */
  function loadBacktest() {
    api("/api/backtest").then(function (d) {
      rowsInto($("#btDefault"), (d.default_accounting || []).map(function (x) { return monthRow(x, true); }).join(""), 8);
      rowsInto($("#btStrict"), (d.strict_non_overlapping || []).map(function (x) { return monthRow(x, true); }).join(""), 8);
    }).catch(function (e) {
      rowsInto($("#btDefault"), "", 8, e.message);
      rowsInto($("#btStrict"), "", 8, e.message);
    });
  }

  /* -------------------------------------------------------------- trades */
  function loadTrades() {
    var sel = $("#tradeMonth");
    if (!sel) return;
    var month = sel.value;
    rowsInto($("#tradeRows"), '<tr><td colspan="9"><div class="loading"><div class="spinner"></div></div></td></tr>', 9);
    api("/api/backtest/" + month + "/trades?limit=500").then(function (d) {
      var rows = (d.trades || []).map(function (t) {
        return "<tr>" +
          '<td class="num mono muted">' + fmt(t.n) + "</td>" +
          '<td class="num mono muted">' + fmt(t.index) + "</td>" +
          '<td class="num mono">' + money(t.entry_price) + "</td>" +
          '<td class="num mono">' + fmt(t.bb_pct, 2) + "</td>" +
          '<td class="num mono">' + fmt(t.hv_ratio, 3) + "</td>" +
          "<td>" + (t.win ? '<span class="badge pass">win</span>' : '<span class="badge fail">loss</span>') + "</td>" +
          '<td class="num mono ' + (t.win ? "pos" : "muted") + '">' + fmt(t.max_move_pct, 3) + "%</td>" +
          '<td class="num mono muted">' + (t.bars_to_expansion === null ? "—" : fmt(t.bars_to_expansion)) + "</td>" +
          '<td class="num mono">' + money(t.capital_after) + "</td></tr>";
      }).join("");
      rowsInto($("#tradeRows"), rows, 9);
      var c = $("#tradeCount");
      if (c) c.textContent = fmt(d.total) + " trades · " + esc(d.accounting || "");
    }).catch(function (e) { rowsInto($("#tradeRows"), "", 9, e.message); });
  }
  var tm = $("#tradeMonth");
  if (tm) tm.addEventListener("change", loadTrades);

  /* ------------------------------------------------------------- signals */
  function loadSignals() {
    api("/api/v01t/squeezes?limit=200").then(function (d) {
      var rows = (d.squeezes || []).map(function (s) {
        var up = s.bb_pct > 50;
        return "<tr>" +
          '<td class="num mono muted">' + fmt(s.index) + "</td>" +
          '<td class="num mono">' + money(s.price) + "</td>" +
          '<td class="num mono">' + fmt(s.bb_pct, 2) + "</td>" +
          '<td class="num mono">' + fmt(s.hv_ratio, 3) + "</td>" +
          '<td class="num mono">' + fmt(s.score) + "</td>" +
          "<td>" + (up ? '<span class="badge warn">upper</span>' : '<span class="badge info">lower</span>') + "</td></tr>";
      }).join("");
      rowsInto($("#squeezeRows"), rows, 6, "No squeezes detected");
    }).catch(function (e) { rowsInto($("#squeezeRows"), "", 6, e.message); });
  }

  /* ------------------------------------------------------------- monitor */
  function loadMonitor() {
    api("/api/ve_monitor").then(function (m) {
      var g = m.goal || {};
      $("#monMetrics").innerHTML = [
        metricCard("Status", m.running ? "RUNNING" : "STOPPED", m.running ? "live loop" : "halted", m.running ? "ok" : "bad", m.running ? "pos" : "neg"),
        metricCard("Cycles", fmt(m.cycles), "since start", "", ""),
        metricCard("Resolved", fmt(m.resolved_trades), fmt(m.wins) + "W / " + fmt(m.losses) + "L", "", ""),
        metricCard("Win Rate", pct(m.win_rate_pct, 1), g.wr_above_80 ? "above 80% target" : "below target", g.wr_above_80 ? "ok" : "watch", g.wr_above_80 ? "pos" : "warn-t"),
        metricCard("Capital", money(m.capital), "ROI " + pct(m.roi_pct, 1), "", "pos"),
        metricCard("Max DD", pct(m.max_drawdown_pct), g.dd_below_5 ? "under 5% target" : "above target", g.dd_below_5 ? "ok" : "bad", g.dd_below_5 ? "pos" : "neg"),
        metricCard("Open Windows", fmt(m.pending_windows), "awaiting move", "", ""),
        metricCard("Errors", fmt(m.errors), m.last_error || "none", m.errors ? "bad" : "ok", m.errors ? "neg" : "pos")
      ].join("");
    }).catch(function () {});

    api("/api/ve_monitor/pending").then(function (d) {
      var rows = (d.pending || []).map(function (p) {
        return "<tr><td class='mono muted'>" + esc(p.id) + "</td>" +
          '<td class="num mono">' + money(p.entry_price) + "</td>" +
          '<td class="num mono">' + fmt(p.best_move_pct, 3) + "%</td>" +
          '<td class="num mono">' + fmt(p.bars_elapsed) + "h</td>" +
          '<td class="num mono muted">' + fmt(p.bars_remaining) + "h</td></tr>";
      }).join("");
      rowsInto($("#pendingRows"), rows, 5, "No open windows");
    }).catch(function () {});

    api("/api/ve_monitor/history?limit=50").then(function (d) {
      var rows = (d.history || []).slice().reverse().map(function (t) {
        return "<tr><td>" + (t.win ? '<span class="badge pass">expansion</span>' : '<span class="badge fail">no move</span>') + "</td>" +
          '<td class="num mono">' + money(t.entry_price) + "</td>" +
          '<td class="num mono">' + money(t.exit_price) + "</td>" +
          '<td class="num mono ' + (t.win ? "pos" : "muted") + '">' + fmt(t.max_move_pct, 3) + "%</td>" +
          '<td class="num mono muted">' + fmt(t.bars_held) + "</td>" +
          '<td class="num mono ' + (t.win ? "pos" : "neg") + '">' + t.multiplier + "</td>" +
          '<td class="num mono">' + money(t.capital_after) + "</td></tr>";
      }).join("");
      rowsInto($("#settledRows"), rows, 7, "No settled trades yet");
    }).catch(function () {});
  }

  function metricCard(label, value, foot, cls, valCls) {
    return '<div class="metric ' + (cls || "") + '">' +
      '<div class="metric-label">' + esc(label) + "</div>" +
      '<div class="metric-value sm ' + (valCls || "") + '">' + esc(value) + "</div>" +
      '<div class="metric-foot">' + esc(foot) + "</div></div>";
  }


  /* ----------------------------------------------------------- execution */
  function loadExecution() {
    api("/api/exchange").then(function (x) {
      var st = x.state, c = x.credentials, live = x.mode === "live";
      var badge = $("#execModeBadge");
      if (badge) {
        badge.textContent = x.mode.toUpperCase().replace("_", " ");
        badge.className = "badge " + (live ? "fail" : x.mode === "dry_run" ? "warn" : "info");
      }
      var venue = $("#execVenue");
      if (venue) venue.textContent = x.exchange + " · " + x.symbol + " · " + x.leverage + "×" +
        (c.kucoin_sandbox ? " · sandbox" : " · MAINNET");

      $("#execMetrics").innerHTML = [
        metricCard("Mode", x.mode.toUpperCase(), x.mode_meaning, live ? "bad" : "ok", live ? "neg" : "pos"),
        metricCard("Venue", "KUCOIN", "futures · hedge mode", "", ""),
        metricCard("Legs / Squeeze", String(x.double_entry.legs_per_squeeze), "long + short, same price", "ok", "pos"),
        metricCard("Net Edge", pct(x.double_entry.net_pct_of_capital * 100, 1), "of capital per squeeze", "ok", "pos"),
        metricCard("Squeezes Executed", fmt(st.squeezes_executed), fmt(st.legs_placed) + " legs placed", "", ""),
        metricCard("Rejected", fmt(st.rejected), st.last_rejection || "none", st.rejected ? "watch" : "ok", st.rejected ? "warn-t" : "pos"),
        metricCard("Errors", fmt(st.errors), st.last_error || "none", st.errors ? "bad" : "ok", st.errors ? "neg" : "pos"),
        metricCard("Equity", money(st.equity), "loss " + pct(st.daily_loss_pct), "", "")
      ].join("");

      $("#execModes").innerHTML = [
        ["paper", "none", "no", "nothing — default"],
        ["dry_run", "yes (read)", "no — logged only", "API credentials"],
        ["live", "yes (write)", "YES — real orders", "V01T_EXEC_MODE=live + V01T_LIVE=I_UNDERSTAND"]
      ].map(function (m) {
        var on = x.mode === m[0];
        return "<tr" + (on ? ' style="background:var(--accent-dim)"' : "") + ">" +
          "<td><strong>" + m[0] + "</strong></td><td class='muted'>" + m[1] + "</td>" +
          "<td class='" + (m[0] === "live" ? "neg" : "muted") + "'>" + m[2] + "</td>" +
          "<td class='mono' style='white-space:normal'>" + esc(m[3]) + "</td>" +
          "<td>" + (on ? '<span class="badge pass">active</span>' : '<span class="badge neutral">—</span>') + "</td></tr>";
      }).join("");

      $("#execCreds").innerHTML = [
        ["KUCOIN_API_KEY", c.kucoin_api_key], ["KUCOIN_API_SECRET", c.kucoin_api_secret],
        ["KUCOIN_API_PASSPHRASE", c.kucoin_api_passphrase],
        ["V01T_LIVE confirmation", c.live_confirmation]
      ].map(function (r) {
        return "<tr><td class='mono muted'>" + esc(r[0]) + "</td><td>" +
          (r[1] ? '<span class="badge pass">set</span>' : '<span class="badge neutral">not set</span>') +
          "</td></tr>";
      }).join("") +
        "<tr><td class='mono muted'>Endpoint</td><td>" +
        (c.kucoin_sandbox ? '<span class="badge info">sandbox</span>' : '<span class="badge fail">mainnet</span>') +
        "</td></tr>";
    }).catch(function (e) {
      var m = $("#execMetrics"); if (m) m.innerHTML = '<div class="empty">' + esc(e.message) + "</div>";
    });

    api("/api/exchange/orders?limit=50").then(function (d) {
      var rows = (d.orders || []).slice().reverse().map(function (o) {
        return "<tr><td class='mono muted'>" + esc(o.id) + "</td>" +
          '<td class="num mono">' + money(o.entry_price) + "</td>" +
          '<td class="num mono">' + fmt(o.contracts_per_leg) + "</td>" +
          '<td class="num mono">' + money(o.notional_per_leg) + "</td>" +
          '<td class="num mono">' + fmt(o.bb_pct, 2) + "</td>" +
          "<td><span class='badge " + (o.mode === "live" ? "fail" : "info") + "'>" + esc(o.mode) + "</span></td></tr>";
      }).join("");
      rowsInto($("#execOrders"), rows, 6, "No double entries executed yet");
      var b = $("#badgeExec"); if (b) b.textContent = fmt(d.count);
    }).catch(function () {});

    api("/api/exchange/risk").then(function (r) {
      var L = r.limits, C = r.current;
      $("#execRails").innerHTML = [
        ["Max concurrent squeezes", L.max_concurrent_squeezes, C.open_squeezes, C.open_squeezes < L.max_concurrent_squeezes],
        ["Max daily loss", pct(L.max_daily_loss_pct), pct(C.daily_loss_pct), C.daily_loss_pct < L.max_daily_loss_pct],
        ["Max notional / leg", money(L.max_notional_per_leg), "—", true],
        ["Min free balance", money(L.min_free_balance), money(C.equity), C.equity >= L.min_free_balance],
        ["Kill switch", L.kill_switch ? "ENGAGED" : "off", "—", !L.kill_switch]
      ].map(function (x) {
        return "<tr><td>" + esc(x[0]) + "</td><td class='num mono'>" + esc(x[1]) + "</td>" +
          "<td class='num mono'>" + esc(x[2]) + "</td><td>" +
          (x[3] ? '<span class="badge pass">ok</span>' : '<span class="badge fail">blocking</span>') + "</td></tr>";
      }).join("");
      if (r.blocking) toast("Execution blocked: " + r.blocking, "neg");
    }).catch(function () {});

    previewOrder();
  }

  function previewOrder() {
    var pr = $("#pvPrice"), eq = $("#pvEquity");
    if (!pr || !eq) return;
    api("/api/exchange/preview?price=" + encodeURIComponent(pr.value) +
        "&equity=" + encodeURIComponent(eq.value)).then(function (d) {
      $("#pvLegs").innerHTML = d.legs.map(function (l) {
        return "<tr><td><span class='badge " + (l.leg === "LONG" ? "pass" : "fail") + "'>" + l.leg + "</span></td>" +
          "<td class='mono'>" + esc(l.side) + "</td><td class='mono muted'>" + esc(l.positionSide) + "</td>" +
          "<td class='num mono'>" + fmt(l.size) + "</td>" +
          "<td class='num mono neg'>" + money(l.stopLoss) + "</td>" +
          "<td class='num mono pos'>" + money(l.takeProfit) + "</td></tr>";
      }).join("");
      $("#pvNote").innerHTML = d.tradable
        ? fmt(d.contracts_per_leg) + " contracts/leg · " + money(d.notional_per_leg) +
          " notional per leg · " + d.leverage + "× on " + esc(d.symbol)
        : "<span class='neg'>Not tradable: size rounds to zero contracts at this equity/price.</span>";
    }).catch(function (e) { rowsInto($("#pvLegs"), "", 6, e.message); });
  }
  ["#pvPrice", "#pvEquity"].forEach(function (s) {
    var el = $(s);
    if (el) { var t; el.addEventListener("input", function () { clearTimeout(t); t = setTimeout(previewOrder, 300); }); }
  });

  var pfBtn = $("#preflightBtn");
  if (pfBtn) pfBtn.addEventListener("click", function () {
    var host = $("#execPreflight");
    host.innerHTML = '<div class="loading"><div class="spinner"></div><span>Contacting exchange…</span></div>';
    api("/api/exchange/preflight").then(function (p) {
      if (p.ready && p.note) { host.innerHTML = '<div class="callout info">' + esc(p.note) + "</div>"; return; }
      var rows = Object.keys(p.checks || {}).map(function (k) {
        var c = p.checks[k];
        return "<tr><td>" + esc(k.replace(/_/g, " ")) + "</td><td>" +
          (c.ok ? '<span class="badge pass">ok</span>' : '<span class="badge fail">fail</span>') +
          "</td><td class='muted' style='white-space:normal'>" + esc(c.ok ? String(c.value) : c.error).slice(0, 90) + "</td></tr>";
      }).join("");
      host.innerHTML = "<div class='table-wrap' style='border:none'><table><tbody>" + rows + "</tbody></table></div>" +
        (p.ready ? '<div class="callout info" style="margin-top:var(--s-3)">All checks passed — account is ready.</div>'
                 : '<div class="callout warn" style="margin-top:var(--s-3)"><span>⚠</span><span>' +
                   esc(p.fatal || "Not ready. Blocking: " + (p.blocking || []).join(", ")) + "</span></div>");
      toast(p.ready ? "Preflight passed" : "Preflight failed", p.ready ? "pos" : "neg");
    }).catch(function (e) {
      host.innerHTML = '<div class="callout warn"><span>⚠</span><span>' + esc(e.message) + "</span></div>";
    });
  });

  var ecBtn = $("#execCycleBtn");
  if (ecBtn) ecBtn.addEventListener("click", function () {
    fetch("/api/exchange/cycle", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.executed) toast("Double entry placed @ " + money(d.executed.entry_price), "pos");
        else if (d.blocked) toast("Blocked: " + d.blocked, "neg");
        else toast(d.elite === false ? "No squeeze on this bar" : "Cycle complete");
        loadExecution();
      }).catch(function (e) { toast(e.message, "neg"); });
  });

  /* ---------------------------------------------------------------- risk */
  function loadCosts() {
    api("/api/costs").then(function (c) {
      $("#costRows").innerHTML = [
        ["Spread", c.spread_bps + " bps"],
        ["Taker fee", c.taker_fee_bps + " bps"],
        ["Slippage", c.slippage_bps + " bps"],
        ["Funding (8h)", c.funding_bps_8h + " bps"],
        ["Round trip vs notional", pct(c.round_trip_cost_pct_of_notional * 100, 3)],
        ["Round trip vs equity @50×", pct(c.round_trip_cost_pct_of_equity_at_50x * 100, 2)],
        ["Breakeven move", pct(c.breakeven_move_pct * 100, 3)]
      ].map(function (r) {
        return "<tr><td class='muted'>" + esc(r[0]) + "</td><td class='num mono'>" + esc(r[1]) + "</td></tr>";
      }).join("");
    }).catch(function () {});
  }

  function calcSize() {
    var eq = $("#calcEquity"), pr = $("#calcPrice"), out = $("#calcOut");
    if (!eq || !pr || !out) return;
    api("/api/sizing?equity=" + encodeURIComponent(eq.value) + "&price=" + encodeURIComponent(pr.value))
      .then(function (d) {
        var p = d.position;
        out.innerHTML = [
          metricCard("Units", fmt(p.units, 6), "base asset", "", ""),
          metricCard("Notional", money(p.notional), "position value", "", ""),
          metricCard("Margin", money(p.margin), "at " + d.rules.leverage + "×", "", ""),
          metricCard("Risk", money(p.risk_amount), pct(p.risk_pct_of_equity * 100) + " of equity", "watch", "warn-t"),
          metricCard("Stop Distance", money(p.stop_distance), "price move", "", ""),
          metricCard("Bound By", String(p.capped_by).toUpperCase(), "binding constraint", "", "")
        ].join("");
      }).catch(function (e) { out.innerHTML = '<div class="empty">' + esc(e.message) + "</div>"; });
  }
  ["#calcEquity", "#calcPrice"].forEach(function (s) {
    var el = $(s);
    if (el) {
      var t;
      el.addEventListener("input", function () { clearTimeout(t); t = setTimeout(calcSize, 300); });
    }
  });

  /* -------------------------------------------------------------- health */
  var ENDPOINTS = [
    "/api/health", "/api/status", "/api/backtest", "/api/backtest/jan2026",
    "/api/backtest/jul2026/trades", "/api/ve_monitor", "/api/ve_monitor/pending",
    "/api/ve_monitor/history", "/api/v01t", "/api/v01t/squeezes", "/api/v01t/series",
    "/api/v01t/report", "/api/engine", "/api/engine/compare", "/api/sizing", "/api/costs"
  ];

  function loadHealth() {
    api("/api/health").then(function (h) {
      $("#healthMetrics").innerHTML = [
        metricCard("Service", String(h.status).toUpperCase(), "v" + h.version, h.status === "ok" ? "ok" : "bad", h.status === "ok" ? "pos" : "neg"),
        metricCard("Dataset", fmt(h.dataset.bars) + " bars", h.dataset.symbol + " " + h.dataset.interval, h.dataset.bars_ok ? "ok" : "bad", ""),
        metricCard("Origin", String(h.dataset.origin).toUpperCase(), "data source", "", ""),
        metricCard("Uptime", fmt(h.uptime_seconds, 0) + "s", "since boot", "", "")
      ].join("");
    }).catch(function () {});

    var grid = $("#endpointGrid");
    if (grid) {
      grid.innerHTML = ENDPOINTS.map(function (p) {
        return '<a class="endpoint" href="' + p + '" target="_blank" rel="noopener">' +
          '<span class="verb">GET</span><span>' + esc(p) + '</span>' +
          '<span class="code" data-probe="' + p + '">…</span></a>';
      }).join("");
      ENDPOINTS.forEach(function (p) {
        fetch(p).then(function (r) {
          var el = grid.querySelector('[data-probe="' + p + '"]');
          if (el) { el.textContent = r.status; el.className = "code " + (r.ok ? "pos" : "neg"); }
        }).catch(function () {
          var el = grid.querySelector('[data-probe="' + p + '"]');
          if (el) { el.textContent = "ERR"; el.className = "code neg"; }
        });
      });
    }
  }

  /* --------------------------------------------------- live status poll */
  var lastResolved = null;

  function poll() {
    api("/api/ve_monitor").then(function (m) {
      var dot = $("#monDot"), txt = $("#monText"), badge = $("#badgeMon");
      if (dot) dot.className = "dot " + (m.running ? "live" : "down");
      if (txt) txt.textContent = m.running
        ? "live · " + fmt(m.cycles) + " cycles · " + fmt(m.resolved_trades) + " trades"
        : "monitor stopped";
      if (badge) badge.textContent = fmt(m.resolved_trades);

      var g = m.goal || {};
      var gt = $("#goalText");
      if (gt) {
        var all = g.wr_above_80 && g.roi_thousands_pct && g.dd_below_5;
        gt.textContent = m.resolved_trades ? (all ? "goal met" : "goal partial") : "goal —";
        gt.className = m.resolved_trades ? (all ? "pos" : "warn-t") : "muted";
      }

      if (lastResolved !== null && m.resolved_trades > lastResolved) {
        toast("Trade settled — capital " + money(m.capital), "pos");
        if ($("#view-monitor").classList.contains("active")) loadMonitor();
      }
      lastResolved = m.resolved_trades;
    }).catch(function () {
      var dot = $("#monDot"), txt = $("#monText");
      if (dot) dot.className = "dot down";
      if (txt) txt.textContent = "unreachable";
    });
  }

  /* ------------------------------------------------------------ palette */
  var CMDS = Object.keys(TITLES).map(function (k) {
    return { label: "Go to " + TITLES[k], hint: "view", run: function () { show(k); } };
  }).concat([
    { label: "Toggle theme", hint: "appearance", run: toggleTheme },
    { label: "Refresh current view", hint: "data", run: function () {
        var v = ($$(".view.active")[0] || {}).id;
        if (v) { v = v.replace("view-", ""); loaded[v] = false; hydrate(v); loaded[v] = true; toast("Refreshed " + TITLES[v]); }
      } },
    { label: "Open API health", hint: "system", run: function () { show("api"); } }
  ]);

  var mask = $("#paletteMask"), input = $("#paletteInput"), list = $("#paletteList");
  var filtered = CMDS, sel = 0;

  function renderPalette() {
    var q = (input.value || "").toLowerCase();
    filtered = CMDS.filter(function (c) { return c.label.toLowerCase().indexOf(q) !== -1; });
    if (sel >= filtered.length) sel = 0;
    list.innerHTML = filtered.length
      ? filtered.map(function (c, i) {
          return '<button class="palette-item' + (i === sel ? " sel" : "") + '" data-i="' + i + '" role="option">' +
            esc(c.label) + '<span class="hint">' + esc(c.hint) + "</span></button>";
        }).join("")
      : '<div class="empty"><span>No matching command</span></div>';
  }
  function openPalette() { mask.classList.add("open"); input.value = ""; sel = 0; renderPalette(); input.focus(); }
  function closePalette() { mask.classList.remove("open"); }

  if (input) {
    input.addEventListener("input", renderPalette);
    list.addEventListener("click", function (e) {
      var b = e.target.closest("[data-i]");
      if (b) { closePalette(); filtered[+b.dataset.i].run(); }
    });
    mask.addEventListener("click", function (e) { if (e.target === mask) closePalette(); });
  }

  document.addEventListener("keydown", function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openPalette(); return; }
    if (mask && mask.classList.contains("open")) {
      if (e.key === "Escape") { closePalette(); }
      else if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(sel + 1, filtered.length - 1); renderPalette(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(sel - 1, 0); renderPalette(); }
      else if (e.key === "Enter" && filtered[sel]) { e.preventDefault(); closePalette(); filtered[sel].run(); }
      return;
    }
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
    var n = parseInt(e.key, 10);
    if (n >= 1 && n <= 9) show(Object.keys(TITLES)[n - 1]);
  });

  var pb = $("#paletteBtn"); if (pb) pb.addEventListener("click", openPalette);

  /* -------------------------------------------------------------- theme */
  function toggleTheme() {
    var cur = document.documentElement.getAttribute("data-theme");
    var next = cur === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("v01t-theme", next); } catch (_) {}
    toast("Theme: " + next);
  }
  var tb = $("#themeBtn"); if (tb) tb.addEventListener("click", toggleTheme);
  try {
    var saved = localStorage.getItem("v01t-theme");
    if (saved) document.documentElement.setAttribute("data-theme", saved);
  } catch (_) {}

  var rt = $("#railToggle");
  if (rt) rt.addEventListener("click", function () {
    var open = $("#rail").classList.toggle("open");
    rt.setAttribute("aria-expanded", String(open));
  });

  /* --------------------------------------------------------------- boot */
  show(location.hash.slice(1) || "overview");
  poll();
  setInterval(poll, 4000);
})();
