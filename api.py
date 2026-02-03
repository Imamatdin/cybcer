from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import os
import json

from orchestrator import CerebrasAttacker
from genome_analysis import SecurityGenomeAnalyzer

# Load .env file
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val.strip('"').strip("'")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/attack")
async def run_attack(target: str):
    api_key = os.environ.get("CEREBRAS_API_KEY")
    attacker = CerebrasAttacker(api_key=api_key, target_url=target)
    
    if not api_key:
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'message': 'CEREBRAS_API_KEY not found'})}\n\n"]), 
            media_type="text/event-stream"
        )

    def generate():
        try:
            yield f"data: {json.dumps({'type': 'think', 'content': 'Initializing attack sequence...', 'time': 0})}\n\n"
            for event in attacker.run(max_steps=20):
                yield f"data: {json.dumps(event)}\n\n"
            
            analyzer = SecurityGenomeAnalyzer(api_key=api_key)
            genome = analyzer.analyze(attacker.state.attack_log, attacker.state)
            
            yield f"data: {json.dumps({'type': 'genome', 'content': genome})}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Server Error: {str(e)}'})}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/health")
async def health():
    return {"status": "ok"}
