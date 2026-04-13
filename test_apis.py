"""
Comprehensive API testing script for async-doc-processor
"""
import requests
import json
from typing import Any

BASE_URL = "http://127.0.0.1:8000"
API_PREFIX = f"{BASE_URL}/api/v1"

def test_health():
    """Test the health endpoint"""
    print("\n" + "="*80)
    print("TEST 1: HEALTH CHECK")
    print("="*80)
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_list_jobs():
    """Test list jobs endpoint"""
    print("\n" + "="*80)
    print("TEST 2: LIST JOBS (no jobs yet)")
    print("="*80)
    try:
        response = requests.get(f"{API_PREFIX}/jobs", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_register_user():
    """Test user registration"""
    print("\n" + "="*80)
    print("TEST 3: REGISTER USER")
    print("="*80)
    payload = {
        "email": f"testuser_{id(object())}@example.com",
        "password": "SecurePass123!@",
        "full_name": "Test User"
    }
    print(f"Payload: {json.dumps(payload, indent=2)}")
    try:
        response = requests.post(f"{API_PREFIX}/auth/register", json=payload, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 201
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_login():
    """Test user login"""
    print("\n" + "="*80)
    print("TEST 4: LOGIN")
    print("="*80)
    # First register a user
    register_payload = {
        "email": f"testlogin_{id(object())}@example.com",
        "password": "LoginPass123!@",
        "full_name": "Login Test User"
    }
    requests.post(f"{API_PREFIX}/auth/register", json=register_payload, timeout=5)
    
    # Then login
    login_payload = {
        "email": register_payload["email"],
        "password": register_payload["password"]
    }
    print(f"Payload: {json.dumps(login_payload, indent=2)}")
    try:
        response = requests.post(f"{API_PREFIX}/auth/login", json=login_payload, timeout=5)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response (truncated tokens):")
        print(f"  - access_token: {data.get('access_token', '')[:50]}...")
        print(f"  - refresh_token: {data.get('refresh_token', '')[:50]}...")
        print(f"  - token_type: {data.get('token_type')}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_invalid_login():
    """Test invalid login"""
    print("\n" + "="*80)
    print("TEST 5: INVALID LOGIN (should fail)")
    print("="*80)
    payload = {
        "email": "nonexistent@example.com",
        "password": "WrongPassword123!"
    }
    print(f"Payload: {json.dumps(payload, indent=2)}")
    try:
        response = requests.post(f"{API_PREFIX}/auth/auth/login", json=payload, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code in [401, 403, 404]
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_invalid_document_upload():
    """Test document upload with no files"""
    print("\n" + "="*80)
    print("TEST 6: DOCUMENT UPLOAD (no files - should fail)")
    print("="*80)
    try:
        response = requests.post(f"{API_PREFIX}/documents/upload", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code in [400, 422]
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_nonexistent_job():
    """Test getting a non-existent job"""
    print("\n" + "="*80)
    print("TEST 7: GET NON-EXISTENT JOB (should fail)")
    print("="*80)
    fake_job_id = "00000000-0000-0000-0000-000000000000"
    try:
        response = requests.get(f"{API_PREFIX}/jobs/{fake_job_id}", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code in [404, 400]
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_list_jobs_with_filters():
    """Test list jobs with filters"""
    print("\n" + "="*80)
    print("TEST 8: LIST JOBS WITH FILTERS")
    print("="*80)
    params = {
        "status": "completed",
        "page": 1,
        "page_size": 10,
        "sort_by": "created_at",
        "sort_order": "desc"
    }
    print(f"Query Params: {json.dumps(params, indent=2)}")
    try:
        response = requests.get(f"{API_PREFIX}/jobs", params=params, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n╔" + "="*78 + "╗")
    print("║" + " "*20 + "ASYNC DOCUMENT PROCESSOR - API TESTS" + " "*25 + "║")
    print("╚" + "="*78 + "╝")
    
    results = {
        "Health Check": test_health(),
        "List Jobs": test_list_jobs(),
        "Register User": test_register_user(),
        "Login": test_login(),
        "Invalid Login": test_invalid_login(),
        "Invalid Document Upload": test_invalid_document_upload(),
        "Get Non-existent Job": test_get_nonexistent_job(),
        "List Jobs with Filters": test_list_jobs_with_filters(),
    }
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<45} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

if __name__ == "__main__":
    main()
