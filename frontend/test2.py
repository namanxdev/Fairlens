import requests

r = requests.get('http://127.0.0.1:8000/audits', headers={"X-User-Id": "anonymous"})
print(r.status_code, r.text)

if r.status_code == 200 and len(r.json()) > 0:
    for audit in r.json():
        aid = audit["audit_id"]
        res = requests.get(f'http://127.0.0.1:8000/remediate/{aid}', headers={"X-User-Id": "anonymous"})
        print(res.status_code, res.text[:200])

