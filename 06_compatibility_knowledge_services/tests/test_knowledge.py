from app.config import settings
from app.main import knowledge_assess
from app.models import KnowledgeRequest

def snap(parts, schema="1.0"):
    return {"schema_version": schema, "parts": parts}

def test_compatible_build():
    parts = [{"category": "cpu", "part_id": "Ryzen 5 7600", "socket": "AM5", "wattage_draw": 65},
             {"category": "motherboard", "part_id": "B650M", "socket": "AM5"},
             {"category": "gpu", "part_id": "RTX 4060", "wattage_draw": 115, "price": 10500},
             {"category": "psu", "part_id": "650W", "wattage_draw": 650}]
    r = knowledge_assess(KnowledgeRequest(request_id="r1", snapshot=snap(parts), budget=60000), x_internal_token=settings.internal_token)
    assert r.compatibility.status == "COMPATIBLE" and not r.compatibility.hard_override
    assert not r.evidence.found and not r.alternatives.options
    assert {"rag_provider_unavailable", "alternatives_provider_unavailable"}.issubset(r.degraded_services)

def test_socket_mismatch_is_hard_incompatible():
    parts = [{"category": "cpu", "part_id": "Ryzen 5 7600", "socket": "AM5"},
             {"category": "motherboard", "part_id": "Z690", "socket": "LGA1700"}]
    r = knowledge_assess(KnowledgeRequest(request_id="r2", snapshot=snap(parts)), x_internal_token=settings.internal_token)
    assert r.compatibility.status == "INCOMPATIBLE" and r.compatibility.hard_override

def test_insufficient_psu_is_hard_incompatible():
    parts = [{"category": "cpu", "part_id": "c", "wattage_draw": 65}, {"category": "gpu", "part_id": "RTX 4070 Super", "wattage_draw": 220},
             {"category": "psu", "part_id": "p", "wattage_draw": 300}]
    r = knowledge_assess(KnowledgeRequest(request_id="r3", snapshot=snap(parts)), x_internal_token=settings.internal_token)
    assert r.compatibility.status == "INCOMPATIBLE"

def test_unknown_socket_needs_review_not_guessed():
    parts = [{"category": "cpu", "part_id": "c"}, {"category": "motherboard", "part_id": "m"}]
    r = knowledge_assess(KnowledgeRequest(request_id="r4", snapshot=snap(parts)), x_internal_token=settings.internal_token)
    assert r.compatibility.status == "NEEDS_REVIEW" and r.degraded

def test_alternatives_exclude_wrong_socket():
    alt_socket = [{"category": "cpu", "part_id": "Ryzen 9 7900", "socket": "AM5"}, {"category": "gpu", "part_id": "RTX 4070 Super"}]
    r = knowledge_assess(KnowledgeRequest(request_id="r5", snapshot=snap(alt_socket), budget=100000), x_internal_token=settings.internal_token)
    assert all(o.to_part != "Core i5-13600K" for o in r.alternatives.options)

def test_low_confidence_rag_returns_not_found():
    r = knowledge_assess(KnowledgeRequest(request_id="r6", snapshot=snap([]), question="xyz unrelated gibberish query"), x_internal_token=settings.internal_token)
    assert not r.evidence.found

def test_schema_drift_degrades():
    r = knowledge_assess(KnowledgeRequest(request_id="r7", snapshot=snap([], schema="9.9")), x_internal_token=settings.internal_token)
    assert r.degraded and "schema_drift" in r.degraded_services

def test_default_flow_never_returns_sample_knowledge():
    assert settings.enable_sample_knowledge is False
    response = knowledge_assess(KnowledgeRequest(request_id="r8", snapshot=snap([
        {"category": "gpu", "part_id": "RTX 4060", "wattage_draw": 115}
    ])), x_internal_token=settings.internal_token)
    assert response.evidence.passages == []
    assert response.alternatives.options == []
