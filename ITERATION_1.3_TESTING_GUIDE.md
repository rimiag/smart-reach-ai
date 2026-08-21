# Iteration 1.3 - Quick Testing Guide

**🚀 Ready to test Iteration 1.3: Lead System**

---

## 📋 Testing Checklist

Use this checklist to systematically test Iteration 1.3.

---

## Part 1: Database & Migration (5 minutes)

### Step 1: Navigate to Backend
```bash
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai\backend"
```

### Step 2: Check Migration Status
```bash
alembic current
```
**Expected:** `Revision: No revision info` (before migration)

### Step 3: Run Migration
```bash
alembic upgrade head
```
**Expected:** `Running upgrade... -> 001`

### Step 4: Verify Migration
```bash
alembic current
```
**Expected:** `Revision: 001`

---

## Part 2: Backend Model Test (5 minutes)

### Step 1: Run Lead Model Test
```bash
python -m app.db.test_lead_model
```

**Expected Output:**
```
============================================================
Iteration 1.3 - Lead Model Test
============================================================

[1] Checking for test user...
   ✅ Test user created
[2] Creating test campaign...
   ✅ Campaign created (ID: 1)
[3] Creating test lead...
   ✅ Lead created (ID: 1)
[4] Reading lead back...
   ✅ Lead retrieved successfully
[5] Testing lead update...
   ✅ Lead updated - Status: qualified
[6] Testing lead approval...
   ✅ Lead approved - Status: approved
[7] Testing campaign relationship...
   ✅ Campaign has 1 lead(s)
[8] Cleanup...
   ✅ Test data cleaned up

============================================================
✅ ALL TESTS PASSED - Iteration 1.3 Lead Model Working!
============================================================
```

**Status:** ☐ Pass

---

## Part 3: Backend API Test (10 minutes)

### Step 1: Start FastAPI Server
```bash
uvicorn app.main:app --reload --port 8000
```
**Keep this running in a separate terminal**

### Step 2: Verify Server Running
Open browser: http://localhost:8000/docs

**Expected:** Swagger UI with all endpoints visible

**Status:** ☐ API Docs Load

### Step 3: Run API Test Script
Open a new terminal:
```bash
cd backend
python -m app.api.test_leads_api
```

**Expected Output:**
```
============================================================
Iteration 1.3 - Leads API Test
============================================================

[1/10] Testing authentication...
      ✅ Authentication successful
[2/10] Creating test campaign...
      ✅ Campaign created (ID: 1)
[3/10] Creating lead...
      ✅ Lead created (ID: 1)
[4/10] Listing leads...
      ✅ Retrieved 1 lead(s)
[5/10] Getting lead details...
      ✅ Lead details retrieved
[6/10] Updating lead...
      ✅ Lead updated
[7/10] Approving lead...
      ✅ Lead approved - Status: approved
[8/10] Testing bulk approve...
      ✅ Bulk approved 1 lead(s)
[9/10] Testing bulk reject...
      ✅ Bulk rejected 1 lead(s)
[10/10] Deleting lead...
      ✅ Lead deleted

============================================================
✅ ALL API TESTS PASSED - Iteration 1.3 API Working!
============================================================
```

**Status:** ☐ Pass

---

## Part 4: Frontend Testing (10 minutes)

### Step 1: Start Frontend Dev Server
```bash
cd frontend
npm run dev
```
**Keep this running**

### Step 2: Open Application
Navigate to: http://localhost:3000

**Status:** ☐ Frontend Loads

### Step 3: Test Authentication Flow

| Action | Steps | Expected | Status |
|--------|-------|----------|--------|
| Register | Click "Get Started", fill form | Redirects to campaigns | ☐ |
| Login | Enter credentials | Access granted | ☐ |

### Step 4: Test Campaign Creation

| Action | Steps | Expected | Status |
|--------|-------|----------|--------|
| Create Campaign | Click "New Campaign", fill form | Campaign appears in list | ☐ |

### Step 5: Test Leads Pages

| Action | Steps | Expected | Status |
|--------|-------|----------|--------|
| Navigate to Leads | Click on campaign, then "View Details" | Campaign detail loads | ☐ |
| Create Test Lead | Use API or Swagger to create a lead | Lead ready for testing | ☐ |
| View Leads List | Navigate to /leads | Leads list page loads | ☐ |
| Select Campaign | Choose your test campaign | Leads display | ☐ |
| View Lead Detail | Click on a lead | Detail page loads | ☐ |
| Check Lead Info | Verify all fields display | All info visible | ☐ |
| Test Approve | Click "Approve" button | Status changes to approved | ☐ |
| Test Reject | (create new lead) Click "Reject" | Status changes to rejected | ☐ |
| Check Score Color | View leads with different scores | Colors match score | ☐ |
| Test Navigation | Use breadcrumb links | Navigation works | ☐ |

---

## Part 5: Integration Test (5 minutes)

### End-to-End Flow Test

1. **Register** → **Create Campaign** → **Generate Leads** → **Review** → **Approve** → **Send**

**Status:** ☐ Complete Flow Works

---

## ✅ Sign-Off

### All Tests Passed?

- [ ] Database migration successful
- [ ] Lead model test passed
- [ ] API test passed (all 10/10)
- [ ] Frontend loads without errors
- [ ] Authentication works
- [ ] Campaign creation works
- [ ] Leads pages work
- [ ] Approve/Reject functions work

### Issues Found:

| # | Issue | Severity | Fixed? |
|---|-------|----------|--------|
| 1 | | | |
| 2 | | | |

---

## 📝 Notes

```
Add any observations or issues during testing here:
```

---

## 🚫 Troubleshooting

### Server won't start
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill process if needed
taskkill /PID <PID> /F
```

### Migration fails
```bash
# Reset database
alembic downgrade base
alembic upgrade head
```

### Frontend errors
```bash
# Clear cache and rebuild
cd frontend
rm -rf .next
npm run dev
```

---

## ✅ Ready for Iteration 1.4?

When all tests pass, you're ready to proceed to **Iteration 1.4: Search & Discovery**.

---

**Testing Guide Version:** 1.0
**Date:** 2026-08-19
