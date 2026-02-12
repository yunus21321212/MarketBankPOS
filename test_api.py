import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://127.0.0.1:5000"

def test_endpoint(url):
    print(f"Testing {url}...")
    try:
        res = requests.get(url, verify=False, timeout=5)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            print("Response:", json.dumps(res.json(), indent=2)[:200] + "...")
        else:
            print("Error:", res.text)
    except Exception as e:
        print(f"Failed: {e}")
    print("-" * 20)

test_endpoint(f"{BASE_URL}/api/stores")
test_endpoint(f"{BASE_URL}/api/hr/employees")
test_endpoint(f"{BASE_URL}/api/audit/logs")
test_endpoint(f"{BASE_URL}/api/product/11")
