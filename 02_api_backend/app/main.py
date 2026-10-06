import time, uuid, logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus
from fastapi import FastAPI, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from jose import jwt, JWTError
from pydantic_settings import BaseSettings, SettingsConfigDict
from .schemas import BuildRequest, BuildResponse

class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
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

def _store_search_links(part_name: str) -> list[dict[str, str]]:
    query = quote_plus(part_name)
    return [
        {"store": "BaNANA", "url": f"https://www.bnn.in.th/th/p?q={query}"},
        {"store": "Amazon.com", "url": f"https://www.amazon.com/s?k={query}"},
    ]

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
        if path == "/v1/decision/evaluate" and response.is_error:
            try:
                detail = response.json().get("detail")
            except ValueError:
                detail = None
            if not isinstance(detail, str):
                detail = "The decision/LLM service returned an error. Check its container logs."
            log.warning("decision_service_error status=%s detail=%s",
                        response.status_code, detail)
            raise ApiError(503, "LLM_PROVIDER_ERROR", detail)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as error:
        log.warning("downstream_http_error path=%s status=%s",
                    path, error.response.status_code)
        return None
    except (httpx.HTTPError, ValueError) as error:
        log.warning("downstream_unavailable path=%s error=%s", path, type(error).__name__)
        return None

def _fallback_response(agent_result: dict, body: BuildRequest, unavailable: str) -> dict:
    result = _build_response(agent_result, body)
    degraded = sorted(set(result.get("degraded_services", [])) | {unavailable})
    result.update(status="degraded", partial_result=True, confidence=None, degraded_services=degraded)
    if result.get("compatibility_status") != "incompatible":
        result.update(recommendation_code="needs_price_data",
                      summary=f"บริการ {unavailable} ไม่พร้อม จึงยังยืนยันผลจัดสเปกไม่ได้")
    return result

