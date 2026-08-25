@echo off
REM =============================================================================
REM Post-Deployment Migration Runner (Windows)
REM =============================================================================

echo ==========================================
echo Running Database Migrations
echo ==========================================

docker-compose exec backend python migrate.py

echo.
echo ==========================================
echo Migration Complete!
echo ==========================================
echo You can now login to the application
pause
