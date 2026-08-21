# Local Development & Testing Guide

**Run and test SmartReach AI locally on your laptop (without Docker Compose)**

**📌 Updated for MariaDB 10.1.x compatibility**

---

## 📋 Prerequisites Check

First, verify you have the required software:

```bash
# Check Python (need 3.11+)
python --version

# Check Node.js (need 20+)
node --version

# Check npm
npm --version

# Check MariaDB/MySQL (optional, can use Docker for just database)
mysql --version
```

---

## 🐍 Part 1: Backend Setup (Local)

### Step 1: Navigate to Backend
```bash
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai\backend"
```

### Step 2: Create Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate

# You should see (.venv) in your terminal prompt
```

### Step 3: Install Dependencies
```bash
# Install all required packages
pip install -r requirements.txt

# If requirements.txt doesn't exist, install from pyproject.toml
pip install fastapi uvicorn[standard] sqlalchemy alembic aiomysql pymysql pydantic pydantic-settings python-jose passlib[bcrypt] python-dotenv httpx aiohttp beautifulsoup4 lxml openai anthropic redis celery
```

### Step 4: Create .env File
```bash
# Copy the example file
copy .env.example .env

# Edit with your settings
notepad .env
```

**For local testing, your .env should look like:**
```env
# Application
ENVIRONMENT=development
APP_NAME=AI Lead Generation Platform
API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# Security
SECRET_KEY=change-this-secret-key-for-local-development
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENCRYPTION_KEY=

# Database (MariaDB 10.1.x compatible - using Docker or local MariaDB/MySQL)
# The mariadb+aiomysql driver is compatible with both MariaDB and MySQL
DATABASE_URL=mariadb+aiomysql://root:btpacs4admin@localhost:3306/leadgen_db

# Redis (using Docker or skip for now)
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=http://localhost:3000

# AI Providers (optional for now)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Email Providers (optional for now)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
```

### Step 5: Start MySQL (Option A - Docker, Recommended)
```bash
# Navigate to project root
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai"

# Start only database and redis (detached mode)
docker-compose up -d db redis

# Verify they're running
docker-compose ps
```

### Step 5: Start MySQL (Option B - Local MariaDB/MySQL)
```bash
# If you have MariaDB or MySQL installed locally
# For MariaDB 10.1.22, this setup is fully compatible
mysql -u root -p

# In MySQL/MariaDB console:
CREATE DATABASE leadgen_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'leadgen_user'@'localhost' IDENTIFIED BY 'leadgen_pass';
GRANT ALL PRIVILEGES ON leadgen_db.* TO 'leadgen_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# Update your .env DATABASE_URL to:
# DATABASE_URL=mariadb+aiomysql://leadgen_user:leadgen_pass@localhost:3306/leadgen_db
```

### Step 6: Run Database Migration
```bash
# Navigate back to backend
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai\backend"

# Make sure virtual environment is activated
.venv\Scripts\activate

# Run migration
alembic upgrade head

# Verify migration
alembic current
# Expected: Revision: 001
```

### Step 7: Test Backend Model
```bash
# Run lead model test
python -m app.db.test_lead_model

# Expected output: All tests pass ✅
```

### Step 8: Start FastAPI Server
```bash
# In backend directory, with virtual env activated
uvicorn app.main:app --reload --port 8000

# You should see:
# INFO: Started server process
# INFO: Uvicorn running on http://0.0.0.0:8000
```

### Step 9: Verify Backend
Open browser: http://localhost:8000/docs

**Expected:** Swagger UI with all endpoints

---

## 🎨 Part 2: Frontend Setup (Local)

### Step 1: Navigate to Frontend
```bash
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai\frontend"
```

### Step 2: Install Dependencies
```bash
npm install
```

### Step 3: Create Environment File
```bash
# Create .env.local file
notepad .env.local
```

**Add this to .env.local:**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 4: Start Frontend Dev Server
```bash
npm run dev

# You should see:
# ready - started server on 0.0.0.0:3000, url: http://localhost:3000
```

### Step 5: Verify Frontend
Open browser: http://localhost:3000

**Expected:** Landing page with login/register options

---

## 🧪 Part 3: Backend API Testing (Local)

### Option A: Using Swagger UI (Recommended)
1. Navigate to http://localhost:8000/docs
2. Expand `/auth/register` endpoint
3. Click "Try it out"
4. Enter test data:
   ```json
   {
     "email": "test@example.com",
     "password": "Test123!",
     "name": "Test User"
   }
   ```
5. Click "Execute"
6. Copy the `access_token` from response
7. Click "Authorize" button
8. Enter: `Bearer YOUR_ACCESS_TOKEN`
9. Test other endpoints

### Option B: Using API Test Script
```bash
# Navigate to backend
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai\backend"

# Activate virtual environment
.venv\Scripts\activate

# Run API test
python -m app.api.test_leads_api

# Expected: All 10/10 tests pass
```

### Option C: Using cURL
```bash
# Test health
curl http://localhost:8000/health

