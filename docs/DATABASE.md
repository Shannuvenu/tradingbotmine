# Database

Default: SQLite at `data_store/indiaquant.db` (WAL mode). Created/migrated by `python -m indiaquant.cli init`.
Migrations are an ordered list in `indiaquant/db.py` (`MIGRATIONS`); `schema_version` tracks what ran.

Tables: instruments, candles (PK instrument_key+interval+ts, with `source`), orders (PK client_tag), fills, signals,
kv_state (execution state, position metadata), audit_log, api_errors, backtest_runs, holidays, news,
model_registry, data_quality.

## Backup
Stop the dashboard/engine, copy `data_store/indiaquant.db` (and `-wal`/`-shm` if present).

## PostgreSQL migration path
1. Install PostgreSQL 16 for Windows; create database `indiaquant`.
2. Translate the `MIGRATIONS` SQL: `INTEGER PRIMARY KEY AUTOINCREMENT` → `BIGSERIAL PRIMARY KEY`; `REAL` →
   `DOUBLE PRECISION`; keep TEXT timestamps or convert to `TIMESTAMPTZ`.
3. Replace `sqlite3` in `Database.__init__` with `psycopg` and change `?` placeholders to `%s`
   (all SQL is in `db.py`, `instruments.py`, `calendar.py`, `engine.py`, `dashboard_data.py`, `ml.py`).
4. Copy data: `sqlite3 indiaquant.db .dump` → adapt → `psql`, or pandas `read_sql`/`to_sql` per table.
SQLite is adequate for one user on one PC; PostgreSQL is only worth it for multi-process writes or very large
1-minute histories.
