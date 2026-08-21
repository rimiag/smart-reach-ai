# Iteration 1.3 - Docker Compose Testing Guide

**For Docker Compose Development Environment**

---

## 🐳 Prerequisites

- Docker Desktop running
- Docker Compose installed
- Project directory: `c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai`

---

## Part 1: Start Services

### Step 1: Navigate to Project Root
```bash
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai"
```

### Step 2: Start All Services
```bash
docker-compose up -d
```

### Step 3: Verify Services Running
```bash
docker-compose ps
```

**Expected Output:**
```
NAME                STATUS              PORTS
smart-reach-ai-frontend    Up                 0.0.0.0:3000->3000/tcp
smart-reach-ai-backend     Up                 0.0.0.0:8000->8000/tcp
smart-reach-ai-db          Up (healthy)       0.0.0.0:3306->3306/tcp
smart-reach-ai-redis       Up (healthy)       0.0.0.0:6379->6379/tcp
```

---

## Part 2: Database Migration (Docker)

### Step 1: Run Migration in Backend Container
```bash
docker-compose exec backend alembic upgrade head
```

### Step 2: Verify Migration
```bash
docker-compose exec backend alembic current
```

**Expected:** `Revision: 001`

---

## Part 3: Backend Model Test (Docker)

### Step 1: Run Lead Model Test
```bash
docker-compose exec backend python -m app.db.test_lead_model
```

**Expected Output:**
```
============================================================
Iteration 1.3 - Lead Model Test
============================================================

[1] Checking for test user...
   ✅ Test user found
[2] Creating test campaign...
   ✅ Campaign created
[3] Creating test lead...
   ✅ Lead created
[4] Reading lead back...
   ✅ Lead retrieved successfully
[5] Testing lead update...
   ✅ Lead updated
[6] Testing lead approval...
   ✅ Lead approved
[7] Testing campaign relationship...
   ✅ Campaign has 1 lead(s)
[8] Cleanup...
   ✅ Test data cleaned up

============================================================
✅ ALL TESTS PASSED
============================================================
```

**Status:** ☐ Pass

---

## Part 4: Backend API Test (Docker)

### Step 1: Verify Backend Health
```bash
curl http://localhost:8000/health
```

**Expected:** `{"status": "healthy", ...}`

### Step 2: Open API Docs
Navigate to: http://localhost:8000/docs

**Expected:** Swagger UI with all endpoints visible

### Step 3: Run API Test Script
```bash
docker-compose exec backend python -m app.api.test_leads_api
```

**Expected Output:**
```
============================================================
Iteration 1.3 - Leads API Test
============================================================

[1/10] Testing authentication...
      ✅ Authentication successful
[2/10] Creating test campaign...
      ✅ Campaign created
[3/10] Creating lead...
      ✅ Lead created
[4/10] Listing leads...
      ✅ Retrieved 1 lead(s)
[5/10] Getting lead details...
      ✅ Lead details retrieved
[6/10] Updating lead...
      ✅ Lead updated
[7/10] Approving lead...
      ✅ Lead approved
[8/10] Testing bulk approve...
      ✅ Bulk approved 1 lead(s)
[9/10] Testing bulk reject...
      ✅ Bulk rejected 1 lead(s)
[10/10] Deleting lead...
      ✅ Lead deleted

============================================================
✅ ALL API TESTS PASSED
============================================================
```

**Status:** ☐ Pass

---

## Part 5: Frontend Testing (Docker)

### Step 1: Access Frontend
Navigate to: http://localhost:3000

**Status:** ☐ Frontend Loads

### Step 2: Test Authentication Flow

| Action | Steps | Expected | Status |
|--------|-------|----------|--------|
| Register | Click "Get Started", fill form | Redirects to campaigns | ☐ |
| Login | Enter credentials | Access granted | ☐ |

### Step 3: Test Campaign Creation

| Action | Steps | Expected | Status |
|--------|-------|----------|--------|
| Create Campaign | Click "New Campaign", fill form with 5+ keywords | Campaign appears in list | ☐ |

### Step 4: Test Lead Functionality

#### Option A: Create Test Leads via API Docs
1. Go to http://localhost:8000/docs
2. Login via `/auth/login` to get token
3. Authorize with token
4. Create a lead via `POST /leads`
5. Use this lead ID for frontend testing

#### Option B: Use Test Script
```bash
# Run the API test which creates test data
docker-compose exec backend python -m app.api.test_leads_api
# Don't cleanup - comment out cleanup section temporarily
```

### Step 5: Frontend Lead Pages

| Action | Steps | Expected | Status |
|--------|-------|----------|--------|
| Navigate to Leads | Go to http://localhost:3000/leads | Leads page loads | ☐ |
| Select Campaign | Choose your test campaign from dropdown | Leads display | ☐ |
| View Lead Detail | Click on a lead | Detail page loads | ☐ |
| Check All Fields | Scroll through page | All info visible | ☐ |
| Test Approve Button | Click "Approve" on eligible lead | Status changes | ☐ |
| Test Reject Button | Click "Reject" on eligible lead | Status changes | ☐ |
| Check Score Colors | View different scored leads | Colors correct | ☐ |
| Test Navigation | Use breadcrumb back links | Navigation works | ☐ |

---

## Part 6: View Logs (If Issues)

### Backend Logs
```bash
docker-compose logs -f backend
```

### Frontend Logs
```bash
docker-compose logs -f frontend
```

### Database Logs
```bash
docker-compose logs -f db
```

---

## 🔄 Restart Services (If Needed)

```bash
# Restart all
docker-compose restart

# Rebuild after code changes
docker-compose up -d --build

# Stop all
docker-compose down

# Stop and remove volumes (deletes data!)
docker-compose down -v
```

---

## ✅ Testing Checklist

- [ ] Services start successfully
- [ ] Database migration completes
- [ ] Lead model test passes
- [ ] Backend API test passes (all 10/10)
- [ ] Frontend loads at localhost:3000
- [ ] Authentication works
- [ ] Campaign creation works
- [ ] Leads list page works
- [ ] Lead detail page works
- [ ] Approve/Reject buttons work
- [ ] No console errors in browser

---

## 🚫 Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs backend

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Migration fails
```bash
# Reset migration
docker-compose exec backend alembic downgrade base
docker-compose exec backend alembic upgrade head
```

### Can't access frontend
```bash
# Check frontend is running
docker-compose ps frontend

# Check port
netstat -ano | findstr :3000
```

### Database connection issues
```bash
# Check database is healthy
docker-compose ps db

# Restart database
docker-compose restart db
```

---

## 📝 Quick Test Commands Reference

```bash
# Start everything
docker-compose up -d

# Check status
docker-compose ps

# Run migration
docker-compose exec backend alembic upgrade head

# Run model test
docker-compose exec backend python -m app.db.test_lead_model

# Run API test
docker-compose exec backend python -m app.api.test_leads_api

# View logs
docker-compose logs -f

# Stop everything
docker-compose down
```

---

## ✅ Ready for Iteration 1.4?

When all tests pass, you're ready to proceed to **Iteration 1.4: Search & Discovery**.

---

**Docker Testing Guide Version:** 1.0
**Date:** 2026-08-19