# Test registration
curl -X POST http://localhost:8000/api/v1/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@example.com\",\"password\":\"Test123!\",\"name\":\"Test User\"}"

# Test login (save the token)
curl -X POST http://localhost:8000/api/v1/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@example.com\",\"password\":\"Test123!\"}"
```

---

## 🎨 Part 4: Frontend Testing (Local)

### Step 1: Test Authentication Flow
1. Navigate to http://localhost:3000
2. Click "Get Started"
3. Fill registration form:
   - Email: `test@example.com`
   - Password: `Test123!`
   - Name: `Test User`
4. Submit
5. Login with credentials
6. **Expected:** Redirected to campaigns page

### Step 2: Create a Campaign
1. Click "New Campaign"
2. Fill form:
   - Name: `Test Campaign`
   - Description: `Testing locally`
   - Keywords: `test`, `local`, `development` (add 2 more to make 5)
3. Submit
4. **Expected:** Campaign appears in list

### Step 3: Test Leads Navigation
1. On campaign card, click "Leads →"
2. **Expected:** Leads page loads with "No leads found" message
3. Click "← Back to Campaign"
4. **Expected:** Returns to campaign detail

### Step 4: Test Campaign Detail Navigation
1. Click "View Details →" on campaign
2. **Expected:** Campaign detail page loads
3. Click "View Leads (0)" button
4. **Expected:** Leads page loads

---

## 🔬 Part 5: Integration Testing (Local)

### Create Test Lead via API
1. Go to http://localhost:8000/docs
2. Login to get token
3. Authorize with token
4. Use `POST /api/v1/campaigns` to create a campaign (save the campaign ID)
5. Use `POST /api/v1/leads` with:
   ```json
   {
     "campaign_id": 1,
     "keyword": "test",
     "source_url": "https://example.com",
     "organization_name": "Test Organization LLC",
     "website": "https://example.com",
     "contact_name": "John Smith",
     "job_title": "CTO",
     "email": "john@example.com",
     "lead_score": 85
   }
   ```

### View Lead in Frontend
1. Navigate to http://localhost:3000/leads?campaign_id=1
2. **Expected:** See the lead you just created
3. Click on the lead
4. **Expected:** Lead detail page loads with all information
5. Click "Approve" button
6. **Expected:** Status changes to "Approved"

---

## 🐛 Troubleshooting (Local Development)

### Backend Issues

**Problem:** Module not found errors
```bash
# Solution: Make sure virtual environment is activated
.venv\Scripts\activate

# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

**Problem:** Database connection failed
```bash
# Solution 1: Check database is running
docker-compose ps db

# Solution 2: Check DATABASE_URL in .env
# Should be: mariadb+aiomysql://user:pass@localhost:3306/dbname

# Solution 3: Test MySQL/MariaDB connection
mysql -u root -p -e "SELECT 1;"
```

**Problem:** Migration fails
```bash
# Solution: Reset and retry
alembic downgrade base
alembic upgrade head
```

### Frontend Issues

**Problem:** Port 3000 already in use
```bash
# Solution 1: Find and kill process
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Solution 2: Use different port
npm run dev -- -p 3001
```

**Problem:** Cannot connect to backend
```bash
# Solution 1: Check .env.local has correct API URL
# Should be: NEXT_PUBLIC_API_URL=http://localhost:8000

# Solution 2: Verify backend is running
curl http://localhost:8000/health

# Solution 3: Check browser console for CORS errors
```

---

## 📝 Quick Commands Reference (Local)

### Backend
```bash
# Navigate
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai\backend"

# Activate venv
.venv\Scripts\activate

# Start server
uvicorn app.main:app --reload --port 8000

# Run model test
python -m app.db.test_lead_model

# Run API test
python -m app.api.test_leads_api

# Migration
alembic upgrade head
```

### Frontend
```bash
# Navigate
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai\frontend"

# Install
npm install

# Start dev server
npm run dev

# Clear cache
rm -rf .next
npm run dev
```

### Database (Docker)
```bash
# Navigate to project root
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai"

# Start database only
docker-compose up -d db redis

# Check status
docker-compose ps

# View logs
docker-compose logs -f db

# Stop
docker-compose down
```

---

## ✅ Local Testing Checklist

- [ ] Python virtual environment activated
- [ ] Backend dependencies installed
- [ ] .env file configured
- [ ] Database running (Docker or local)
- [ ] Migration completed successfully
- [ ] Backend model test passes
- [ ] Backend API test passes (10/10)
- [ ] Backend server running on port 8000
- [ ] Frontend dependencies installed
- [ ] .env.local configured
- [ ] Frontend server running on port 3000
- [ ] Can register/login successfully
- [ ] Can create campaign
- [ ] Can navigate to leads page
- [ ] Can view lead details
- [ ] Approve/reject buttons work

---

## 🚀 After Local Testing Passes

Once all local tests pass, you can:
1. Commit your changes
2. Push to git (if using version control)
3. Then test with Docker Compose using the [ITERATION_1.3_DOCKER_TESTING.md](ITERATION_1.3_DOCKER_TESTING.md) guide

---

**Happy Local Testing! 🎯**
