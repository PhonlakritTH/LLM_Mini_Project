from fastapi import FastAPI, Header, HTTPException
from .config import settings
from .models import IntegrationRequest, PartCatalogSnapshot
from .pipeline import build_snapshot

app = FastAPI(title="Data Integration", version="1.0")

@app.post("/v1/integration/snapshot", response_model=PartCatalogSnapshot)
def snapshot(req: IntegrationRequest, x_internal_token: str = Header(default="")):
    if x_internal_token != settings.internal_token:
        raise HTTPException(401, "UNAUTHORIZED")
    return build_snapshot(req)

@app.get("/health")
def health(): return {"status": "ok", "schema_version": settings.canonical_schema_version}