async def _orchestrate(agent_result: dict, body: BuildRequest) -> dict:
    package = agent_result.get("evidence_package") or {}
    if not package or agent_result.get("status") == "needs_info":
        return _build_response(agent_result, body)

    agent_parts = package.get("parts", [])
    requested_parts = [{
        "part_id": part["name"], "knowledge_id": part.get("part_id"),
        "category": part["type"], "socket": part.get("specs", {}).get("socket"),
        "wattage_draw": part.get("wattage") or part.get("watts") or part.get("specs", {}).get("wattage"),
        "form_factor": part.get("specs", {}).get("form_factor"),
        "specs": part.get("specs", {}),
        "spec_source": part.get("spec_source"),
        "owned": part.get("owned", False),
    } for part in agent_parts]
    existing_parts_dicts = [p.model_dump() for p in body.existing_parts]
    snapshot = await _post_service(s.data_integration_service_url, "/v1/integration/snapshot", {
        "request_id": body.request_id, "budget": body.budget, "use_case": body.use_case,
        "existing_parts": existing_parts_dicts, "requested_parts": requested_parts,
        "records": package.get("records", []),
    })
    if snapshot is None:
        return _fallback_response(agent_result, body, "data_integration")

    data_quality = {**snapshot.get("data_quality", {}), **package.get("data_quality", {})}
    degraded = set(agent_result.get("degraded_services", []))
    if data_quality.get("coverage", 0) < 1:
        degraded.add("price")
    else:
        degraded.discard("price")
    if not data_quality.get("freshness_ok", True):
        degraded.add("stale_data")
    else:
        degraded.discard("stale_data")

    knowledge = await _post_service(s.knowledge_service_url, "/v1/knowledge/assess", {
        "request_id": body.request_id, "snapshot": snapshot, "existing_parts": existing_parts_dicts,
        "constraints": package.get("request_summary", {}).get("constraints", {}),
        "question": body.question, "locale": body.locale, "budget": body.budget,
    })
    if knowledge is None:
        return _fallback_response(agent_result, body, "knowledge_services")
    degraded.update(knowledge.get("degraded_services", []))

    decision_parts = [{
        **part,
        "price": round((part["price_low"] + part["price_high"]) / 2)
        if part.get("price_low") is not None and part.get("price_high") is not None else part.get("price"),
    } for part in snapshot.get("parts", [])]
    decision = await _post_service(s.decision_service_url, "/v1/decision/evaluate", {
        "request_id": body.request_id, "conversation_id": body.conversation_id,
        "budget": body.budget, "parts": decision_parts,
        "compatibility": knowledge.get("compatibility", {}),
        "alternatives": knowledge.get("alternatives", {"options": []}),
        "evidence": knowledge.get("evidence", {"passages": []}),
        "data_quality": data_quality, "degraded_services": sorted(degraded), "locale": body.locale,
    })
    if decision is None:
        raise ApiError(503, "DECISION_ENGINE_UNAVAILABLE",
                       "The live decision/LLM service is unavailable; no generated explanation was returned.")

    decision_parts = [{
        "type": part.get("category", "part"), "name": part.get("part_id", "Unknown part"),
        "price": part.get("price"), "price_low": part.get("price_low"), "price_high": part.get("price_high"),
        "price_source": part.get("price_source"),
        "spec_source": (part.get("spec_sources") or [None])[0],
        "owned": part.get("owned", False),
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
        "price_observed_at": price_observed_at,
        "total_price_range": data_quality.get("total_price_range"),
        "consent_live_updates": False,
        "versions": decision.get("versions", {}),
    })
    if formatted is None:
        degraded.add("recommendation_formatter")

    action = (formatted or {}).get("action_code", decision["action_code"])
    status = (formatted or {}).get("compatibility_status", decision["compatibility_status"])
    output_parts = (formatted or {}).get("primary_build", decision_parts)
    required_prices = [part for part in output_parts if not part.get("owned", False)]
    ranges_complete = all(part.get("price_low") is not None and part.get("price_high") is not None
                          for part in required_prices)
    total_range = ({
        "low": sum(part["price_low"] for part in required_prices),
        "high": sum(part["price_high"] for part in required_prices),
        "currency": "THB",
    } if required_prices and ranges_complete else None)
    total = round(sum((part.get("price_low", part.get("price", 0)) +
                       part.get("price_high", part.get("price", 0))) / 2
                      for part in required_prices)) if all(part.get("price") is not None for part in required_prices) else None
    
    is_fully_compatible_and_in_budget = (action == "FINALIZE_BUILD" and status == "compatible")
    final_status = "complete" if (is_fully_compatible_and_in_budget or not degraded and not decision.get("escalate")) else "degraded"

    return BuildResponse(
        status=final_status, questions=[],
        recommendation_code={"FINALIZE_BUILD": "finalize_build", "SWAP_COMPONENT": "swap_component",
                             "RECONFIGURE_BUILD": "reconfigure_build", "NEEDS_PRICE_DATA": "needs_price_data",
                             "NEEDS_REVIEW": "needs_review",
                             "AVOID_COMBINATION": "avoid_combination"}[action],
        compatibility_status=status, confidence=decision.get("confidence"),
        summary=(formatted or {}).get("short_summary", decision["summary"]),
        reasons=(formatted or {}).get("reasons", decision["reasons"]),
        limitations=(formatted or {}).get("limitations", []),
        conflicts=(knowledge.get("compatibility", {}).get("reason_codes", [])
                   if status == "incompatible" else []), suggested_fix=None,
        parts_list=[{
            **part,
            "store_search_links": [] if part.get("owned") else _store_search_links(part["name"]),
        } for part in output_parts],
        price_breakdown={part["type"]: part.get("price") for part in output_parts},
        data_quality={**data_quality, "total_price": total, "total_price_range": total_range,
                      "budget_is_estimate": True},
        sources=list(dict.fromkeys(
            package.get("sources", [])
            + [f"{item['document_id']}:{item['section']}" for item in (formatted or {}).get("sources", [])]
            + knowledge.get("compatibility", {}).get("evidence_sources", [])
        )),
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
            recommendation_code="needs_price_data", compatibility_status="warning", confidence=None,
            summary="ต้องการข้อมูลเพิ่มเติมก่อนจัดสเปก", reasons=[], limitations=[], conflicts=[], parts_list=[],
            price_breakdown={}, sources=[], partial_result=True,
            degraded_services=agent_result.get("degraded_services", []), updated_at=datetime.now(timezone.utc).isoformat(),
            request_id=body.request_id, correlation_id="", conversation_id=body.conversation_id or "").model_dump()

    quality = package.get("data_quality", {})
    compat = package.get("compatibility", {})
    raw_status = compat.get("status", "unknown")
    status = {"compatible": "compatible", "warning": "warning", "incompatible": "incompatible"}.get(raw_status, "warning")
    parts = package.get("parts", [])
    total = quality.get("total_price")
    degraded = sorted(set(agent_result.get("degraded_services", [])))
    price_range = quality.get("total_price_range") or {}
    price_range_overlaps_budget = (
        price_range.get("low") is not None and price_range.get("high") is not None
        and price_range["low"] <= body.budget < price_range["high"]
    )
    if status == "incompatible":
        action = "avoid_combination"
    elif total is None or any(name in degraded for name in ("price",)):
        action = "needs_price_data"
    elif status == "warning" or price_range_overlaps_budget:
        action = "needs_review"
    elif total > body.budget:
        action = "swap_component" if package.get("alternatives") else "reconfigure_build"
    else:
        action = "finalize_build"

    reasons = list(compat.get("conflicts", [])) + list(compat.get("warnings", [])) + list(compat.get("unknown", []))
    if total is not None:
        reasons.append(f"Known total: {total:,} THB against a {body.budget:,} THB budget.")
    if not reasons:
        reasons.append("Compatibility was checked by deterministic component rules.")
    limitations = []
    if degraded:
        limitations.append(f"ข้อมูลบางส่วนยังตรวจไม่ได้: {', '.join(degraded)}")
    if quality.get("price_reference_note"):
        limitations.append(quality["price_reference_note"])
    if compat.get("unknown"):
        limitations.append("ความเข้ากันได้บางด้านยังต้องตรวจจากคู่มือ/รายการ support ของผู้ผลิต")
    return BuildResponse(status=agent_result.get("status", "degraded"), questions=agent_result.get("questions", []),
        recommendation_code=action, compatibility_status=status,
        confidence=None,
        summary=("ตรวจพบชิ้นส่วนที่ไม่เข้ากัน" if status == "incompatible" else
             "ราคารวมอ้างอิงเกินงบที่กำหนด" if total is not None and total > body.budget and action == "reconfigure_build" else
             "ข้อมูลราคาอ้างอิงยังไม่ครบ จึงยังประเมินงบรวมไม่ได้" if action == "needs_price_data" else
             "มีช่วงราคาอ้างอิงแล้ว แต่ต้องตรวจสอบความเข้ากันได้หรือช่วงงบก่อนยืนยัน" if action == "needs_review" else
                 "สเปกผ่านการตรวจสอบตามข้อมูลที่มี"),
        reasons=reasons, limitations=limitations, conflicts=compat.get("conflicts", []), suggested_fix=None,
        parts_list=[{"type": p["type"], "name": p["name"], "price": p.get("price"),
                     "price_low": p.get("price_low"), "price_high": p.get("price_high"),
                     "price_source": p.get("price_source"),
                     "spec_source": p.get("spec_source"),
                     "owned": p.get("owned", False),
                     "store_search_links": [] if p.get("owned") else _store_search_links(p["name"])}
                    for p in parts],
        price_breakdown={p["type"]: p.get("price") for p in parts},
        sources=list(dict.fromkeys(
            package.get("sources", []) + compat.get("evidence_sources", [])
        )),
        partial_result=agent_result.get("status") != "complete" or bool(degraded),
        degraded_services=degraded,         data_quality={**quality, "budget_is_estimate": True}, updated_at=package.get("updated_at", datetime.now(timezone.utc).isoformat()),
        request_id=body.request_id, correlation_id="", conversation_id=agent_result.get("conversation_id", "")).model_dump()

@app.get("/health")
def health(): return {"status": "ok"}
@app.get("/ready")
def ready(): return {"status": "ready"}
