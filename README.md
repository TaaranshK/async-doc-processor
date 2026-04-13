# 📄 Async Document Processor

> **High-performance asynchronous document processing pipeline** with real-time progress tracking and multi-format export capabilities.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791?logo=postgresql)
![React](https://img.shields.io/badge/React-18.3+-61DAFB?logo=react)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)

## 🎯 Overview

**Async Document Processor** is a full-stack application that processes documents asynchronously, extracts structured data using AI/ML, and provides real-time progress tracking via Server-Sent Events (SSE). Perfect for high-volume document processing workflows.

### Key Capabilities

- 📤 **Async Document Upload** - Multipart file uploads with automatic validation
- 🧠 **Intelligent Extraction** - Extract title, category, keywords, and metadata
- ⚡ **Real-time Progress** - Server-Sent Events (SSE) for live job status updates
- 📊 **Multi-format Export** - Export results as JSON or CSV
- 🔐 **JWT Authentication** - Secure token-based API access
- 🗄️ **PostgreSQL Persistence** - Reliable data storage with JSONB support
- 🔄 **Job Lifecycle Management** - Create, monitor, retry, and finalize jobs
- 📱 **Modern Web UI** - React frontend with Vite and TypeScript

---

## 🏗️ Architecture

### Technology Stack

| Layer              | Technology                     | Purpose                          |
| ------------------ | ------------------------------ | -------------------------------- |
| **Frontend**       | React 18.3 + TypeScript + Vite | Modern, responsive web interface |
| **Backend API**    | FastAPI 0.115 + Uvicorn        | High-performance async REST API  |
| **Database**       | PostgreSQL 14 + SQLAlchemy 2.0 | Persistent data storage          |
| **Async Queue**    | Celery + Redis                 | Background job processing        |
| **Authentication** | JWT (HS256)                    | Token-based API security         |

### System Architecture

```
┌─────────────────┐
│   React UI      │  Frontend (Port 5173/8080)
│   (Vite)        │
└────────┬────────┘
         │ HTTP/WebSocket
         │
┌────────▼──────────────────┐
│   FastAPI Backend         │  Port 8000
│  ┌──────────────────────┐ │
│  │ Auth Router          │ │
│  │ Document Router      │ │
│  │ Job Router           │ │
│  │ Export Router        │ │
│  └──────────────────────┘ │
└────────┬──────────────────┘
         │
    ┌────┴──────┬──────────┐
    │            │          │
┌───▼───┐   ┌───▼───┐  ┌──▼────┐
│ Async │   │PostgreSQL│  Redis
│Queue  │   │   DB   │  Queue
└───────┘   └────────┘  └───────┘
    │            │          │
┌───▼────────────▼──────────▼────┐
│  Background Workers             │
│  (Document Processing)          │
└─────────────────────────────────┘
```

---

## 📋 Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for frontend)
- **PostgreSQL 14+**
- **Redis 7+** (for task queue)
- **Git**

### System Requirements

- **OS**: Windows, macOS, or Linux
- **RAM**: 2GB minimum (4GB recommended)
- **Storage**: 1GB for dependencies + document storage space
- **Network**: Internet connection for initial setup

---

## 🚀 Getting Started (Complete Setup Guide)

Follow these steps **exactly** to get everything running. Estimated time: **10-15 minutes**.

### ⚠️ Prerequisites Check

Before starting, verify you have these installed:

```powershell
# Check Python version (should be 3.11 or higher)
python --version

# Check Node version (should be 18 or higher)
node --version

# Check PostgreSQL is running (should return version)
psql --version

# Verify PostgreSQL is running
psql -U postgres -c "SELECT version();"
```

If any command fails, install the missing software from:

- Python: https://www.python.org/downloads/
- Node.js: https://nodejs.org/
- PostgreSQL: https://www.postgresql.org/download/

---

### Step 1: Clone & Navigate to Project

```powershell
# Clone the repository
git clone <repository-url>
cd async-doc-processor

# Verify you're in the right directory
# You should see: backend/, frontend/, README.md, etc.
ls
```

---

### Step 2: Create Virtual Environment (Backend)

```powershell
# Create Python virtual environment named 'ven'
python -m venv ven

# Activate virtual environment
# On Windows:
.\ven\Scripts\Activate.ps1

# You should see (ven) at the start of your prompt now
# If you get an execution policy error, run this first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Verify activation:**

```powershell
# This should show the venv Python path
python -c "import sys; print(sys.executable)"
```

---

### Step 3: Install Backend Dependencies

```powershell
# Navigate to backend directory
cd backend

# Install all Python packages
pip install -r requirements.txt

# This will take 2-3 minutes. Wait for it to complete.
```

---

### Step 4: Install Frontend Dependencies

```powershell
# Navigate to frontend directory
cd ../frontend

# Install Node packages
npm install

# This will take 1-2 minutes. Wait for it to complete.

# Go back to root directory
cd ..
```

---

### Step 5: Create Environment Configuration File

**Windows PowerShell:**

```powershell
# Create .env file in the root directory
@"
# Application
APP_ENV=development

# JWT Security (keep these for development)
SECRET_KEY=your-super-secret-key-change-this-in-production-12345678
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=HS256

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000,http://127.0.0.1:5173

# PostgreSQL (Update password to YOUR Postgres password)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=docprocessor
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password_here

# Redis (optional for development)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
"@ | Out-File -FilePath .env -Encoding UTF8
```

**Or manually create `.env` file:**

- Create a new file named `.env` in the root directory
- Copy the content above into it
- Replace `your_postgres_password_here` with your actual PostgreSQL password

---

### Step 6: Verify Database Connection

```powershell
# Verify PostgreSQL is running by testing connection
python backend/test_db_connection.py

# You should see:
# ✓ Connection successful!
# ✓ Database 'docprocessor' already exists.

# If database doesn't exist, it will be created automatically.
```

---

### Step 7: Initialize Database Tables

```powershell
# Create all database tables
python init_db.py

# You should see:
# DATABASE_URL: postgresql+asyncpg://postgres:...
# --- Testing SQLAlchemy async engine ---
# Creating tables...
# ✓ Tables created successfully!
# ✓ Database initialization complete!
```

---

### Step 8: Start Backend Server

**Open a NEW PowerShell terminal and run:**

```powershell
# Navigate to backend directory
cd async-doc-processor\backend

# Activate virtual environment
.\ven\Scripts\Activate.ps1

# Start the server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# You should see:
# INFO:     Will watch for changes in these directories: [...]
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# INFO:     Started server process
# INFO:     Application startup complete.
```

✅ **Backend is now running!** Keep this terminal open.

**Access API documentation:**

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health Check: http://127.0.0.1:8000/health

---

### Step 9: Start Frontend Server

**Open a DIFFERENT PowerShell terminal and run:**

```powershell
# Navigate to frontend directory
cd async-doc-processor\frontend

# Start development server
npm run dev

# You should see:
# VITE v5.4.19  ready in XXX ms
# ➜  Local:   http://localhost:5173/
# ➜  press h + enter to show help
```

✅ **Frontend is now running!** Keep this terminal open.

---

### Step 10: Test Everything Works

**Open a THIRD PowerShell terminal and run:**

```powershell
# Navigate to root directory
cd async-doc-processor

# Run API tests
python test_apis.py

# You should see all 8 tests pass:
# ✅ PASS - Health Check
# ✅ PASS - List Jobs
# ✅ PASS - Register User
# ✅ PASS - Login
# ✅ PASS - Invalid Login
# ✅ PASS - Invalid Upload
# ✅ PASS - Get Non-existent Job
# ✅ PASS - List with Filters
#
# Total: 8/8 tests passed
# 🎉 All tests passed!
```

---

### 🎉 You're All Set!

Your complete setup is running on:

| Service         | URL                         | Purpose                  |
| --------------- | --------------------------- | ------------------------ |
| **Frontend**    | http://localhost:5173       | React web application    |
| **Backend API** | http://127.0.0.1:8000       | REST API server          |
| **API Docs**    | http://127.0.0.1:8000/docs  | Swagger UI documentation |
| **ReDoc**       | http://127.0.0.1:8000/redoc | Alternative API docs     |

---

## 🧪 Quick Test Commands

Now that everything is running, try these:

### Register a User

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d '{
    "email":"test@example.com",
    "password":"TestPass123!@",
    "full_name":"Test User"
  }'

# Expected response: 201 Created with user ID
```

### Login

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{
    "email":"test@example.com",
    "password":"TestPass123!@"
  }'

# Expected response: 200 OK with access_token and refresh_token
```

### Check API Health

```powershell
curl http://127.0.0.1:8000/health

# Expected response: {"status":"ok"}
```

---

## ⚠️ Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'app'"

**Solution:**

```powershell
# Make sure you're in the backend directory
cd backend

# Verify virtual environment is activated (should see (ven) in prompt)
.\ven\Scripts\Activate.ps1

# Try running again
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

### Issue: "Cannot find path '...ven\Scripts\Activate.ps1'"

**Solution:**

```powershell
# Recreate virtual environment
python -m venv ven

# Then activate
.\ven\Scripts\Activate.ps1
```

---

### Issue: "Error: listen EADDRINUSE: address already in use :::5173" (Frontend)

**Solution:**

```powershell
# Use a different port
npm run dev -- --port 5174
```

---

### Issue: "Error: [WinError 10013] socket access denied" (Backend)

**Solution:**

```powershell
# Use localhost instead of 0.0.0.0
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

### Issue: "FATAL: role 'postgres' does not exist"

**Solution:**

```powershell
# Check PostgreSQL is installed and running
psql --version

# Try with default admin user (depends on your setup)
# Or reinstall PostgreSQL if needed
```

---

## 🛑 Stopping Services

To stop any service, press **Ctrl+C** in its terminal.

```powershell
# Stop backend (in backend terminal)
Ctrl+C

# Stop frontend (in frontend terminal)
Ctrl+C

# Deactivate virtual environment
deactivate
```

---

## 🔄 Restarting Everything

If something goes wrong, restart in this order:

```powershell
# Terminal 1: Stop and restart backend
cd async-doc-processor\backend
.\ven\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: Stop and restart frontend
cd async-doc-processor\frontend
npm run dev

# Terminal 3: Re-run tests
cd async-doc-processor
python test_apis.py
```

---

## 📚 API Documentation

### Base URL

```
http://localhost:8000/api/v1
```

### Authentication

All protected endpoints require JWT token in Authorization header:

```
Authorization: Bearer {access_token}
```

### Core Endpoints

#### 🔐 Authentication

```bash
# Register User
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!@",
  "full_name": "John Doe"
}

