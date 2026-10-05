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
    data_integration_service_url: str = "http://localhost:8300"
    knowledge_service_url: str = "http://localhost:8400"
    decision_service_url: str = "http://localhost:8500"
    recommendation_service_url: str = "http://localhost:8600"
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

    result = await _orchestrate(agent_result, body)
    result.update(request_id=body.request_id, correlation_id=cid,
                  conversation_id=agent_result.get("conversation_id") or body.conversation_id or uuid.uuid4().hex)
    if idempotency_key:
        _idem[(user, idempotency_key)] = result
    return result

async def _post_service(base_url: str, path: str, payload: dict) -> dict | None:
    if not base_url:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{base_url}{path}", json=payload,
                                         headers={"X-Internal-Token": s.internal_token})
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as error:
        log.warning("downstream_unavailable path=%s error=%s", path, type(error).__name__)
        return None

def _fallback_response(agent_result: dict, body: BuildRequest, unavailable: str) -> dict:
    result = _build_response(agent_result, body)
    degraded = sorted(set(result.get("degraded_services", [])) | {unavailable})
    result.update(status="degraded", partial_result=True, confidence=None, degraded_services=degraded)
    if result.get("compatibility_status") != "incompatible":
        result.update(recommendation_code="wait_for_price_drop",
                      summary=f"บริการ {unavailable} ไม่พร้อม จึงยังยืนยันผลจัดสเปกไม่ได้")
    return result

async def _orchestrate(agent_result: dict, body: BuildRequest) -> dict:
    package = agent_result.get("evidence_package") or {}
    if not package or agent_result.get("status") == "needs_info":
        return _build_response(agent_result, body)

    agent_parts = package.get("parts", [])
    requested_parts = [{
        "part_id": part["name"], "category": part["type"], "socket": part.get("socket"),
        "wattage_draw": part.get("wattage") or part.get("watts"),
        "form_factor": part.get("form_factor"), "owned": part.get("owned", False),
    } for part in agent_parts]
    snapshot = await _post_service(s.data_integration_service_url, "/v1/integration/snapshot", {
        "request_id": body.request_id, "budget": body.budget, "use_case": body.use_case,
        "existing_parts": body.existing_parts, "requested_parts": requested_parts,
        "records": package.get("records", []),
    })
    if snapshot is None:
        return _fallback_response(agent_result, body, "data_integration")

    data_quality = snapshot.get("data_quality", {})
    degraded = set(agent_result.get("degraded_services", []))
    if data_quality.get("coverage", 0) < 1:
        degraded.add("price")
    if any(part.get("in_stock") is None for part in snapshot.get("parts", [])):
        degraded.add("stock")
    if not any(part.get("performance_index") is not None for part in snapshot.get("parts", [])):
        degraded.add("benchmark")
    if not data_quality.get("freshness_ok", False):
        degraded.add("stale_data")

    knowledge = await _post_service(s.knowledge_service_url, "/v1/knowledge/assess", {
        "request_id": body.request_id, "snapshot": snapshot, "existing_parts": body.existing_parts,
        "constraints": package.get("request_summary", {}).get("constraints", {}),
        "question": body.question, "locale": body.locale, "budget": body.budget,
    })
    if knowledge is None:
        return _fallback_response(agent_result, body, "knowledge_services")
    degraded.update(knowledge.get("degraded_services", []))

    decision = await _post_service(s.decision_service_url, "/v1/decision/evaluate", {
        "request_id": body.request_id, "conversation_id": body.conversation_id,
        "budget": body.budget, "parts": snapshot.get("parts", []),
        "compatibility": knowledge.get("compatibility", {}),
        "alternatives": knowledge.get("alternatives", {"options": []}),
        "evidence": knowledge.get("evidence", {"passages": []}),
        "data_quality": data_quality, "degraded_services": sorted(degraded), "locale": body.locale,
    })
    if decision is None:
        return _fallback_response(agent_result, body, "decision_engine")

    agent_part_by_name = {part["name"]: part for part in agent_parts}
    decision_parts = [{
        "type": part.get("category", "part"), "name": part.get("part_id", "Unknown part"),
        "price": part.get("price"), "in_stock": part.get("in_stock"),
        "owned": part.get("owned", False),
        "product_url": agent_part_by_name.get(part.get("part_id"), {}).get("product_url"),
        "source": agent_part_by_name.get(part.get("part_id"), {}).get("source"),
    } for part in snapshot.get("parts", [])]
    price_records = [record for record in package.get("records", []) if record.get("kind") == "price"]
    price_observed_at = max((record["observed_at"] for record in price_records), default=None)
    formatted = await _post_service(s.recommendation_service_url, "/v1/recommendation/build", {
        "request_id": body.request_id, "conversation_id": body.conversation_id or body.request_id,
        "locale": body.locale, "action_code": decision["action_code"],
        "compatibility_status": decision["compatibility_status"], "confidence": decision["confidence"],
        "escalate": decision["escalate"], "summary": decision["summary"],
        "reasons": decision["reasons"], "immediate_actions": decision["immediate_actions"],
        "citations": decision.get("citations", []), "parts": decision_parts,
        "alternatives": [], "degraded_services": sorted(degraded),
        "price_observed_at": price_observed_at, "consent_live_updates": False,
        "versions": decision.get("versions", {}),
    })
    if formatted is None:
        degraded.add("recommendation_formatter")

    action = (formatted or {}).get("action_code", decision["action_code"])
    status = (formatted or {}).get("compatibility_status", decision["compatibility_status"])
    output_parts = (formatted or {}).get("primary_build", decision_parts)
    required_prices = [part for part in output_parts if not part.get("owned", False)]
    total = sum(part["price"] for part in required_prices) if all(part.get("price") is not None for part in required_prices) else None
    return BuildResponse(
        status="degraded" if degraded or decision.get("escalate") else "complete", questions=[],
        recommendation_code={"FINALIZE_BUILD": "finalize_build", "SWAP_COMPONENT": "swap_component",
                             "WAIT_FOR_PRICE_DROP": "wait_for_price_drop", "AVOID_COMBINATION": "avoid_combination"}[action],
        compatibility_status=status, confidence=decision.get("confidence"),
        summary=(formatted or {}).get("short_summary", decision["summary"]),
        reasons=(formatted or {}).get("reasons", decision["reasons"]),
        conflicts=(knowledge.get("compatibility", {}).get("reason_codes", [])
                   if status == "incompatible" else []), suggested_fix=None,
        parts_list=output_parts,
        price_breakdown={part["type"]: part.get("price") for part in output_parts},
        benchmark_estimate=package.get("benchmark"),
        data_quality={**data_quality, "total_price": total},
        sources=package.get("sources", []) + [f"{item['document_id']}:{item['section']}"
            for item in (formatted or {}).get("sources", [])],
        partial_result=bool(degraded) or bool(decision.get("escalate")),
        degraded_services=sorted(degraded),
        updated_at=(formatted or {}).get("fetched_at", package.get("updated_at", datetime.now(timezone.utc).isoformat())),
        request_id=body.request_id, correlation_id="",
        conversation_id=decision.get("conversation_id", body.conversation_id or body.request_id),
    ).model_dump()

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
