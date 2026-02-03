"""Quick API test"""
import os
import requests

# Load from .env file
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val.strip('"').strip("'")

api_key = os.environ.get("CEREBRAS_API_KEY")
if not api_key:
    print("ERROR: CEREBRAS_API_KEY not set")
    exit(1)

print(f"Testing GLM 4.7 with key: {api_key[:8]}...")

r = requests.post(
    "https://api.cerebras.ai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    json={
        "model": "zai-glm-4.7",
        "messages": [{"role": "user", "content": "Analyze this code for SQL injection: user_input = request.args.get('id'); cursor.execute(f'SELECT * FROM users WHERE id = {user_input}')"}],
        "max_tokens": 200
    }
)

print(f"Status: {r.status_code}")
print(f"Response: {r.text[:800]}")