# Login
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!@"
}

Response:
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer"
}

# Refresh Token
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGci..."
}
```

#### 📤 Documents

```bash
# Upload Document
POST /documents/upload
Content-Type: multipart/form-data
Authorization: Bearer {token}

Body:
  files: [binary_file_data]

Response:
{
  "documents": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "document.pdf",
      "file_type": "application/pdf",
      "file_size": 2048576,
      "job_id": "550e8400-e29b-41d4-a716-446655440001"
    }
  ]
}
```

#### 💼 Jobs

```bash
# List Jobs (with filtering)
GET /jobs?status=processing&page=1&page_size=20&sort_by=created_at&sort_order=desc
Authorization: Bearer {token}

Response:
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "processing",
      "current_stage": "extraction",
      "progress_pct": 45,
      "error_message": null,
      "created_at": "2026-04-13T10:00:00+00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}

# Get Job Details
GET /jobs/{job_id}
Authorization: Bearer {token}

# Stream Job Progress (Server-Sent Events)
GET /jobs/{job_id}/progress
Authorization: Bearer {token}

# Example progress events:
event: ping
data: {"status": "processing"}

event: job_progress
data: {"stage": "extraction", "progress": 45}

event: job_completed
data: {"status": "completed"}
```

#### 📊 Results

```bash
# Get Job Result
GET /jobs/{job_id}/result
Authorization: Bearer {token}

