import requests
import json

r = requests.get('http://127.0.0.1:8000/status')
audit_id = r.json().get('audit_id')
print("Active audit:", audit_id)

r2 = requests.get(f'http://127.0.0.1:8000/remediate/{audit_id}', headers={"X-User-Id": "anonymous"})
if r2.status_code != 200:
    print(r2.status_code, r2.text)
else:
    print("Success. Headers:", r2.headers.get("X-Remediation-Summary"))
