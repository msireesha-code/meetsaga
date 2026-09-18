# Deployment

## Local Deployment (dev mode — default)

```bash
./scripts/start.sh
```

Runs the backend (`uvicorn`, port 8000) and a separate frontend dev server
(`vite`, port 5173, with hot reload) as background processes on the same
machine. This is the right mode for day-to-day local use and development.

## Production-Style Deployment (single process, same-origin)

MeetSage's backend can serve the built frontend itself — one process, one
port, no CORS needed for the UI's own requests:

```bash
./scripts/build_frontend.sh                       # builds frontend/dist
MEETSAGE_MODE=production ./scripts/start.sh        # starts only the backend
```

In this mode `./scripts/start.sh` starts only the backend; it detects
`frontend/dist` and serves it directly (see `backend/app/main.py`), including
client-side route fallback (e.g. `/meetings/<id>` still loads the SPA
correctly, not a 404). Re-run `build_frontend.sh` after any frontend change
you want reflected here — the dev server's hot reload does not apply to this
path.

This is what's actually implemented and verified in this project; the
systemd/nginx material below builds on top of it for a persistent,
internet-facing deployment, which is provided as a starting point, not
something exercised end-to-end here.

## systemd

A ready-to-adapt unit file is at
[`deploy/systemd/meetsage.service`](../deploy/systemd/meetsage.service). It
runs the backend in production mode (same as above) under a dedicated
non-root user, with automatic restart on failure. Before use:

1. Build the frontend: `./scripts/build_frontend.sh`
2. Replace every `/opt/meetsage` in the unit file with your actual install
   path (systemd unit files don't expand shell variables — this needs to be a
   literal path).
3. Create the `meetsage` user/group (or change `User=`/`Group=` to an
   existing one) and make sure it owns the install directory.
4. Install and enable:
   ```bash
   sudo cp deploy/systemd/meetsage.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now meetsage
   sudo systemctl status meetsage
   ```

## Reverse Proxy (nginx)

An example config is at
[`deploy/nginx/meetsage.conf`](../deploy/nginx/meetsage.conf) — proxies to the
single backend process, terminates TLS, and sets generous timeouts (CPU-only
transcription/diarization can legitimately take a long time — see
[troubleshooting.md](troubleshooting.md#slow-transcription-or-diarization) —
so a typical short reverse-proxy timeout would cut off a slow-but-working
request). Adjust `server_name`, certificate paths, and
`client_max_body_size` (match `MAX_UPLOAD_SIZE_MB` from your `.env`) before
using it.

## CORS

`CORS_ALLOWED_ORIGINS` in `.env` (comma-separated) controls which origins the
backend accepts cross-origin requests from — this only matters in **dev
mode**, where the frontend runs on a different port (5173) than the backend
(8000). In **production mode**, the frontend is served from the same origin
as the API, so no CORS configuration is needed at all for the UI to work; if
you're also serving a browser client from yet another external origin, add it
here.

## Ports

Default: backend `8000`, frontend `5173` (dev mode only). Override via
`MEETSAGE_BACKEND_PORT` / `MEETSAGE_FRONTEND_PORT` environment variables when
calling `scripts/start.sh`, or by editing the reverse-proxy/systemd config
directly for a production-style setup.

## Filesystem Permissions

`data/` (database, uploads, media, models) should be owned by whatever user
runs the backend process, with no group/world write access — it contains
meeting recordings and, indirectly (via `.env`), secrets are read from outside
this directory but never written into it.

## Logs

Local mode (either dev or production `start.sh`): `data/logs/backend.log`,
and `data/logs/frontend.log` in dev mode (plain files, no rotation configured
— rotate manually or via `logrotate` for long-term use). Under systemd, logs
go to the journal (`journalctl -u meetsage`) instead.

## Environment Configuration

See [configuration.md](configuration.md) for every `.env` variable. For a
non-local deployment, treat `HUGGINGFACE_TOKEN` and `LLM_API_KEY` as secrets
(file permissions, not committed, ideally injected via your process
manager's secret mechanism rather than a plain `.env` file on disk).

## Service Management

Local mode: `./scripts/start.sh`, `./scripts/stop.sh`,
`./scripts/health_check.sh` (works against either mode — it only checks the
backend's `/api/system/health` and doesn't care whether the frontend dev
server is also running). Under systemd:
`systemctl {start,stop,status} meetsage`, plus nginx's own service if you're
using the reverse proxy.

## Backup Considerations

See [backup-recovery.md](backup-recovery.md) — at minimum, back up
`data/meetsage.db`, `data/uploads/`, and `data/media/` together, since the
database references files in those directories by path.