Response:
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "job_id": "550e8400-e29b-41d4-a716-446655440001",
  "raw_output": {
    "title": "Document Title",
    "category": "Technical",
    "summary": "Summary of document content...",
    "keywords": ["keyword1", "keyword2"],
    "metadata": {...}
  },
  "reviewed_output": null,
  "is_finalized": false,
  "finalized_at": null
}

# Update Result
PUT /jobs/{job_id}/result
Authorization: Bearer {token}
Content-Type: application/json

{
  "reviewed_output": {
    "title": "Corrected Title",
    "category": "Technical"
  }
}

# Finalize Result (Mark as Reviewed)
POST /jobs/{job_id}/finalize
Authorization: Bearer {token}

# Retry Job
POST /jobs/{job_id}/retry
Authorization: Bearer {token}

# Cancel Job
POST /jobs/{job_id}/cancel
Authorization: Bearer {token}
```

#### 📤 Export

```bash
# Export Single Job Result
GET /jobs/{job_id}/export?format=json
GET /jobs/{job_id}/export?format=csv
Authorization: Bearer {token}

# Export Multiple Jobs
GET /export/bulk?job_ids=id1,id2,id3&format=json
Authorization: Bearer {token}
```

### Status Codes

| Code | Meaning               |
| ---- | --------------------- |
| 200  | Success               |
| 201  | Created               |
| 400  | Bad Request           |
| 401  | Unauthorized          |
| 403  | Forbidden             |
| 404  | Not Found             |
| 409  | Conflict              |
| 422  | Unprocessable Entity  |
| 500  | Internal Server Error |

---

## 🧪 Testing

### Run API Tests

```bash
# Comprehensive test suite (8 tests)
python test_apis.py

