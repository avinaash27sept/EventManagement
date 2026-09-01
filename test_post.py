import requests
import json

url = "http://127.0.0.1:8000/webhook"
payload = {
    "type": "registration",
    "name": "Automation Test",
    "email": "tester+webhook@example.com",
    "workshop_id": 1
}
try:
    r = requests.post(url, json=payload, timeout=10)
    print('STATUS', r.status_code)
    print('TEXT', r.text)
except Exception as e:
    print('ERROR', str(e))
