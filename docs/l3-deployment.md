# L3 Deployment Guide

This document describes how to deploy the Kimi Production-Grade Agent System v3.x L3 frontend layer.

## Architecture Overview

```
+------------+      +------------------+      +------------------+
|   User     |----->|  Next.js Frontend |----->|  FastAPI Backend |
|  Browser   |      |  (apps/frontend)  |      |  (apps/backend)  |
+------------+      +------------------+      +------------------+
                              |                         |
                              v                         v
                       [Optional]                Kimi API
                    Streamlit Local
                     (apps/dashboard.py)
```

The frontend **never** calls the Kimi API directly. All requests go through the backend API layer.

## Deployment Modes

### Mode 1: Local Streamlit (Development / Quick Validation)

For rapid local validation and debugging:

```powershell
# 1. Install dependencies
pip install streamlit requests

# 2. Start the backend API
cd apps/backend
uvicorn main:app --reload --port 8000

# 3. In a new terminal, start the Streamlit dashboard
streamlit run apps/dashboard.py --server.port 8501

# 4. Open browser to http://localhost:8501```

**Note**: Streamlit is for local use only. See [KL-L3-002](l3-known-limits.md).

### Mode 2: Local Next.js (Development)

For full Next.js frontend development:

```powershell
# 1. Start the backend API
cd apps/backend
uvicorn main:app --reload --port 8000

# 2. In a new terminal, start the Next.js dev server
cd apps/frontend
npm install
npm run dev

# 3. Open browser to http://localhost:3000```

### Mode 3: Docker Production Deployment

Build and run with Docker:

```powershell
# Build frontend image
cd apps/frontend
docker build -t kimi-agent-pack-frontend .

# Build backend image
cd apps/backend
docker build -t kimi-agent-pack-backend .

# Run with docker-compose
docker-compose up -d```

#### Example docker-compose.yml

```yaml
version: '3.8'
services:
  backend:
    image: kimi-agent-pack-backend
    ports:
      - "8000:8000"
    environment:
      - API_URL=http://backend:8000
      - DATABASE_URL=sqlite:///./data/agent.db
    volumes:
      - ./data:/app/data

  frontend:
    image: kimi-agent-pack-frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
```

## Playwright CI Setup

Browser automation tests require Playwright with browser binaries.

### Container Environment

Use the official Playwright Docker image for CI:

```yaml
# .github/workflows/ci.yml example
jobs:
  e2e:
    runs-on: ubuntu-latest
    container:
      image: mcr.microsoft.com/playwright:v1.40.0-jammy
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npx playwright install --with-deps chromium
      - run: npx playwright test
```

### Browser Download Strategy

Option A: Pre-baked image (recommended for CI)
```powershell
# Use the official image which includes browsers
docker run -it mcr.microsoft.com/playwright:v1.40.0-jammy```

Option B: Install on demand
```powershell
npm install @playwright/test
npx playwright install --with-deps chromium```

Option C: Cache browsers in CI
```yaml
- name: Cache Playwright browsers
  uses: actions/cache@v3
  id: playwright-cache
  with:
    path: ~/.cache/ms-playwright
    key: ${{ runner.os }}-playwright-${{ hashFiles('**/package-lock.json') }}
- run: npx playwright install --with-deps chromium
  if: steps.playwright-cache.outputs.cache-hit != 'true'
```

## Environment Variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `API_URL` | `http://localhost:8000` | Internal API base URL |
| `DATABASE_URL` | `sqlite:///./data/agent.db` | Database connection string |
| `KIMI_API_KEY` | (required) | Kimi API key |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_CONCURRENT_JOBS` | `3` | Maximum concurrent runner jobs |

### Frontend (Next.js)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL (must be public) |
| `NEXT_PUBLIC_APP_VERSION` | `3.0.0` | App version display |

### Streamlit

| Variable | Default | Description |
|----------|---------|-------------|
| `API_URL` | `http://localhost:8000` | Backend API base URL |
| `STREAMLIT_SERVER_PORT` | `8501` | Streamlit server port |

## Security Considerations

1. **Never expose `KIMI_API_KEY` to the frontend**. All Kimi API calls go through the backend.
2. **Use HTTPS in production** for both frontend and backend.
3. **The Script Console only executes whitelisted scripts**. The whitelist is configured server-side.
4. **Memory Review UI is read-only**. Approve/reject operations require backend API access.
5. **Enable CORS only for trusted origins** in the backend configuration.

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Frontend shows "API Error" | Backend not running | Start backend: `uvicorn main:app --reload` |
| CORS errors | Backend CORS not configured | Add frontend origin to backend CORS whitelist |
| Streamlit slow | Large artifact rendering | Reduce `limit` parameter in artifact queries |
| Next.js build fails | Missing env var | Set `NEXT_PUBLIC_API_URL` |
| Playwright tests timeout | Browser not installed | Run `npx playwright install --with-deps` |

## Migration Notes

### From v2.x to v3.0
- Replace standalone Streamlit with Next.js frontend for production
- Update API endpoints from `/v1/*` to `/api/*`
- Environment variable names have changed; update your `.env` files

### From v3.0 to v3.x (Future)
- PostgreSQL migration will be provided as a migration script
- WebSocket real-time updates will be opt-in initially
