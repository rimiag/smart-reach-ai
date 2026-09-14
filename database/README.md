# Database schema scripts (manual fallback)

Normally you run **nothing** in this folder: the backend entrypoint compares
the ORM models against the database at every startup and automatically
creates missing tables (`create_all`) and missing columns (`ensure_schema`).

Use these scripts only when that automatic path cannot run or you are
building an environment from zero.

## Contents

| File | Purpose |
|---|---|
| `schema_full.sql` | Complete schema for a **fresh / empty** database. Re-runnable (`CREATE TABLE IF NOT EXISTS`). AUTO-GENERATED from the ORM models - do not edit by hand. |
| `incremental/*.sql` | Targeted upgrades for **existing** databases. Idempotent (each ALTER is guarded by an information_schema check) - safe to run repeatedly. |

## Compatibility

Works unchanged on **MySQL 8.x** and **MariaDB 10.1+** (staging runs
MariaDB 10.1): utf8mb4 charset, InnoDB, indexed strings capped at 191
characters to respect MariaDB 10.1's 767-byte index limit. No stored
procedures, no engine-specific syntax.

## When to run what

| Situation | Action |
|---|---|
| Normal deploy (CI pushed new code) | Nothing - entrypoint auto-applies schema. |
| Entry point crashed on schema / "Unknown column" persists after deploy | Run the newest `incremental/*.sql` you have not applied. |
| Brand-new database (new environment, recovery) | Run `schema_full.sql`. |
| Completely broken database state | [Full recovery](#full-recovery-from-a-broken-database) below. |

## Running on staging (scripts live in the runner checkout after a deploy)

```bash
cd /home/rizwan/actions-runner/_work/smart-reach-ai/smart-reach-ai

# Full schema into an EMPTY database:
docker exec -i smart-reach-ai-staging-db-1 mysql -u root -p<MYSQL_ROOT_PASSWORD> \
  -D leadgen_db < database/schema_full.sql

# Incremental upgrade into an EXISTING database:
docker exec -i smart-reach-ai-staging-db-1 mysql -u root -p<MYSQL_ROOT_PASSWORD> \
  -D leadgen_db < database/incremental/2026-09-14_admin_billing.sql
```

Notes:
- `-i` (not `-it`) is required - it feeds the file in through stdin.
- `-D leadgen_db` selects the database, which the incremental guards
  (`DATABASE()`) depend on.
- The checkout only exists on the VM after at least one deploy. If the VM
  has no checkout yet, copy the file up first:
  `scp database/schema_full.sql root@192.168.1.30:/root/`
  and run `docker exec -i ... < /root/schema_full.sql`.

## Running locally (laptop)

```bash
cd backend
mysql -u <user> -p -D <database> < ../database/schema_full.sql
```

No mysql client installed? The Python route (adjust the URL):

```bash
.venv/Scripts/python -c "import pymysql; c=pymysql.connect(host='127.0.0.1',user='root',password='...',database='leadgen_db',autocommit=True); [c.cursor().execute(s) for s in open('../database/schema_full.sql').read().split(';') if s.strip() and not s.strip().startswith('--')]"
```

## Running on MySQL 8 (future production)

```bash
mysql -u <admin_user> -p -D <database> < database/schema_full.sql
```

Same file, no changes. Create the database first with utf8mb4:

```sql
CREATE DATABASE <database> CHARACTER SET utf8mb4;
```

## Full recovery (broken database)

This **destroys all data** - the staging-DB reset in
`STAGING_DEPLOYMENT.md` is the same operation driven by CI.

```bash
docker exec -it smart-reach-ai-staging-db-1 mysql -u root -p -e "
  DROP DATABASE leadgen_db;
  CREATE DATABASE leadgen_db CHARACTER SET utf8mb4;"
docker exec -i smart-reach-ai-staging-db-1 mysql -u root -p -D leadgen_db \
  < database/schema_full.sql
docker restart smart-reach-ai-staging-backend-1
```

## Verify what a database actually has

```sql
-- Tables (expect 7: users, campaigns, leads, research_results, emails, replies, suppressions)
SHOW TABLES;

-- Columns of a table
SHOW COLUMNS FROM users;

-- Which upgrade columns are present?
SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND (COLUMN_NAME IN ('plan','billing_status','billing_notes')
       OR (TABLE_NAME='leads' AND COLUMN_NAME='follow_up_count'));
```

Expect the 4 upgrade columns: `users.plan`, `users.billing_status`,
`users.billing_notes`, `leads.follow_up_count`.

## After every model change (for developers)

Regenerate the full schema so it never drifts from the code, and commit it
together with the model change:

```bash
cd backend
python generate_schema_sql.py      # writes ../database/schema_full.sql
```

For an EXISTING database, also drop a guarded ALTER into
`database/incremental/<date>_<topic>.sql` - copy the guard pattern from
`2026-09-14_admin_billing.sql`. (The entrypoint's `ensure_schema` applies
the same change automatically, so the incremental file is only the manual
fallback for when that cannot run.)
