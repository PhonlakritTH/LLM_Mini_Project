from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
def hdr(): return {"Authorization": "Bearer " + c.post("/v1/auth/dev-token").json()["access_token"]}
def body(**k): return {"budget": 50000, "use_case": "gaming", "request_id": "req-12345678", **k}
def test_requires_auth(): assert c.post("/v1/builder/recommendations", json=body()).status_code == 401
def test_invalid_budget(): assert c.post("/v1/builder/recommendations", json=body(budget=10), headers=hdr()).status_code == 422
def test_incompatible_socket():
    r = c.post("/v1/builder/recommendations", headers=hdr(),
               json=body(existing_parts=[{"type": "motherboard", "name": "Z690", "socket": "LGA1700"}, {"type": "cpu", "name": "x"}]) | {"preferred_brand": "amd"})
    assert r.json()["recommendation_code"] == "avoid_combination"
