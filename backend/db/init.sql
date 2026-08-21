-- =============================================================================
-- Database Initialization Script for MariaDB
-- =============================================================================
-- This script is run automatically when the database container is first created
-- It sets up the database with proper character set and collation

-- Set character set and collation for better international support
ALTER DATABASE leadgen_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Note: Table creation is handled by Alembic migrations
-- This script ensures proper database configuration

-- Success message (for verification)
SELECT 'Database initialized successfully' AS status;
