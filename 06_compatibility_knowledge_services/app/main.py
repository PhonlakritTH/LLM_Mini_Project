from fastapi import FastAPI, Header, HTTPException
from .config import settings
from .models import KnowledgeRequest, KnowledgeResponse
from .compat_model import assess
from .rag import retrieve
from .alternatives import find_alternatives

app = FastAPI(title="Compatibility and Knowledge Services", version="1.0")

@app.post("/v1/knowledge/assess", response_model=KnowledgeResponse)
def knowledge_assess(req: KnowledgeRequest, x_internal_token: str = Header(default="")):
    if x_internal_token != settings.internal_token:
        raise HTTPException(401, "UNAUTHORIZED")
    parts = req.snapshot.get("parts", [])
    if req.snapshot.get("schema_version") and req.snapshot["schema_version"] != settings.feature_schema_version:
        # feature schema drift: degrade rather than guess
        return KnowledgeResponse(compatibility=assess([], {}), evidence=retrieve(req.question or "compatibility"),
                                 alternatives=find_alternatives("", None, None), degraded=True,
                                 degraded_services=["schema_drift"], versions=_versions())
    compat = assess(parts, req.constraints)
    gpu = next((p for p in parts if p.get("category") == "gpu"), None)
    query = req.question or (f"power requirements for {gpu['part_id']}" if gpu else "PC build compatibility")
    evidence = retrieve(query, category="gpu" if gpu else None)
    cpu = next((p for p in parts if p.get("category") == "cpu"), None)
    socket = (cpu or {}).get("socket")
    budget_left = (req.budget - sum(p.get("price") or 0 for p in parts)) if req.budget else None
    alt = find_alternatives(gpu["part_id"], socket, budget_left) if gpu else find_alternatives("", socket, budget_left)
    degraded = compat.status == "NEEDS_REVIEW" and "unknown_socket_data" in compat.reason_codes
    return KnowledgeResponse(compatibility=compat, evidence=evidence, alternatives=alt, degraded=degraded,
                             degraded_services=["compatibility_model"] if degraded else [], versions=_versions())

def _versions():
    return {"model": settings.model_version, "embedding": settings.embedding_model,
            "collection": settings.collection_version, "feature_schema": settings.feature_schema_version}

@app.get("/health")
def health(): return {"status": "ok", **_versions()}
