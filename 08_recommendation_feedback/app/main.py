from fastapi import FastAPI, Header, HTTPException
from .config import settings
from .models import FormatRequest, RecommendationResponse, Feedback, FeedbackReceipt
from .formatter import build_response
from . import feedback as fb_store

app = FastAPI(title="Recommendation and Feedback", version="1.0")

@app.post("/v1/recommendation/build", response_model=RecommendationResponse)
def build(req: FormatRequest, x_internal_token: str = Header(default="")):
    if x_internal_token != settings.internal_token:
        raise HTTPException(401, "UNAUTHORIZED")
    return build_response(req)

@app.post("/v1/feedback", response_model=FeedbackReceipt)
def feedback(fb: Feedback, x_internal_token: str = Header(default="")):
    if x_internal_token != settings.internal_token:
        raise HTTPException(401, "UNAUTHORIZED")
    return fb_store.submit(fb)

@app.get("/v1/safety-queue")
def safety_queue(x_internal_token: str = Header(default="")):
    if x_internal_token != settings.internal_token:
        raise HTTPException(401, "UNAUTHORIZED")
    return fb_store.SAFETY_QUEUE

@app.get("/health")
def health(): return {"status": "ok", "schema_version": settings.recommendation_schema_version}
