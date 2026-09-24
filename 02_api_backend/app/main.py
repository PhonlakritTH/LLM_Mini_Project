import time, uuid, logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from pydantic_settings import BaseSettings
from .schemas import BuildRequest, BuildResponse
from .agent_stub import recommend

class Settings(BaseSettings):
    jwt_secret: str = "dev-secret"
    jwt_issuer: str = "pc-spec-builder"
    jwt_audience: str = "web-app"
    cors_allowed_origins: str = "http://localhost:3000"
    rate_limit_per_min: int = 20
    log_level: str = "INFO"
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
    result = await recommend(body)
    result.update(request_id=body.request_id, correlation_id=cid,
                  conversation_id=body.conversation_id or uuid.uuid4().hex)
    if idempotency_key:
        _idem[(user, idempotency_key)] = result
    return result

@app.get("/health")
def health(): return {"status": "ok"}
@app.get("/ready")
def ready(): return {"status": "ready"}
