"""List available Cerebras models"""
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
r = requests.get(
    "https://api.cerebras.ai/v1/models",
    headers={"Authorization": f"Bearer {api_key}"}
)
print(r.json())
