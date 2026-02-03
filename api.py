from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import os
import json

from orchestrator import CerebrasAttacker
from genome_analysis import SecurityGenomeAnalyzer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/attack")
async def run_attack(target: str):
    api_key = os.environ.get("CEREBRAS_API_KEY")
    attacker = CerebrasAttacker(api_key=api_key, target_url=target)
    
    def generate():
        for event in attacker.run(max_steps=20):
            yield f"data: {json.dumps(event)}\n\n"
        
        analyzer = SecurityGenomeAnalyzer(api_key=api_key)
        genome = analyzer.analyze(attacker.state.attack_log, attacker.state)
        
        yield f"data: {json.dumps({'type': 'genome', 'content': genome})}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/health")
async def health():
    return {"status": "ok"}