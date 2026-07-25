// v01T model dashboard — polls /api/status and reflects liveness in the footer.
(function () {
  "use strict";

  var footer = document.querySelector("footer");
  if (!footer) return;
  var base = footer.textContent;

  function tick() {
    fetch("/api/status")
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (s) {
        footer.textContent =
          base + " · uptime " + Math.round(s.uptime_seconds) + "s · " + s.roi_repr + " %";
      })
      .catch(function () {
        footer.textContent = base + " · status unavailable";
      });
  }

  tick();
  setInterval(tick, 15000);
})();
