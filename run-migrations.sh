#!/bin/bash
# =============================================================================
# Post-Deployment Migration Runner
# =============================================================================
# Quick script to run database migrations after docker-compose deployment

echo "=========================================="
echo "Running Database Migrations"
echo "=========================================="

# Run the migration script
docker-compose exec backend python migrate.py

echo ""
echo "=========================================="
echo "Migration Complete!"
echo "=========================================="
echo "You can now login to the application"
