import requests
import json
url = "https://cesrv.hknu.ac.kr/srv/gpt"
payload = {
"service": "gpt",
"question": "What is the capital of South Korea?",
"hash": ""
}

headers = {
"Content-Type": "application/json"
}
response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False)
result = response.json()
answer = result.get('answer')
