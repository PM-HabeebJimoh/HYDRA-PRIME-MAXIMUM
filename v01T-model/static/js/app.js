// v01T dashboard — polls the 24/7 monitor and reflects live state.
(function () {
  "use strict";

  function set(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function money(n) {
    return "$" + Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  function poll() {
    fetch("/api/monitor")
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (m) {
        set("mon-running", m.running ? "RUNNING" : "stopped");
        set("mon-cycles", m.cycles);
        set("mon-open", m.open_positions);
        set("mon-opps", m.active_opportunities);
        set("mon-off", m.off_opportunities);
        set("mon-closed", m.closed_trades);
        set("mon-equity", money(m.equity));
        set("mon-wr", m.closed_trades ? m.win_rate_pct.toFixed(1) + "%" : "no trades yet");
        var dot = document.getElementById("mon-dot");
        if (dot) dot.className = "dot" + (m.running ? " live" : "");
      })
      .catch(function () { set("mon-running", "unavailable"); });
  }

  poll();
  setInterval(poll, 3000);
})();
