# Async Document Processor - Integration Test & Documentation

## 🚀 Setup Complete!

The frontend and backend have been successfully integrated and are now running in Docker containers.

---

## 📋 Architecture Overview

### Services Running:

1. **PostgreSQL (Port 5432)** - Relational database
2. **Redis (Port 6379)** - Celery message broker & caching
3. **FastAPI Backend (Port 8000)** - API server with Gunicorn + Uvicorn
4. **Celery Worker** - Background job processor
5. **Vite + React Frontend (Port 5173)** - Modern UI

### Network: `async-doc-processor-net`
All services communicate internally via the Docker network.

---

## 🔌 API Integration

### Base URLs:
- **Backend API**: `http://localhost:8000`
- **Frontend App**: `http://localhost:5173`
- **Internal API URL (from frontend)**: `http://api:8000`

### API Endpoints:

#### Health Check
```bash
GET http://localhost:8000/health
# Response: { "status": "ok" }
```

#### Jobs Management
```bash
GET /api/v1/jobs                    # List all jobs
GET /api/v1/jobs/{job_id}           # Get job details
POST /api/v1/jobs/{job_id}/retry    # Retry failed job
POST /api/v1/jobs/{job_id}/cancel   # Cancel job
```

#### Results
```bash
GET /api/v1/jobs/{job_id}/result            # Get job result
PUT /api/v1/jobs/{job_id}/result            # Update result
POST /api/v1/jobs/{job_id}/result/finalize  # Finalize result
```

#### Export
```bash
POST /api/v1/export/json  # Export as JSON
POST /api/v1/export/csv   # Export as CSV
```

---

## 🔧 Configuration

### Environment Variables (.env)
```env
# Application
APP_ENV=development
SECRET_KEY=your-super-secret-key-change-me-in-production-12345678901234567890
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=docprocessor
POSTGRES_USER=docuser
POSTGRES_PASSWORD=docpassword123

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## 📱 Frontend API Client

### API Client Utility (`src/lib/api-client.ts`)
The frontend uses a centralized API client that handles:
- Automatic URL construction with `VITE_API_URL`
- Request/response formatting
- Error handling

### Usage Example:
```typescript
import { get, post } from '@/lib/api-client';

// GET request
const jobs = await get('/api/v1/jobs');

// POST request
const result = await post('/api/v1/jobs/{id}/retry');
```

### API Files Updated:
- ✅ `src/api/jobs.ts` - Job operations (fetch, retry, cancel)
- ✅ `src/api/documents.ts` - Result operations (fetch, update, finalize)
- ✅ `src/api/export.ts` - Export operations (JSON, CSV)

---

## ✅ Integration Testing

### Test 1: Backend Health Check
```bash
curl http://localhost:8000/health
# Expected: { "status": "ok" }
```

### Test 2: Get Jobs List
```bash
curl http://localhost:8000/api/v1/jobs
# Expected: List of jobs with pagination
```

### Test 3: Frontend Loads
```bash
Open http://localhost:5173 in browser
# Expected: React application loads successfully
```

### Test 4: Frontend → Backend Communication
1. Navigate to Frontend (http://localhost:5173)
2. Check Browser DevTools Console for API calls
3. Verify requests are made to `http://localhost:8000/api/v1/*`
4. Check Network tab for successful responses

---

## 📊 Docker Compose Services

### Service Dependencies:
```
postgres (healthy) ──┐
                    ├─→ api (healthy) ──→ worker
redis   (healthy) ──┤
                    ├─→ frontend
                    
worker depends on api → ensures DB migrations complete before job processing
```

### Health Checks:
- **API**: `curl -f http://localhost:8000/health` (every 10s)
- **PostgreSQL**: `pg_isready` (every 5s)
- **Redis**: `redis-cli ping` (every 5s)
- **Frontend**: `wget --quiet --tries=1 --spider http://localhost:5173` (every 30s)