# Expected output:
# ✅ Health Check
# ✅ List Jobs
# ✅ Register User
# ✅ Login
# ✅ Invalid Login (expected failure)
# ✅ Invalid Upload (expected failure)
# ✅ Get Non-existent Job (expected failure)
# ✅ List with Filters
#
# Total: 8/8 tests passed
```

### Test Individual Endpoints

```bash
# Health check
curl http://127.0.0.1:8000/health

# Register
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Pass123!","full_name":"Test User"}'

# Login
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Pass123!"}'
```

### Database Testing

```bash
# Verify database connection
python backend/test_db_connection.py

# Initialize/verify database tables
python init_db.py
```

---

## 📁 Project Structure

```
async-doc-processor/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app factory
│   │   ├── controllers/        # Route handlers
│   │   │   ├── auth_controller.py
│   │   │   ├── document_controller.py
│   │   │   ├── job_controller.py
│   │   │   └── export_controller.py
│   │   ├── services/           # Business logic
│   │   │   ├── document_service.py
│   │   │   ├── job_service.py
│   │   │   ├── result_service.py
│   │   │   └── export_service.py
│   │   ├── models/             # SQLAlchemy models
│   │   │   ├── user_model.py
│   │   │   ├── document_model.py
│   │   │   ├── job_model.py
│   │   │   └── result_model.py
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── db/                 # Database setup
│   │   ├── core/               # Configuration
│   │   ├── middlewares/        # Error handling
│   │   └── workers/            # Background jobs
│   ├── requirements.txt        # Python dependencies
│   ├── test_db_connection.py
│   └── .env
│
├── frontend/                   # React application
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── api/                # API client
│   │   ├── components/         # React components
│   │   ├── pages/              # Page components
│   │   ├── hooks/              # Custom hooks
│   │   └── types/              # TypeScript types
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── init_db.py                  # Database initialization
├── test_apis.py                # API test suite
├── check_endpoints.py          # Endpoint verification
├── diagnostic_report.py        # Diagnostics
├── .env                        # Environment variables
├── README.md                   # This file
└── .gitignore
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Application
APP_ENV=development|staging|production

# JWT Settings
SECRET_KEY=your-secret-key (min 32 characters)
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=HS256

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=docprocessor
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Redis (for background tasks)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# File Upload (optional)
MAX_FILE_SIZE=52428800  # 50MB in bytes
ALLOWED_FILE_TYPES=pdf,doc,docx,txt,jpg,png
```

---

## 🔧 Troubleshooting

### Backend Won't Start

**Error**: `[WinError 10013] An attempt was made to access a socket`

**Solution**:

```bash
# Use localhost instead of 0.0.0.0
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Or use a different port
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### Database Connection Failed

