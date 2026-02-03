import requests
import json
import sys

def test_sse():
    url = "http://localhost:8000/attack?target=http://localhost:5000"
    print(f"Connecting to {url}...")
    
    try:
        with requests.get(url, stream=True) as response:
            print(f"Status Code: {response.status_code}")
            if response.status_code != 200:
                print(f"Error content: {response.text}")
                return

            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    print(f"Received: {decoded_line}")
                    if decoded_line.startswith("data:"):
                        try:
                            data = json.loads(decoded_line[6:])
                            if data.get("type") == "done":
                                print("Stream complete.")
                                break
                        except:
                            pass
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_sse()
