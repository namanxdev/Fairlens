import requests
import json
import io

URL = 'http://127.0.0.1:8000'

# 1. upload a dummy csv
csv_data = "gender,hired,feature\n" + "Male,1,0.5\nFemale,0,0.1\nMale,1,0.6\nFemale,1,0.9\n" * 15
files = {'file': ('test.csv'.encode('utf-8'), csv_data, 'text/csv')}
data = {'target_col': 'hired', 'sensitive_col': 'gender', 'domain': 'custom'}

print("Uploading...")
res1 = requests.post(f"{URL}/upload", files=files, data=data, headers={"X-User-Id": "test-user"})
print("Upload status:", res1.status_code)
if res1.status_code != 200:
    print(res1.text)
    exit(1)

audit_id = res1.json().get('audit_id')
print("Audit ID:", audit_id)

# 2. Try the remediate endpoint
print("Hitting remediate...")
res2 = requests.get(f"{URL}/remediate/{audit_id}", headers={"X-User-Id": "test-user"})
print("Remediate status:", res2.status_code, dict(res2.headers))
if res2.status_code != 200:
    print("Error text:", res2.text)
else:
    summary = res2.headers.get("x-remediation-summary")
    print("Summary header:", summary)
    print("Content preview:", res2.text[:150])

