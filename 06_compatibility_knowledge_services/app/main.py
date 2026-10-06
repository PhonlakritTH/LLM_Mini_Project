from fastapi import FastAPI, Header, HTTPException
from .config import settings
from .models import (KnowledgeRequest, KnowledgeResponse, RetrievedEvidence, AlternativeBuildOptions)
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
        query = req.question or "compatibility"
        return KnowledgeResponse(compatibility=assess([], {}),
                                 evidence=RetrievedEvidence(query=query, passages=[], found=False, confidence=0.0,
                                                            collection_version=settings.collection_version),
                                 alternatives=AlternativeBuildOptions(options=[], excluded=[]), degraded=True,
                                 degraded_services=["schema_drift", "rag_provider_unavailable", "alternatives_provider_unavailable"],
                                 versions=_versions())
    compat = assess(parts, req.constraints)
    gpu = next((p for p in parts if p.get("category") == "gpu"), None)
    query = req.question or (f"power requirements for {gpu['part_id']}" if gpu else "PC build compatibility")
    degraded_services = []
    if settings.enable_sample_knowledge:
        evidence = retrieve(query, category="gpu" if gpu else None)
        cpu = next((p for p in parts if p.get("category") == "cpu"), None)
        socket = (cpu or {}).get("socket")
        budget_left = (req.budget - sum(p.get("price") or 0 for p in parts)) if req.budget else None
        alt = find_alternatives(gpu["part_id"], socket, budget_left) if gpu else find_alternatives("", socket, budget_left)
    else:
        evidence = RetrievedEvidence(query=query, passages=[], found=False, confidence=0.0,
                                     collection_version=settings.collection_version)
        alt = AlternativeBuildOptions(options=[], excluded=[])
        # Optional retrieval and alternative suggestions do not block a compatibility assessment.
    if compat.status == "NEEDS_REVIEW":
        degraded_services.append("compatibility_evidence_unverified")
    degraded = bool(degraded_services)
    return KnowledgeResponse(compatibility=compat, evidence=evidence, alternatives=alt, degraded=degraded,
                             degraded_services=degraded_services, versions=_versions())

def _versions():
    return {"model": settings.model_version, "embedding": settings.embedding_model,
            "collection": settings.collection_version, "feature_schema": settings.feature_schema_version}

@app.get("/health")
def health(): return {"status": "ok", **_versions()}
