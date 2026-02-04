#!/usr/bin/env python3
"""
Quick test: Verify both APIs work before running the full breach race.
Run this first!
"""
import os
import time
import requests

# Load .env
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val.strip('"').strip("'")

def test_cerebras():
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        print("❌ CEREBRAS_API_KEY not found in environment or .env")
        return False
    
    print(f"Testing Cerebras (key: {api_key[:8]}...)")
    
    # Try different models in order of preference
    models = ["llama3.1-8b"]
    
    for model in models:
        try:
            start = time.time()
            r = requests.post(
                "https://api.cerebras.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say 'API working' in exactly 2 words."}],
                    "max_tokens": 20,
                    "temperature": 0
                },
                timeout=30
            )
            elapsed = time.time() - start
            
            if r.status_code == 200:
                data = r.json()
                if "choices" in data and len(data["choices"]) > 0 and "message" in data["choices"][0]:
                    text = data["choices"][0]["message"].get("content", "")
                    print(f"[OK] Cerebras OK - Model: {model}")
                    print(f"   Response: {text[:50]}")
                    print(f"   Time: {elapsed:.2f}s")
                    return model  # Return working model name
                else:
                    print(f"   Model {model} unexpected response format: {data}")
            else:
                print(f"   Model {model}: HTTP {r.status_code} - {r.text[:100]}")
        except Exception as e:
            print(f"   Model {model} error: {e}")
    
    print("[FAIL] No Cerebras model worked")
    return False


def test_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[FAIL] GEMINI_API_KEY not found in environment or .env")
        print("   Add to .env: GEMINI_API_KEY=your-key-here")
        print("   Get key at: https://aistudio.google.com/apikey")
        return False
    
    print(f"\nTesting Gemini (key: {api_key[:10]}...)")
    
    models = ["gemini-2.5-flash"]
    
    for model in models:
        try:
            start = time.time()
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": "Say 'API working' in exactly 2 words."}]}],
                    "generationConfig": {"temperature": 0, "maxOutputTokens": 20}
                },
                timeout=30
            )
            elapsed = time.time() - start
            
            if r.status_code == 200:
                data = r.json()
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                except:
                    text = str(data)[:100]
                print(f"[OK] Gemini OK - Model: {model}")
                print(f"   Response: {text[:50]}")
                print(f"   Time: {elapsed:.2f}s")
                return model
            else:
                print(f"   Model {model}: HTTP {r.status_code} - {r.text[:100]}")
        except Exception as e:
            print(f"   Model {model} error: {e}")
    
    print("[FAIL] No Gemini model worked")
    return False


if __name__ == "__main__":
    print("=" * 60)
    print("BREACH RACE - API TEST")
    print("=" * 60)
    print()
    
    cerebras_model = test_cerebras()
    gemini_model = test_gemini()
    
    print()
    print("=" * 60)
    
    if cerebras_model and gemini_model:
        print("[OK] ALL SYSTEMS GO")
        print()
        print(f"   Cerebras model: {cerebras_model}")
        print(f"   Gemini model: {gemini_model}")
        print()
        print("   Run the breach race:")
        print("   python breach_race.py")
    else:
        print("[FAIL] FIX ISSUES ABOVE BEFORE RUNNING BREACH RACE")
        if not cerebras_model:
            print("   - Check CEREBRAS_API_KEY in .env")
        if not gemini_model:
            print("   - Add GEMINI_API_KEY to .env")
            print("   - Get key: https://aistudio.google.com/apikey")
    
    print("=" * 60)