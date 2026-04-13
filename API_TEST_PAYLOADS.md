## Async Document Processor — API Test Guide

**Base URL**: `http://localhost:8000`

---

## 1. HEALTH CHECK

```bash
curl -X GET http://localhost:8000/health
```

**Response** (200):

```json
{ "status": "ok" }
```

---

## 2. AUTH ENDPOINTS

### 2.1 Register User

```bash
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Doe"
  }'
```

**Response** (201):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2026-04-13T12:00:00Z"
}
```

---

### 2.2 Login

```bash
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

**Response** (200):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### 2.3 Refresh Token

```bash
curl -X POST http://localhost:8000/api/v1/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Response** (200):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 3. DOCUMENT ENDPOINTS

### 3.1 Upload Documents (Multipart)

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "files=@/path/to/file1.pdf" \
  -F "files=@/path/to/file2.txt"
```

**Response** (200):

```json
{
  "items": [
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440001",
      "job_id": "660e8400-e29b-41d4-a716-446655440002",
      "filename": "file1.pdf",
      "file_size": 102400
    },
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440003",
      "job_id": "660e8400-e29b-41d4-a716-446655440004",
      "filename": "file2.txt",
      "file_size": 5120
    }
  ]
}
```

---

## 4. JOB ENDPOINTS

### 4.1 List Jobs (with filters)

```bash
# All jobs
curl http://localhost:8000/api/v1/jobs

# Filter by status
curl "http://localhost:8000/api/v1/jobs?status=processing&page=1&page_size=20&sort_by=created_at&sort_order=desc"

# Search by filename
curl "http://localhost:8000/api/v1/jobs?search=invoice&status=completed"
```

**Response** (200):

```json
{
  "items": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440002",
      "document_id": "550e8400-e29b-41d4-a716-446655440001",
      "filename": "file1.pdf",
      "file_type": "application/pdf",
      "file_size": 102400,
      "status": "processing",
      "progress_pct": 45,
      "current_stage": "extract_text",
      "retry_count": 0,
      "error_message": null,
      "created_at": "2026-04-13T12:05:00Z",
      "updated_at": "2026-04-13T12:05:15Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

### 4.2 Get Job Details

```bash
curl http://localhost:8000/api/v1/jobs/660e8400-e29b-41d4-a716-446655440002
```

**Response** (200):

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440002",
  "document_id": "550e8400-e29b-41d4-a716-446655440001",
  "filename": "file1.pdf",
  "file_type": "application/pdf",
  "file_size": 102400,
  "status": "completed",
  "celery_task_id": "task-abc123xyz",
  "current_stage": "completed",
  "progress_pct": 100,
  "error_message": null,
  "retry_count": 0,
  "created_at": "2026-04-13T12:05:00Z",
  "updated_at": "2026-04-13T12:06:30Z"
}
```

---

### 4.3 Stream Job Progress (Server-Sent Events)

```bash
curl http://localhost:8000/api/v1/jobs/660e8400-e29b-41d4-a716-446655440002/progress
```

**Response** (Streaming 200):

```
data: {"status": "processing", "progress_pct": 25, "current_stage": "extract_text"}
data: {"status": "processing", "progress_pct": 50, "current_stage": "analyse"}
data: {"status": "completed", "progress_pct": 100, "current_stage": "completed"}
```

---

### 4.4 Get Job Result

```bash
curl http://localhost:8000/api/v1/jobs/660e8400-e29b-41d4-a716-446655440002/result
```

**Response** (200):

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440003",
  "job_id": "660e8400-e29b-41d4-a716-446655440002",
  "raw_output": {
    "title": "Invoice 2026",
    "category": "financial",
    "summary": "Q1 2026 invoice for services",
    "keywords": ["invoice", "payment", "2026"],
    "file_metadata": {
      "name": "file1.pdf",
      "type": "application/pdf",
      "size": 102400
    },
    "status": "completed",
    "extraction_confidence": 0.95
  },
  "reviewed_output": null,
  "is_finalized": false,
  "finalized_at": null
}
```

---

### 4.5 Update Job Result

```bash
curl -X PUT http://localhost:8000/api/v1/jobs/660e8400-e29b-41d4-a716-446655440002/result \
  -H "Content-Type: application/json" \
  -d '{
    "reviewed_output": {
      "title": "Q1 2026 Invoice - Corrected",
      "category": "financial",
      "summary": "Q1 2026 invoice for consulting services rendered",
      "keywords": ["invoice", "payment", "2026", "consulting"],
      "file_metadata": {
        "name": "file1.pdf",
        "type": "application/pdf",
        "size": 102400
      },
      "status": "reviewed",
      "extraction_confidence": 0.95
    }
  }'
