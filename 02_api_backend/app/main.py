import time, uuid, logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from jose import jwt, JWTError
from pydantic_settings import BaseSettings
from .schemas import BuildRequest, BuildResponse

class Settings(BaseSettings):
    jwt_secret: str = "dev-secret"
    jwt_issuer: str = "pc-spec-builder"
    jwt_audience: str = "web-app"
    cors_allowed_origins: str = "http://localhost:3000"
    rate_limit_per_min: int = 20
    log_level: str = "INFO"
    agent_service_url: str = "http://localhost:8100"
    internal_token: str = "dev-internal"
s = Settings(_env_file=".env")
logging.basicConfig(level=s.log_level)
log = logging.getLogger("api")

app = FastAPI(title="PC Spec Builder API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=s.cors_allowed_origins.split(","),
                   allow_methods=["GET", "POST"], allow_headers=["*"])

class ApiError(Exception):
    def __init__(self, status, code, msg, headers=None):
        self.status, self.code, self.msg, self.headers = status, code, msg, headers or {}

@app.exception_handler(ApiError)
async def api_error(_: Request, e: ApiError):
    return JSONResponse({"error": {"code": e.code, "message": e.msg}}, e.status, e.headers)

def make_token(sub: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=15)
    return jwt.encode({"sub": sub, "iss": s.jwt_issuer, "aud": s.jwt_audience, "exp": exp}, s.jwt_secret, algorithm="HS256")

def current_user(authorization: str = Header(default="")) -> str:
    try:
        tok = authorization.removeprefix("Bearer ")
        return jwt.decode(tok, s.jwt_secret, algorithms=["HS256"], audience=s.jwt_audience, issuer=s.jwt_issuer)["sub"]
    except JWTError:
        raise ApiError(401, "UNAUTHORIZED", "Missing or invalid token.")

_hits: dict[str, deque] = defaultdict(deque)
def rate_limit(request: Request, user: str = Depends(current_user)) -> str:
    q, now = _hits[f"{user}:{request.client.host}"], time.time()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= s.rate_limit_per_min:
        raise ApiError(429, "RATE_LIMITED", "Too many requests.", {"Retry-After": str(int(60 - (now - q[0])) + 1)})
    q.append(now)
    return user

@app.post("/v1/auth/dev-token")  # DEV ONLY: replace with OAuth2/OIDC provider
def dev_token():
    return {"access_token": make_token(f"guest-{uuid.uuid4().hex[:8]}"), "expires_in": 900}

_idem: dict = {}
@app.post("/v1/builder/recommendations", response_model=BuildResponse)
async def recommendations(body: BuildRequest, user: str = Depends(rate_limit),
                          idempotency_key: str | None = Header(default=None)):
    if idempotency_key and (user, idempotency_key) in _idem:
        return _idem[(user, idempotency_key)]
    cid = uuid.uuid4().hex
    log.info("rec cid=%s rid=%s use_case=%s", cid, body.request_id, body.use_case)  # no PII in logs
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{s.agent_service_url}/v1/agent/run",
                json={**body.model_dump(), "constraints": {}},
                headers={"X-Internal-Token": s.internal_token})
        response.raise_for_status()
        agent_result = response.json()
    except (httpx.HTTPError, ValueError) as e:
        log.warning("agent_unavailable cid=%s error=%s", cid, type(e).__name__)
        raise ApiError(503, "RECOMMENDER_UNAVAILABLE", "The recommendation service is temporarily unavailable.") from e

    result = _build_response(agent_result, body)
    result.update(request_id=body.request_id, correlation_id=cid,
                  conversation_id=agent_result.get("conversation_id") or body.conversation_id or uuid.uuid4().hex)
    if idempotency_key:
        _idem[(user, idempotency_key)] = result
    return result

def _build_response(agent_result: dict, body: BuildRequest) -> dict:
    package = agent_result.get("evidence_package") or {}
    if agent_result.get("status") == "needs_info" or not package:
        return BuildResponse(status="needs_info", questions=agent_result.get("questions", []),
            recommendation_code="wait_for_price_drop", compatibility_status="warning", confidence=None,
            summary="ต้องการข้อมูลเพิ่มเติมก่อนจัดสเปก", reasons=[], conflicts=[], parts_list=[],
            price_breakdown={}, benchmark_estimate=None, sources=[], partial_result=True,
            degraded_services=agent_result.get("degraded_services", []), updated_at=datetime.now(timezone.utc).isoformat(),
            request_id=body.request_id, correlation_id="", conversation_id=body.conversation_id or "").model_dump()

    quality = package.get("data_quality", {})
    compat = package.get("compatibility", {})
    raw_status = compat.get("status", "unknown")
    status = {"compatible": "compatible", "warning": "warning", "incompatible": "incompatible"}.get(raw_status, "warning")
    parts = package.get("parts", [])
    total = quality.get("total_price")
    degraded = sorted(set(agent_result.get("degraded_services", [])))
    stock_unknown = any(part.get("in_stock") is None for part in parts)
    if status == "incompatible":
        action = "avoid_combination"
    elif total is None or stock_unknown or any(name in degraded for name in ("price", "stock", "benchmark")):
        action = "wait_for_price_drop"
    elif total > body.budget:
        action = "swap_component" if package.get("alternatives") else "wait_for_price_drop"
    else:
        action = "finalize_build"

    reasons = list(compat.get("conflicts", [])) + list(compat.get("warnings", [])) + list(compat.get("unknown", []))
    if total is not None:
        reasons.append(f"Known total: {total:,} THB against a {body.budget:,} THB budget.")
    if not reasons:
        reasons.append("Compatibility was checked by deterministic component rules.")
    benchmark = package.get("benchmark")
    return BuildResponse(status=agent_result.get("status", "degraded"), questions=agent_result.get("questions", []),
        recommendation_code=action, compatibility_status=status,
        confidence=None,
        summary=("ตรวจพบชิ้นส่วนที่ไม่เข้ากัน" if status == "incompatible" else
             "ราคารวมเกินงบและยังไม่มีตัวเลือกทดแทนที่ยืนยันได้" if total is not None and total > body.budget and action == "wait_for_price_drop" else
             "ข้อมูลราคา/สต็อก/ประสิทธิภาพยังไม่ครบ จึงยังยืนยันรายการซื้อไม่ได้" if action == "wait_for_price_drop" else
                 "สเปกผ่านการตรวจสอบตามข้อมูลที่มี"),
        reasons=reasons, conflicts=compat.get("conflicts", []), suggested_fix=None,
        parts_list=[{"type": p["type"], "name": p["name"], "price": p.get("price"),
                     "in_stock": p.get("in_stock"), "source": package.get("sources", [None])[0] if package.get("sources") else None,
                     "product_url": p.get("product_url"), "owned": p.get("owned", False)} for p in parts],
        price_breakdown={p["type"]: p.get("price") for p in parts},
        benchmark_estimate=benchmark, sources=package.get("sources", []),
        partial_result=agent_result.get("status") != "complete" or bool(degraded),
        degraded_services=degraded, data_quality=quality, updated_at=package.get("updated_at", datetime.now(timezone.utc).isoformat()),
        request_id=body.request_id, correlation_id="", conversation_id=agent_result.get("conversation_id", "")).model_dump()

@app.get("/health")
def health(): return {"status": "ok"}
@app.get("/ready")
def ready(): return {"status": "ready"}
