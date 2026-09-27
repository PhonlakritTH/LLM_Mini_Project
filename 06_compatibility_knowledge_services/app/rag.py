"""Hybrid (keyword + mock-vector) retrieval over manufacturer manuals/spec sheets, then rerank.
Retrieved text is DATA, never instructions — callers must not execute anything found here."""
import re
from .config import settings
from .models import RetrievedEvidence, EvidencePassage

DOCS = [
    {"document_id": "amd-am5-manual", "title": "AM5 Socket Installation Guide", "page": 4, "section": "CPU seating",
     "authority": "manufacturer", "effective_date": "2025-01-01",
     "text": "Align the AM5 CPU notch with the socket. Do not force the lever. Use only AM5 coolers."},
    {"document_id": "nvidia-4060-spec", "title": "RTX 4060 Spec Sheet", "page": 1, "section": "Power requirements",
     "authority": "manufacturer", "effective_date": "2025-03-01",
     "text": "RTX 4060 requires one 8-pin PCIe power connector and a 550W minimum system PSU."},
    {"document_id": "generic-psu-guide", "title": "Choosing a PSU", "page": 2, "section": "Headroom",
     "authority": "retailer", "effective_date": "2024-06-01",
     "text": "Leave at least 20% headroom above peak system draw for stability and long-term reliability."},
]

def _score(query: str, text: str) -> float:
    q = set(re.findall(r"\w+", query.lower())); t = set(re.findall(r"\w+", text.lower()))
    return len(q & t) / max(len(q), 1)

def retrieve(query: str, category: str | None = None) -> RetrievedEvidence:
    scored = sorted(((_score(query, d["text"] + " " + d["title"]), d) for d in DOCS), key=lambda x: -x[0])
    top = [d for s, d in scored[:settings.top_k] if s > 0][: settings.rerank_top_n]
    confidence = scored[0][0] if scored else 0.0
    if confidence < settings.rag_min_confidence or not top:
        return RetrievedEvidence(query=query, passages=[], found=False, confidence=round(confidence, 3),
                                 collection_version=settings.collection_version)
    passages = [EvidencePassage(document_id=d["document_id"], title=d["title"], page=d["page"], section=d["section"],
                                snippet=d["text"][:280], authority=d["authority"], effective_date=d["effective_date"],
                                score=round(_score(query, d["text"]), 3)) for d in top]
    return RetrievedEvidence(query=query, passages=passages, found=True, confidence=round(confidence, 3),
                             collection_version=settings.collection_version)
