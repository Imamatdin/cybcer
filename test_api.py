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

print(f"Testing with key: {api_key[:8]}...")

r = requests.post(
    "https://api.cerebras.ai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    json={
        "model": "llama3.1-8b",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 50
    }
)

print(f"Status: {r.status_code}")
print(f"Response: {r.text[:500]}")
