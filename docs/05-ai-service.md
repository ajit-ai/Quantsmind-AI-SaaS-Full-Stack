# AI Inference Service — Standalone FastAPI Microservice

## 1. Purpose
Isolate ML dependencies, enable independent GPU scaling and release cycle. Stable internal contract with backend.

## 2. Stack
Python 3.11, FastAPI 0.110, Uvicorn, Pydantic v2, Redis (cache), Prometheus client, pytest + httpx, Docker (python:3.11-slim).

## 3. API Contract (internal)
```
POST /predict
  body: { prompt: str (1..8000), params: {temperature?: float, maxTokens?: int}, modelVersion: str = "v1" }
  → 200 { result: str|json, tokensIn: int, tokensOut: int, latencyMs: int, modelVersion: str }
  → 422 validation, 503 model not loaded

GET /health
  → { status: "ok"|"degraded", modelLoaded: bool, version: str, uptimeSec: int }

GET /metrics
  → Prometheus exposition (request_count, latency histogram, cache_hit_rate)

POST /batch/predict
  body: { items: [{prompt, params}] }
  → { results: [...] }
```

## 4. Implementation Layout
```
services/ai-service/
├── app/
│   ├── main.py          # FastAPI app, lifespan (load model)
│   ├── config.py        # pydantic settings (MODEL_PATH, REDIS_URL, INTERNAL_TOKEN)
│   ├── schemas.py       # Pydantic models
│   ├── model.py         # load_model(), predict() — swap impl here
│   ├── cache.py         # Redis sha256(prompt+params+version) → result TTL 1h
│   ├── metrics.py       # Prometheus counters/histograms
│   └── deps.py          # verify_internal_token
├── tests/
├── Dockerfile
├── requirements.txt
└── .env.example
```

## 5. Baseline & Targets
- Before touching model: benchmark existing model (if any) on fixed eval set → record latency p50/p95/p99 + accuracy (exact match / human eval).
- v1 targets: p95 < 800ms (cold), < 250ms (cache hit), accuracy ≥ baseline. Log every inference (promptHash, latency, tokens) — no raw PII unless consented, for retraining.
- Optimizations: batch, cache, quantization (e.g., 8-bit), distilled smaller model if latency bound not accuracy.

## 6. Caching & Batching
- Cache key: `sha256(normalizedPrompt + jsonStable(params) + modelVersion)` → Redis `ai:cache:<hash>` TTL 3600.
- Batch endpoint aggregates up to 16 items, parallel `asyncio.gather` with semaphore.

## 7. Scaling
- Stateless, `model` loaded once at startup (lifespan). Horizontal via replicas behind internal LB.
- GPU: set `MODEL_DEVICE=cuda` + `torch`/`onnxruntime-gpu`; non-GPU fallback is CPU.

## 8. Security
- Not publicly exposed; only `api` can reach it via Docker network / internal VPC.
- `X-Internal-Token` shared secret, rotated via env.
- Input sanitization + max length; no code exec from prompt.

## 9. Observability
- `/metrics` scraped by Prometheus/Grafana.
- Structured JSON logs with `requestId` propagated from `api` (`X-Request-Id`).
- Sentry optional for Python.

## 10. Swapping Models
Replace `app/model.py:predict()` — keep signature. Version via `modelVersion` field, deploy canary by routing `modelVersion=v2` to new replicas.
