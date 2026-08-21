# MariaDB 10.1.22 Compatibility Guide

**Updated:** 2026-08-20
**Status:** ✅ Code adjusted for MariaDB 10.1.x compatibility

---

## 📋 Overview

All database code, migrations, and configurations have been updated to work with **MariaDB 10.1.22** (your local version) and the same settings are used in Docker Compose.

---

## 🔧 Changes Made

### 1. Database Driver Changed
**From:** `mysql+aiomysql://`
**To:** `mariadb+aiomysql://`

**Why:** The `mariadb` dialect is more compatible with MariaDB and handles version-specific features better.

### 2. DateTime Timezone Support Removed
**From:** `DateTime(timezone=True)`
**To:** `DateTime()`

**Why:** MariaDB 10.1 doesn't support timezone in DATETIME columns. This feature was added in MariaDB 10.2.

### 3. Server Defaults Updated
**From:** `server_default=func.now()`
**To:** `server_default=text("CURRENT_TIMESTAMP")`

**Why:** Better compatibility across MySQL/MariaDB versions.

### 4. JSON Type Replaced
**From:** `sa.JSON()`
**To:** `sa.Text()` with custom `JSONText` TypeDecorator

**Why:** MariaDB 10.1 doesn't have a native JSON type (added in MariaDB 10.2). The `JSONText` class stores JSON as TEXT and handles serialization/deserialization.

### 5. Docker Database Image Changed
**From:** `mysql:8.0`
**To:** `mariadb:10.1.48`

**Why:** To match your local MariaDB version for consistency across environments.

---

## 📁 Files Modified

| File | Changes |
|------|---------|
| [docker-compose.yml](docker-compose.yml) | Changed DB image to `mariadb:10.1.48`, updated DATABASE_URL |
| [backend/app/models/user.py](backend/app/models/user.py) | Removed timezone from DateTime, updated server defaults |
| [backend/app/models/campaign.py](backend/app/models/campaign.py) | Removed timezone from DateTime, updated server defaults |
| [backend/app/models/lead.py](backend/app/models/lead.py) | Removed timezone from DateTime, updated server defaults |
| [backend/alembic/versions/001_initial_migration.py](backend/alembic/versions/001_initial_migration.py) | Replaced JSON with TEXT, removed timezone, updated defaults |
| [backend/alembic/env.py](backend/alembic/env.py) | Added mariadb+aiomysql URL conversion |
| [backend/app/core/config.py](backend/app/core/config.py) | Updated default DATABASE_URL |
| [.env](.env) | Updated DATABASE_URL |
| [backend/.env](backend/.env) | Updated DATABASE_URL |
| [.env.example](.env.example) | Updated DATABASE_URL example |
| [LOCAL_DEVELOPMENT_GUIDE.md](LOCAL_DEVELOPMENT_GUIDE.md) | Updated with MariaDB instructions |

---

## 🧪 Local Testing with MariaDB 10.1.22

### Step 1: Verify Your MariaDB Installation
```bash
# Check MariaDB version
mysql --version
# Should show: MariaDB 10.1.22 or similar
```

### Step 2: Create Database and User
```bash
# Connect to MariaDB
mysql -u root -p

# Run these commands in MariaDB console:
CREATE DATABASE leadgen_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'leadgen_user'@'localhost' IDENTIFIED BY 'leadgen_pass';
GRANT ALL PRIVILEGES ON leadgen_db.* TO 'leadgen_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 3: Update Environment Variables
Your `.env` file should have:
```env
DATABASE_URL=mariadb+aiomysql://root:btpacs4admin@localhost:3306/leadgen_db
```

Or with the created user:
```env
DATABASE_URL=mariadb+aiomysql://leadgen_user:leadgen_pass@localhost:3306/leadgen_db
```

### Step 4: Run Migrations
```bash
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai\backend"

# Activate virtual environment
.venv\Scripts\activate

# Run migration
alembic upgrade head
```

### Step 5: Verify Migration
```bash
alembic current
# Expected: Revision: 001

# Or verify directly in MariaDB:
mysql -u root -p leadgen_db
SHOW TABLES;
# Should see: campaigns, leads, users
```

---

## 🐳 Docker Compose Testing

The docker-compose.yml now uses MariaDB 10.1.48 for consistency with your local setup:

```bash
# Start database with Docker
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai"
docker-compose up -d db redis

# Check it's running
docker-compose ps db

# View logs
docker-compose logs -f db
```

---

## 🔍 MariaDB 10.1 Limitations (What We're Working Around)

1. **No JSON data type** - Using TEXT with JSON serialization instead
2. **No DateTime with timezone** - Storing as DATETIME without timezone info
3. **No generated columns** - Using application-level computation
4. **No CHECK constraints** - Using application-level validation

---

## ⚠️ Important Notes

### JSON Handling
The `Campaign.keywords` and `Campaign.settings` fields use `JSONText` TypeDecorator:
- **Stored as:** TEXT in database
- **Read as:** Python dict/list
- **No validation:** Invalid JSON would be stored as-is

### Timezone Handling
All datetime fields are stored **without timezone**:
- Application assumes all times are in the same timezone as the database server
- For multi-timezone support, consider upgrading to MariaDB 10.3+

### Future Upgrade Path
If you later upgrade to MariaDB 10.3+, you can:
1. Add native JSON columns
2. Add TIMESTAMP with timezone support
3. Use generated columns for computed fields

---

## 🐛 Troubleshooting

### Error: "Unknown database type 'JSON'"
**Cause:** MariaDB 10.1 doesn't support JSON type
**Solution:** Already fixed - migration now uses TEXT

### Error: "Invalid default value for DATETIME"
**Cause:** Using timezone in DateTime
**Solution:** Already fixed - using `DateTime()` without timezone

### Error: "Not all keywords converted"
**Cause:** Incorrect database URL prefix
**Solution:** Use `mariadb+aiomysql://` instead of `mysql+aiomysql://`

---

## ✅ Pre-Migration Checklist

Before running the migration on your local MariaDB 10.1.22:

- [ ] MariaDB service is running
- [ ] Database `leadgen_db` is created
- [ ] User `leadgen_user` has privileges
- [ ] `.env` DATABASE_URL uses `mariadb+aiomysql://`
- [ ] Python virtual environment is activated
- [ ] All dependencies installed: `pip install -r requirements.txt`

---

## 📝 Database Connection String Format

```
mariadb+aiomysql://[username]:[password]@[host]:[port]/[database]
```

**Examples:**
```env
# Local MariaDB
DATABASE_URL=mariadb+aiomysql://root:btpacs4admin@localhost:3306/leadgen_db

# Docker MariaDB
DATABASE_URL=mariadb+aiomysql://leadgen_user:leadgen_pass@db:3306/leadgen_db

# Remote MariaDB
DATABASE_URL=mariadb+aiomysql://user:pass@remote-host.example.com:3306/leadgen_db
```

---

**All changes are backward compatible with MySQL 5.5+ and MariaDB 10.1+**
