# Backup and Recovery

MeetSage never silently deletes meeting data. Deleting a meeting is an
explicit user action (Meetings page → Delete), which removes its database
rows and the associated original/normalized media files.

## What to Back Up

| Item | Path | Why |
|---|---|---|
| SQLite database | `data/meetsage.db` | All meetings, jobs, transcripts, analyses, action items, settings, remote provider configs |
| Original uploads | `data/uploads/` | Referenced by path from the database (`Media.original_path`) |
| Normalized media | `data/media/` | Referenced by path (`Media.normalized_audio_path`); regenerable from the original via ffmpeg, but backing it up avoids re-processing |
| Downloaded models | `data/models/` | Not meeting data, but backing it up avoids re-downloading after a migration |
| Configuration | `.env` | Contains secrets (`HUGGINGFACE_TOKEN`, `LLM_API_KEY`) — back up somewhere at least as secure as the original, never in plain git |

**Transcripts, analysis results, and action items live inside `meetsage.db`,
not as separate files** — despite `data/transcripts/`, `data/analysis/`, and
`data/exports/` existing as directories, they are not currently populated
(reserved for future use). Backing up the database is what actually matters
for that data.

## Relationship Between Database and Filesystem Data

The database stores **paths** to files under `data/uploads/` and
`data/media/`, not the file contents. Backing up the database alone without
those directories leaves you with metadata pointing at files that don't
exist. Always back up the database and both media directories together, as
one consistent snapshot (stop the app first — see below — so the snapshot
isn't taken mid-write).

## Backup Procedure

```bash
./scripts/stop.sh   # ensures no writes are in-flight

BACKUP_DIR="meetsage-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp data/meetsage.db "$BACKUP_DIR/"
cp -r data/uploads "$BACKUP_DIR/"
cp -r data/media "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/.env"   # store this backup somewhere access-controlled

tar czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

./scripts/start.sh
```

Automate this on a schedule (cron) for production-style use; it's a manual
procedure in this version.

## Restore Procedure

```bash
./scripts/stop.sh

tar xzf meetsage-backup-YYYYMMDD-HHMMSS.tar.gz
cp meetsage-backup-YYYYMMDD-HHMMSS/meetsage.db data/meetsage.db
cp -r meetsage-backup-YYYYMMDD-HHMMSS/uploads/. data/uploads/
cp -r meetsage-backup-YYYYMMDD-HHMMSS/media/. data/media/
cp meetsage-backup-YYYYMMDD-HHMMSS/.env .env   # review before overwriting a live .env

./scripts/start.sh
./scripts/health_check.sh
```

## Migration to Another Ubuntu Machine

1. On the old machine: run the backup procedure above.
2. On the new machine: `git clone` (or copy) the repository, run
   `./scripts/install.sh` (sets up venv/node_modules/data dirs fresh, does
   **not** touch a `.env` or `data/` you restore over it afterward).
3. Extract the backup tarball and restore `data/meetsage.db`, `data/uploads/`,
   `data/media/`, and `.env` as in the restore procedure above, **before**
   running `./scripts/start.sh` for the first time on the new machine.
4. If the old machine had downloaded models you want to keep, also copy
   `data/models/` — otherwise `./scripts/download_models.sh <model>` will
   re-download them.
5. Run `./scripts/health_check.sh` to confirm FFmpeg/FFprobe are present on
   the new machine (they are a system dependency, not something the backup
   carries) and that the restored database/config look correct.

## Upgrade Procedure

```
Backup (above)
    ↓
Stop MeetSage           ./scripts/stop.sh
    ↓
Update source            git pull  (or replace the checkout)
    ↓
Update dependencies       ./scripts/install.sh
    ↓
Run migrations            included in install.sh — runs `alembic upgrade head`
    ↓
Verify configuration       diff .env.example against your .env for new variables
    ↓
Start MeetSage            ./scripts/start.sh
    ↓
Run health check           ./scripts/health_check.sh
```

Schema changes are managed by [Alembic](https://alembic.sqlalchemy.org/) (see
[development.md](development.md#database-migrations)) — `./scripts/install.sh`
runs `alembic upgrade head` as part of every install/upgrade, applying any new
migrations shipped since your last upgrade. It detects and handles a database
from before Alembic was introduced automatically (stamps it at the baseline
revision instead of re-running `CREATE TABLE`), so upgrading from an older
MeetSage checkout is safe to run as-is.

Always keep the pre-upgrade backup from step 1 until you've verified the
upgraded version works correctly against your restored data — a migration
that runs cleanly is not a substitute for a backup if something else about the
upgrade goes wrong.