```

**Response** (200):

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440003",
  "job_id": "660e8400-e29b-41d4-a716-446655440002",
  "raw_output": {...},
  "reviewed_output": {...},
  "is_finalized": false,
  "finalized_at": null
}
```

---

### 4.6 Finalize Job Result

```bash
curl -X POST http://localhost:8000/api/v1/jobs/660e8400-e29b-41d4-a716-446655440002/finalize
```

**Response** (200):

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440003",
  "job_id": "660e8400-e29b-41d4-a716-446655440002",
  "raw_output": {...},
  "reviewed_output": {...},
  "is_finalized": true,
  "finalized_at": "2026-04-13T12:10:00Z"
}
```

---

### 4.7 Retry Job

```bash
curl -X POST http://localhost:8000/api/v1/jobs/660e8400-e29b-41d4-a716-446655440002/retry
```

**Response** (200):

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440002",
  "document_id": "550e8400-e29b-41d4-a716-446655440001",
  "filename": "file1.pdf",
  "file_type": "application/pdf",
  "file_size": 102400,
  "status": "queued",
  "celery_task_id": null,
  "current_stage": null,
  "progress_pct": 0,
  "error_message": null,
  "retry_count": 1,
  "created_at": "2026-04-13T12:05:00Z",
  "updated_at": "2026-04-13T12:11:00Z"
}
```

---

### 4.8 Cancel Job

```bash
curl -X POST http://localhost:8000/api/v1/jobs/660e8400-e29b-41d4-a716-446655440002/cancel
```

**Response** (200):

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440002",
  "document_id": "550e8400-e29b-41d4-a716-446655440001",
  "filename": "file1.pdf",
  "file_type": "application/pdf",
  "file_size": 102400,
  "status": "cancelled",
  "celery_task_id": "task-abc123xyz",
  "current_stage": "extract_text",
  "progress_pct": 45,
  "error_message": "User cancelled the job",
  "retry_count": 0,
  "created_at": "2026-04-13T12:05:00Z",
  "updated_at": "2026-04-13T12:12:00Z"
}
```

---

## 5. EXPORT ENDPOINTS

### 5.1 Export Single Job (JSON or CSV)

```bash
# Export as JSON
curl http://localhost:8000/api/v1/jobs/660e8400-e29b-41d4-a716-446655440002/export?format=json \
  -o result.json

# Export as CSV
curl http://localhost:8000/api/v1/jobs/660e8400-e29b-41d4-a716-446655440002/export?format=csv \
  -o result.csv
```

**Response** (200):

- **JSON**: Structured extraction data
- **CSV**: Flattened key-value pairs

---

### 5.2 Export Bulk Jobs

```bash
curl "http://localhost:8000/api/v1/export/bulk?ids=660e8400-e29b-41d4-a716-446655440002&ids=660e8400-e29b-41d4-a716-446655440004&format=csv" \
  -o bulk_export.csv
```

**Response** (200): Multi-job CSV or JSON export

---

## API DOCUMENTATION

**Interactive API Docs**: Open `http://localhost:8000/docs` (Swagger UI)

**OpenAPI Schema**: `http://localhost:8000/openapi.json`

---

## ERROR HANDLING

### 400 Bad Request

```json
{
  "detail": "Invalid query parameters"
}
```

### 401 Unauthorized

```json
{
  "detail": "Invalid credentials"
}
```

### 404 Not Found

```json
{
  "detail": "Job not found"
}
```

### 422 Unprocessable Entity

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

---

## QUICK TEST (No Authentication)

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. List jobs (empty initially)
curl http://localhost:8000/api/v1/jobs

# 3. Upload a test document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "files=@test.pdf"

# 4. Get the job ID from response and check progress
curl http://localhost:8000/api/v1/jobs/{job_id}

# 5. Stream progress
curl http://localhost:8000/api/v1/jobs/{job_id}/progress

# 6. Get result when completed
curl http://localhost:8000/api/v1/jobs/{job_id}/result
```

---
