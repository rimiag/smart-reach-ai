-- =========================================================================
-- Incremental upgrade: admin panel billing columns + lead follow-up counter
-- Date: 2026-09-14   |   Applies to: EXISTING databases created before this date
-- Idempotent: every ALTER is guarded - safe to run repeatedly.
-- Compatible with MySQL 8.x and MariaDB 10.1+.
--
-- NOTE: the backend entrypoint applies these automatically at startup.
-- Only run this by hand if the entrypoint could not (see database/README.md).
--
-- Run:  mysql -u <user> -p <database> < database/incremental/2026-09-14_admin_billing.sql
-- =========================================================================

-- users.plan -------------------------------------------------------------
SET @ddl := (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE users ADD COLUMN plan VARCHAR(50) NOT NULL DEFAULT ''free''',
  'SELECT 1 AS plan_already_exists')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'plan');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- users.billing_status ---------------------------------------------------
SET @ddl := (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE users ADD COLUMN billing_status VARCHAR(50) NOT NULL DEFAULT ''active''',
  'SELECT 1 AS billing_status_already_exists')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'billing_status');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- users.billing_notes ----------------------------------------------------
SET @ddl := (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE users ADD COLUMN billing_notes TEXT NULL',
  'SELECT 1 AS billing_notes_already_exists')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'billing_notes');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- leads.follow_up_count --------------------------------------------------
SET @ddl := (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE leads ADD COLUMN follow_up_count INT NOT NULL DEFAULT 0',
  'SELECT 1 AS follow_up_count_already_exists')
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'leads' AND COLUMN_NAME = 'follow_up_count');
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Verify -----------------------------------------------------------------
SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND (COLUMN_NAME IN ('plan', 'billing_status', 'billing_notes')
       OR (TABLE_NAME = 'leads' AND COLUMN_NAME = 'follow_up_count'))
ORDER BY TABLE_NAME, COLUMN_NAME;
