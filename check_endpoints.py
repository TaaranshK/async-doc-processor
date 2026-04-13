"""Get all registered endpoints from OpenAPI schema"""
import requests
import json

resp = requests.get('http://localhost:8000/openapi.json', timeout=5)
data = resp.json()

print("\n" + "="*80)
print("REGISTERED ENDPOINTS")
print("="*80)

for path in sorted(data.get('paths', {}).keys()):
    methods = list(data['paths'][path].keys())
    methods = [m.upper() for m in methods if m not in ['parameters']]
    print(f"{path:<50} {', '.join(methods)}")

print("\n" + "="*80)
print("TOTALS")
print("="*80)
print(f"Total paths: {len(data.get('paths', {}))}")
