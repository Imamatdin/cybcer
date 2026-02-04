import os
import time
import requests
import sys

# Load .env
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val.strip('"').strip("'")

api_key = os.environ.get("CEREBRAS_API_KEY")
if not api_key:
    print("Error: CEREBRAS_API_KEY not found")
    sys.exit(1)

def test_speed(model, prompt, max_tokens, label):
    print(f"\n--- Testing {label} ({max_tokens} max tokens) ---")
    print("Sending request...")
    
    start = time.time()
    try:
        r = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.5
            },
            timeout=60
        )
        total_time = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            
            # Estimate tokens if usage not provided
            if completion_tokens == 0:
                completion_tokens = len(content) / 4
            
            tps = completion_tokens / total_time
            
            print(f"Total Time: {total_time:.4f}s")
            print(f"Tokens Gen: {completion_tokens}")
            print(f"Speed:      {tps:.2f} tokens/sec (Effective)")
            print(f"Note: This includes network latency.")
            return total_time, completion_tokens
        else:
            print(f"Error: {r.status_code} - {r.text}")
            return 0, 0
            
    except Exception as e:
        print(f"Exception: {e}")
        return 0, 0

model = "llama3.1-8b"
print(f"Target Model: {model}")

# Test 1: Short (Latency Bound)
test_speed(
    model, 
    "Say 'Hello world' in JSON.", 
    50, 
    "SHORT / LATENCY TEST"
)

# Test 2: Long (Throughput Bound)
test_speed(
    model, 
    "Write a very long, detailed essay about the history of the internet, starting from ARPANET to modern fiber optics. Write at least 1000 words. Go fast.", 
    1500, 
    "LONG / THROUGHPUT TEST"
)
