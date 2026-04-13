"""
Detailed API testing with error logging
"""
import requests
import json
from typing import Any

BASE_URL = "http://localhost:8000"
API_PREFIX = f"{BASE_URL}/api/v1"

def test_with_details(test_name: str, method: str, url: str, **kwargs):
    """Helper to test with detailed error logging"""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")
    print(f"Method: {method.upper()}")
    print(f"URL: {url}")
    if 'json' in kwargs:
        print(f"Payload: {json.dumps(kwargs['json'], indent=2)}")
    
    try:
        response = requests.request(method, url, timeout=5, **kwargs)
        print(f"Status: {response.status_code}")
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response (raw): {response.text[:500]}")
        return response.status_code, response
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None

def main():
    """Run detailed API tests"""
    print("\n╔" + "="*78 + "╗")
    print("║" + " "*20 + "API TESTING WITH DETAILED LOGGING" + " "*25 + "║")
    print("╚" + "="*78 + "╝")
    
    # Test 1: Health
    status, _ = test_with_details(
        "Health Check",
        "GET",
        f"{BASE_URL}/health"
    )
    
    # Test 2: List jobs with correct path
    status, _ = test_with_details(
        "List Jobs (/api/v1/jobs)",
        "GET",
        f"{API_PREFIX}/jobs"
    )
    
    # Test 3: Try to understand the 500 error
    status, resp = test_with_details(
        "List Jobs (with error details)",
        "GET",
        f"{API_PREFIX}/jobs"
    )
    
    if status == 500:
        print("\n⚠️ Getting 500 error - checking response headers and body:")
        print(f"Headers: {dict(resp.headers)}")
        print(f"Content-Type: {resp.headers.get('content-type')}")
    
    # Test 4: Auth endpoints with correct path
    register_payload = {
        "email": f"testuser_{id(object())}@example.com",
        "password": "SecurePass123!@",
        "full_name": "Test User"
    }
    status, _ = test_with_details(
        "Register User (/api/v1/auth/register)",
        "POST",
        f"{API_PREFIX}/auth/register",
        json=register_payload
    )
    
    # Test 5: Login with correct path
    login_payload = {
        "email": register_payload["email"],
        "password": register_payload["password"]
    }
    status, _ = test_with_details(
        "Login (/api/v1/auth/login)",
        "POST",
        f"{API_PREFIX}/auth/login",
        json=login_payload
    )
    
    # Test 6: Check Swagger docs to see all available endpoints
    print(f"\n{'='*80}")
    print("ℹ️  To see all available endpoints, visit:")
    print(f"   {BASE_URL}/docs")
    print(f"   {BASE_URL}/redoc")

if __name__ == "__main__":
    main()
