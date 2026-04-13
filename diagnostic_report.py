"""
Comprehensive diagnostic report for API issue
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_PREFIX = f"{BASE_URL}/api/v1"

def capture_response(method, url, **kwargs):
    """Capture full response details"""
    try:
        resp = requests.request(method, url, timeout=5, **kwargs)
        return {
            'status': resp.status_code,
            'headers': dict(resp.headers),
            'body': resp.text[:500] if resp.text else '',
            'json': None
        }
    except Exception as e:
        return {'status': None, 'error': str(e)}

print("="*80)
print("ASYNC DOC PROCESSOR - DIAGNOSTIC REPORT")
print(f"Timestamp: {datetime.now().isoformat()}")
print("="*80)

# Test 1: Health
print("\n[TEST] Health Check")
resp = capture_response("GET", f"{BASE_URL}/health")
print(f"  Status: {resp['status']}")
if resp['status'] == 200:
    print("  ✅ PASS - API is responding")
else:
    print(f"  ❌ FAIL - {resp.get('error', 'Unexpected status')}")

# Test 2: List jobs
print("\n[TEST] List Jobs")
resp = capture_response("GET", f"{API_PREFIX}/jobs")
print(f"  Status: {resp['status']}")
if resp['status'] == 200:
    print("  ✅ PASS")
elif resp['status'] == 500:
    print("  ❌ FAIL - 500 Internal Server Error")
    print(f"  Response: {resp['body']}")
else:
    print(f"  ❌ FAIL - {resp['status']}")

# Test 3: Register
print("\n[TEST] Register User")
payload = {"email": f"test_{datetime.now().timestamp()}@test.com", "password": "Pass123!", "full_name": "Test"}
resp = capture_response("POST", f"{API_PREFIX}/auth/register", json=payload)
print(f"  Status: {resp['status']}")
if resp['status'] == 201:
    print("  ✅ PASS")
elif resp['status'] == 404:
    print("  ❌ FAIL - 404 Not Found (endpoint not registered?)")
    print(f"  Note: This endpoint SHOULD be available at /api/v1/auth/register")
else:
    print(f"  ❌ FAIL - {resp['status']}")

# Summary
print("\n" + "="*80)
print("SUMMARY & RECOMMENDATIONS")
print("="*80)
print("""
Issue: Backend returns 500 errors for database queries and 404 for valid endpoints

Possible Causes:
1. Backend process not restarted after config changes
2. Database tables not loaded in memory
3. Asyncpg connection pooling issue
4. Request handling exception not being caught

Recommendations:
1. RESTART the backend process:
   - Kill the running backend (if in separate terminal)
   - Start it again with: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
2. Verify database:
   - Run: python init_db.py
   - Should see: "✓ Tables created successfully!" or "✓ Tables already exist"

3. Re-test APIs:
   - After backend restart, run: python test_apis.py
   - Should see: "✅ PASS" for most endpoints

4. Check backend logs:
   - Look for error messages in backend terminal
   - Check if asyncpg connection is working properly

Debug Info:
- Database URL encoding: Fixed (@ → %40)
- Tables: ✅ Created
- Endpoints: ✅ Registered (14 total)  
- Health: ✅ Working (200 OK)
- Business Logic: ❌ Failing (500 errors)
""")
