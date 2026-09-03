# AI Lead Generation & Outreach Platform

A professional, scalable AI-powered B2B lead generation and outreach platform that discovers potential clients via web search, extracts public business contact information, uses AI to qualify and score leads, generates personalized outreach emails, and manages controlled email campaigns.

## Implementation Status

**Phase 1 (MVP) — ✅ COMPLETE**

| Iteration | Scope | Status |
|-----------|-------|--------|
| 1.0 – 1.2 | Foundation: auth, campaigns, frontend | ✅ Complete |
| 1.3 | Lead system (model, API, UI) | ✅ Complete |
| 1.4 | Search & discovery (multi-provider search agent, live progress tracking) | ✅ Complete |
| 1.5 | Crawling & extraction (robots.txt-compliant crawler, contact extraction, lead creation) | ✅ Complete |
| 1.6 | Export (CSV/Excel/JSON) & campaign statistics | ✅ Complete |
| Phase 2+ | AI qualification, email generation, sending & approval, analytics | ⬜ Not started |

Details: [development_plan.md](development_plan.md), [PHASE1_COMPLETE.md](PHASE1_COMPLETE.md), per-iteration summaries ([1.4](ITERATION_1.4_COMPLETE.md), [1.5](ITERATION_1.5_COMPLETE.md), [1.6](ITERATION_1.6_COMPLETE.md)).

## Features

- **Keyword-based Discovery**: Search for potential clients using 5-10 targeted keywords
- **Intelligent Crawling**: Extract public business contact information from websites
- **AI Lead Qualification**: Score and qualify leads using OpenAI GPT-4 or Anthropic Claude
- **Personalized Outreach**: Generate AI-powered personalized email templates
- **Multi-Channel Email**: Support for SMTP, Amazon SES, Gmail API, and Microsoft Graph
- **Human Approval Workflow**: Review and approve leads and emails before sending
- **Campaign Management**: Track campaigns, leads, emails, and responses
- **Reply Detection**: AI-powered email reply classification and lead status updates
- **Compliance Ready**: Suppression lists, unsubscribe handling, rate limiting, and robots.txt compliance

## Architecture

```
Frontend (Next.js + Tailwind) → FastAPI Backend → MySQL Database
                                  ↓
                             Celery Workers
                                  ↓
                    AI Agents (Search, Crawl, Qualify, Outreach, Reply)
                                  ↓
                    External APIs (OpenAI, Anthropic, Bing, SES, etc.)
```

## Technology Stack

- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Alembic
- **Database**: MySQL 8.0
- **Cache/Queue**: Redis 7, Celery
- **AI**: OpenAI GPT-4, Anthropic Claude (configurable)
- **Search**: Bing Search API, Google Programmable Search, SerpAPI
- **Email**: SMTP, Amazon SES, Gmail API, Microsoft Graph

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Node.js 20+ (for local development)

### 1. Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd ai-lead-generation

# Copy environment file
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Start with Docker

```bash
# Start all services
docker-compose up -d

# Check services are running
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 3. Initialize Database

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Create admin user (optional)
docker-compose exec backend python -m app.cli.create_admin
```

### 4. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Development Setup

### Backend (Local Development)

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run development server
uvicorn app.main:app --reload --port 8000

# Run Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# Run Celery beat (separate terminal)
celery -A app.tasks.celery_app beat --loglevel=info
```

### Frontend (Local Development)

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history
```

## Configuration

### Required API Keys

Configure these in your `.env` file:

**AI Providers** (at least one required):
- `OPENAI_API_KEY` - For lead qualification and email generation
- `ANTHROPIC_API_KEY` - Alternative AI provider

**Search Providers** (at least one required):
- `BING_SEARCH_API_KEY` - Bing Search API (1000 free calls/month)
- `GOOGLE_SEARCH_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID` - Google Custom Search
- `SERPAPI_KEY` - SerpAPI (aggregator)

**Email Providers** (at least one required):
- SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- SES: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Gmail: `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`
- Microsoft: `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`

## Project Structure

```
ai-lead-generation/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── agents/         # AI agents
│   │   ├── crawlers/       # Web crawlers
│   │   ├── db/             # Database models and migrations
│   │   ├── integrations/   # External service integrations
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── tasks/          # Celery background tasks
│   └── tests/              # Backend tests
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # Next.js app router
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks
│   │   └── lib/           # Utilities
└── docker-compose.yml     # Docker orchestration
```

## Usage

### 1. Create a Campaign

1. Navigate to the dashboard
2. Click "New Campaign"
3. Enter campaign name and 5-10 keywords
4. Click "Start Research"

### 2. Review Leads

1. Wait for research to complete
2. Go to Leads tab
3. Filter by score or status
4. Review AI qualification
5. Approve or reject leads

### 3. Generate Emails

1. Go to Templates tab
2. Generate AI templates
3. Customize templates
4. Preview personalized emails

### 4. Send Campaign

1. Select approved leads
2. Review personalized emails
3. Edit if needed
4. Approve campaign
5. Emails send automatically (respecting limits)

### 5. Monitor Replies

1. Check Replies tab for incoming responses
2. AI classifies reply sentiment
3. Interested leads are flagged
4. Follow up as needed

## Deployment

### Docker Production

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start production services
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes

See `k8s/` directory for Kubernetes manifests.

## Testing

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

## Security & Compliance

- **Rate Limiting**: Configurable per-user and per-IP limits
- **Email Compliance**: CAN-SPAM compliant, unsubscribe handling
- **Data Privacy**: GDPR features, data export/delete
- **Crawler Respect**: robots.txt compliance, rate limits
- **Authentication**: JWT tokens, bcrypt password hashing
- **API Key Encryption**: All external API keys encrypted at rest

## Monitoring & Logging

- Application logs: `/app/logs/app.log`
- Celery task logs: Viewable via Celery Flower (optional)
- Database logs: Available via Docker Compose

## License

Proprietary - All rights reserved

## Support

For issues and questions, contact the development team.
