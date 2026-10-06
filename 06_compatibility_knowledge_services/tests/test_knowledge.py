from app.config import settings
from app.main import knowledge_assess
from app.models import KnowledgeRequest

def snap(parts, schema="1.0"):
    return {"schema_version": schema, "parts": parts}

def sourced_parts():
    source = ["https://manufacturer.example/spec"]
    return [
        {"category": "cpu", "part_id": "AMD Ryzen 5 7600", "knowledge_id": "cpu-amd-ryzen-5-7600",
         "spec_sources": source, "specs": {"socket": "AM5", "memory_type": "DDR5", "wattage_draw": 65}},
        {"category": "motherboard", "part_id": "MSI PRO B650M-A WIFI", "spec_sources": source,
         "specs": {"socket": "AM5", "memory_type": "DDR5", "form_factor": "mATX",
                   "supported_cpu_ids": ["cpu-amd-ryzen-5-7600"]}},
        {"category": "ram", "part_id": "Kingston Fury Beast 32GB DDR5", "spec_sources": source,
         "specs": {"memory_type": "DDR5", "capacity_gb": 32}},
        {"category": "gpu", "part_id": "MSI RTX 4060", "spec_sources": source,
         "specs": {"wattage_draw": 115, "length_mm": 199, "power_connectors": ["8-pin"]}},
        {"category": "psu", "part_id": "Corsair CV650", "spec_sources": source,
         "specs": {"wattage": 650, "power_connectors": ["8-pin"]}},
        {"category": "case", "part_id": "MSI MAG FORGE M100A", "spec_sources": source,
         "specs": {"form_factor_support": ["mATX"], "max_gpu_length_mm": 300}},
    ]

def test_compatible_build():
    parts = sourced_parts()
    parts[1]["specs"]["cpu_support_list_status"] = "verified"
    parts[1]["specs"]["bios_version_status"] = "verified"
    parts[1]["specs"]["ram_qvl_status"] = "verified"
    r = knowledge_assess(KnowledgeRequest(request_id="r1", snapshot=snap(parts), budget=60000), x_internal_token=settings.internal_token)
    assert r.compatibility.status == "COMPATIBLE" and not r.compatibility.hard_override
    assert not r.evidence.found and not r.alternatives.options

def test_socket_mismatch_is_hard_incompatible():
    parts = sourced_parts()
    parts[1]["specs"]["socket"] = "LGA1700"
    r = knowledge_assess(KnowledgeRequest(request_id="r2", snapshot=snap(parts)), x_internal_token=settings.internal_token)
    assert r.compatibility.status == "INCOMPATIBLE" and r.compatibility.hard_override

def test_insufficient_psu_is_hard_incompatible():
    parts = sourced_parts()
    parts[3]["specs"]["wattage_draw"] = 220
    parts[4]["specs"]["wattage"] = 300
    r = knowledge_assess(KnowledgeRequest(request_id="r3", snapshot=snap(parts)), x_internal_token=settings.internal_token)
    assert r.compatibility.status == "INCOMPATIBLE"

def test_unknown_socket_needs_review_not_guessed():
    parts = sourced_parts()
    parts[0]["specs"].pop("socket")
    r = knowledge_assess(KnowledgeRequest(request_id="r4", snapshot=snap(parts)), x_internal_token=settings.internal_token)
    assert r.compatibility.status == "NEEDS_REVIEW" and r.degraded

def test_missing_source_evidence_cannot_pass_compatibility():
    parts = sourced_parts()
    parts[1]["spec_sources"] = []
    r = knowledge_assess(KnowledgeRequest(request_id="r9", snapshot=snap(parts)), x_internal_token=settings.internal_token)
    assert r.compatibility.status == "NEEDS_REVIEW"

def test_unverified_bios_and_memory_qvl_require_review():
    parts = sourced_parts()
    parts[1]["specs"]["cpu_support_list_status"] = "verified"
    r = knowledge_assess(KnowledgeRequest(request_id="r10", snapshot=snap(parts)),
                         x_internal_token=settings.internal_token)
    assert r.compatibility.status == "NEEDS_REVIEW"
    assert "Motherboard BIOS version support has not been verified." in r.compatibility.reason_codes

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
