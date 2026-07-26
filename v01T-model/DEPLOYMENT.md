# Deployment — v01T Terminal

## Replit

The repository is Replit-ready. Import it and press **Run**.

```
.replit     run + deployment target (cloudrun), port 8000 -> 80
Procfile    web: uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
```

Both bind `0.0.0.0` and honour the injected `$PORT`, which is what a PaaS
requires — binding `127.0.0.1` is the usual cause of a "container failed to
start" error.

### Boot works offline

Real hourly market data for January, June and July 2026 is **vendored** in
`data/`, so the app boots and serves the full backtest with no outbound network
call. Nothing external is required for the dashboard to work.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | 8000 | injected by the platform |
| `V01T_MONITOR_INTERVAL` | 5 | seconds between 24/7 monitor cycles |
| `V01T_WINDOW` | 24 | expansion window in hours |

Exchange credentials are **only** needed for live order placement, never for
the dashboard:

```
KUCOIN_API_KEY  KUCOIN_API_SECRET  KUCOIN_API_PASSPHRASE  KUCOIN_SANDBOX=1
V01T_EXEC_MODE=paper        # paper (default) | dry_run | live
V01T_LIVE=I_UNDERSTAND      # additionally required before any real order
```

KuCoin Futures is the only supported venue. See `KUCOIN_SETUP.md`.

Set these as Replit **Secrets**, never in the repo. `.gitignore` covers `.env`.

## Any other host

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port $PORT
```

Runs unchanged on Render, Railway, Fly.io, Heroku or a plain VPS. Python 3.10+.

## Verify after deploying

```bash
curl -s https://<your-app>/api/health      # {"status":"ok", ...}
curl -s https://<your-app>/api/backtest    # all months, both accountings
curl -s https://<your-app>/api/ve_monitor  # {"running": true, ...}
```

Then open `/` — the terminal UI. Press **⌘K / Ctrl+K** for the command palette,
or **1–8** to jump between views.

## What runs continuously

The 24/7 monitor starts on application startup and stops cleanly on shutdown
(FastAPI lifespan events). It executes the backtested mechanic unattended:
opens expansion windows on elite squeezes, settles them on a 0.5% move either
way, and compounds capital at x1.225 / x0.975.

Confirm with `/api/ve_monitor` — `cycles` should increase between polls.

## Scaling notes

* The model is deterministic and computed once at import, so additional
  instances are safe and identical.
* Monitor state is in-memory and **per-instance**. Running several replicas
  gives several independent monitors. For a single shared monitor, run one
  instance, or externalise state before scaling out.
* No database is required.