---

## 🔄 Full Request Flow

### Creating a Document (Example):
1. **Frontend** sends `POST /api/v1/documents`
2. **API** validates and stores document metadata
3. **API** creates Job record
4. **API** publishes message to Redis (Celery broker)
5. **Worker** picks up task from Redis queue
6. **Worker** processes document in background
7. **Frontend** polls `GET /api/v1/jobs/{id}` for progress
8. **Frontend** displays real-time progress to user

---

## 🐛 Troubleshooting

### If Frontend can't reach Backend:
1. Check CORS is enabled in `.env`: `CORS_ORIGINS=http://localhost:5173`
2. Check Backend is running: `curl http://localhost:8000/health`
3. Check Network (DevTools) for actual error messages

### If Services Don't Start:
```bash
# Check container logs
docker compose logs api       # API logs
docker compose logs frontend  # Frontend logs
docker compose logs worker    # Worker logs

# Restart services
docker compose restart

# Full rebuild
docker compose down -v
docker compose up --build
```

### Common Issues:

| Issue | Solution |
|-------|----------|
| Port already in use | Change port in docker-compose.yml or kill existing process |
| npm package errors | Docker rebuilds automatically; try `docker compose up --build` |
| Database connection error | Ensure `postgres` service is healthy before `api` starts |
| CORS errors | Add frontend URL to `CORS_ORIGINS` in `.env` |

---

## 📈 Monitoring

### Check Service Status:
```bash
docker compose ps

# Output columns: Service, Status, Health
# api           "gunicorn..." Up (healthy)
# frontend      "npm run..." Up (running)
# postgres      "postgres"   Up (healthy)
# redis         "redis --"   Up (healthy)
# worker        "celery -A"  Up (running)
```

### View Real-time Logs:
```bash
docker compose logs -f       # All services
docker compose logs -f api   # Specific service
```

---

## 🚀 Test Endpoints via cURL

### List Jobs
```bash
curl -X GET http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json"
```

### Get Job Detail
```bash
curl -X GET http://localhost:8000/api/v1/jobs/{job_id} \
  -H "Content-Type: application/json"
```

### Frontend API Test
```bash
# Open browser console and run:
fetch('http://localhost:8000/api/v1/jobs')
  .then(r => r.json())
  .then(data => console.log(data))
```

---

## 📦 Files Modified/Created

### Backend:
- ✅ `backend/Dockerfile` - Created with production & development stages
- ✅ `backend/app/main.py` - Added CORS middleware & API prefix

### Frontend:
- ✅ `frontend/Dockerfile` - Created with build & development stages
- ✅ `frontend/src/lib/api-client.ts` - Created API utilities
- ✅ `frontend/src/api/jobs.ts` - Updated to use real API
- ✅ `frontend/src/api/documents.ts` - Updated to use real API
- ✅ `frontend/src/api/export.ts` - Updated to use real API

### Configuration:
- ✅ `.env` - Created with all required variables
- ✅ `docker-compose.yml` - Updated with correct Vite configuration

---

## 🎯 Summary

✅ **Frontend** and **Backend** fully integrated
✅ **Docker Compose** orchestrates all 5 services
✅ **CORS** properly configured
✅ **API URLs** automatically resolved
✅ **Hot reload** enabled for development
✅ **Database migrations** run automatically
✅ **Background jobs** processed by Celery

### Access Points:
- 🌐 Frontend: http://localhost:5173
- 🔌 Backend API: http://localhost:8000
- 📊 Database: localhost:5432 (docuser/docpassword123)
- ⚡ Redis: localhost:6379

The system is ready for testing!

---

## 🧪 Next Steps

1. Open http://localhost:5173 in your browser
2. Check DevTools Console for any errors
3. Navigate through the app and verify all features work
4. Use curl to test specific API endpoints
5. Monitor logs with `docker compose logs -f`

Happy testing! 🎉