**Error**: `socket.gaierror: [Errno 11003] getaddrinfo failed`

**Solution**:

```bash
# Verify PostgreSQL is running
psql -U postgres -d docprocessor

# Or test with the verification script
python backend/test_db_connection.py
```

### 404 Errors on API Endpoints

**Solution**:

- Verify backend is running at `http://127.0.0.1:8000`
- Check endpoint paths in test scripts
- Ensure authorization headers are correct for protected routes

### Tests Fail After Code Changes

```bash
# Restart backend to reload changes
# In backend terminal: Ctrl+C, then restart
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 📊 Database Schema

### Tables

**users**

- `id` (UUID, PK)
- `email` (String, unique)
- `hashed_password` (String)
- `full_name` (String, nullable)
- `created_at`, `updated_at` (Timestamp)

**documents**

- `id` (UUID, PK)
- `filename` (String)
- `file_type` (String)
- `file_size` (Integer)
- `storage_path` (String)
- `uploaded_by` (UUID, FK → users)
- `created_at`, `updated_at` (Timestamp)

**jobs**

- `id` (UUID, PK)
- `document_id` (UUID, FK → documents)
- `status` (Enum: pending, processing, completed, failed, cancelled)
- `current_stage` (String)
- `progress_pct` (Integer)
- `celery_task_id` (String, nullable)
- `error_message` (String, nullable)
- `retry_count` (Integer, default 0)
- `created_at`, `updated_at` (Timestamp)

**results**

- `id` (UUID, PK)
- `job_id` (UUID, FK → jobs, unique)
- `raw_output` (JSONB)
- `reviewed_output` (JSONB, nullable)
- `is_finalized` (Boolean)
- `finalized_at` (Timestamp, nullable)

---

## 🚀 Deployment

### Production Setup

1. **Update Configuration**

   ```bash
   APP_ENV=production
   SECRET_KEY=<generate-random-32-char-key>
   ```

2. **Run with Gunicorn** (Production WSGI server)

   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 app.main:app
   ```

3. **Setup Reverse Proxy** (Nginx/Apache)
   - Route requests to Gunicorn on port 8000
   - Enable SSL/TLS

4. **Database Backups**
   ```bash
   pg_dump -U postgres docprocessor > backup.sql
   psql -U postgres docprocessor < backup.sql  # Restore
   ```

---

## 📝 Development Workflow

### Add a New Feature

1. Create feature branch

   ```bash
   git checkout -b feature/new-feature
   ```

2. Make changes to backend/frontend

3. Test changes

   ```bash
   python test_apis.py
   ```

4. Commit and push

   ```bash
   git add .
   git commit -m "Add new feature"
   git push origin feature/new-feature
   ```

5. Create Pull Request

---

## 🐛 Known Issues

| Issue                     | Workaround                                    |
| ------------------------- | --------------------------------------------- |
| Redis connection errors   | Optional - not required for basic API testing |
| Celery background tasks   | Can disable in development via settings       |
| CORS issues in production | Update CORS_ORIGINS env var                   |

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📞 Support

For issues, questions, or contributions:

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: support@example.com

---

## 🎉 Acknowledgments

- FastAPI for the excellent async web framework
- SQLAlchemy for comprehensive ORM
- React for the modern frontend
- PostgreSQL for reliable data storage

---

## 📈 Roadmap

- [ ] Add webhook support for job completion notifications
- [ ] Implement job scheduling (cron-based)
- [ ] Add advanced search and filtering
- [ ] Multi-language document support
- [ ] Docker containerization
- [ ] Kubernetes deployment templates
- [ ] Admin dashboard
- [ ] API rate limiting
- [ ] Advanced analytics

---

**Last Updated**: April 13, 2026

**Status**: ✅ Production Ready | All tests passing (8/8) | Database verified

---

## 💡 Quick Reference

```bash
# Start backend
cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Start frontend
cd frontend && npm run dev

# Run tests
python test_apis.py

# Check endpoints
python check_endpoints.py

# Verify database
python backend/test_db_connection.py

# Access API docs
# http://127.0.0.1:8000/docs
```

Happy coding! 🚀
