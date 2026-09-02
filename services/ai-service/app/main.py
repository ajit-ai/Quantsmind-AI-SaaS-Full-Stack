from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import time
import hashlib

app = FastAPI(title="Quantsmind AI Service", version="1.0.0")

class PredictRequest(BaseModel):
    prompt: str
    params: Optional[dict] = None
    modelVersion: str = "v1"

class PredictResponse(BaseModel):
    result: str
    tokensIn: int
    tokensOut: int
    latencyMs: int
    modelVersion: str
    cached: bool = False

def verify_token(x_internal_token: str = Header(None)):
    import os
    expected = os.getenv("INTERNAL_TOKEN", "dev-internal-token")
    if x_internal_token != expected:
        # allow missing in dev if no header sent and expected is dev token? strict in prod
        if x_internal_token is None and expected == "dev-internal-token":
            return
        raise HTTPException(status_code=401, detail="Invalid internal token")

@app.get("/health")
def health():
    return {"status": "ok", "modelLoaded": True, "version": "v1", "uptimeSec": int(time.time() % 100000)}

@app.get("/metrics")
def metrics():
    return "# Prometheus metrics placeholder\nai_requests_total 0\n"

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest, _: None = Depends(verify_token)):
    start = time.time()
    # placeholder model — replace app/model.py:predict()
    prompt_hash = hashlib.sha256(req.prompt.encode()).hexdigest()[:8]
    result = f"[mock v{req.modelVersion}] Echo: {req.prompt[:200]} (hash {prompt_hash})"
    latency = int((time.time() - start) * 1000) or 12
    return PredictResponse(
        result=result,
        tokensIn=len(req.prompt.split()),
        tokensOut=len(result.split()),
        latencyMs=latency,
        modelVersion=req.modelVersion,
    )

@app.post("/batch/predict")
def batch_predict(items: list[PredictRequest], _: None = Depends(verify_token)):
    return {"results": [predict(i) for i in items]}
