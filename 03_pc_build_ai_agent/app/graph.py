"""Explicit state graph: fixed nodes, bounded steps. No open-ended agent loop."""
import asyncio, re
from datetime import datetime, timezone
from .config import settings
from .state import AgentState, AgentRequest, AgentResult, BudgetExceeded
from .tools import call_tool, ToolFailed, ToolDenied, PRICES
from .compat import check_compatibility

CHECKPOINTS: dict[str, dict] = {}   # swap for Redis/PostgreSQL

CPU = {"gaming": ("Ryzen 5 7600", "AM5", "Core i5-13400F", "LGA1700"), "video_editing": ("Ryzen 7 7700", "AM5", "Core i7-13700", "LGA1700"),
       "office": ("Ryzen 5 5600G", "AM4", "Core i3-12100", "LGA1700"), "streaming": ("Ryzen 7 7700", "AM5", "Core i5-13600K", "LGA1700"),
       "ai_rendering": ("Ryzen 9 7900", "AM5", "Core i7-13700K", "LGA1700")}
GPU = {"gaming": (("RTX 4060", 115), ("RX 7600", 165)), "video_editing": (("RTX 4060 Ti", 160), ("RX 7700 XT", 245)),
       "office": (("Integrated", 0), ("Integrated", 0)), "streaming": (("RTX 4060", 115), ("RX 7600", 165)),
       "ai_rendering": (("RTX 4070 Super", 220), ("RX 7800 XT", 263))}
BOARD = {"AM5": "B650M", "AM4": "B550M", "LGA1700": "B760M"}
COMPAT_KW = re.compile(r"compatib|เข้ากัน|ใช้ด้วยกัน|ใส่ได้", re.I)
SPEC_KW = re.compile(r"what is|spec|คืออะไร|ต่างกัน|difference", re.I)

# ---------- nodes: each returns the next node name ----------
async def classify(s: AgentState):
    r, q = s.request, s.request.question
    if r.conversation_id and r.conversation_id in CHECKPOINTS and (q or not r.budget): s.intent = "continue"
    elif len(r.existing_parts) >= 2 and COMPAT_KW.search(q): s.intent = "check_compatibility"
    elif q and SPEC_KW.search(q) and not r.budget: s.intent = "spec_question"
    else: s.intent = "build_new"
    return "extract"

async def extract(s: AgentState):
    r = s.request
    prev = CHECKPOINTS.get(r.conversation_id or "", {}).get("slots", {})
    s.slots = {"budget": r.budget or prev.get("budget"), "use_case": r.use_case or prev.get("use_case"),
               "brand": r.preferred_brand if r.preferred_brand != "any" else prev.get("brand", "any"),
               "constraints": r.constraints.model_dump(exclude_none=True) or prev.get("constraints", {}),
               "existing_parts": [p.model_dump() for p in r.existing_parts] or prev.get("existing_parts", [])}
    if not s.slots["constraints"].get("case_form_factor"):
        s.assumptions.append("Case form factor not given; assuming ATX mid tower.")
    return "ask_missing"

async def ask_missing(s: AgentState):
    if s.intent == "spec_question": s.missing = []
    else:
        if not s.slots["budget"]: s.missing.append("What is your budget in THB?")
        if not s.slots["use_case"]: s.missing.append("What will you use the PC for (gaming, video editing, office, streaming, AI/rendering)?")
        if s.intent == "check_compatibility" and len(s.slots["existing_parts"]) < 2: s.missing.append("List at least two parts to check.")
    return "finish" if s.missing else "plan"

async def plan(s: AgentState):
    s.plan = ["price", "stock", "benchmark", "integrate", "compatibility", "alternatives_rag", "quality", "package"]
    uc, brand = s.slots["use_case"] or "gaming", s.slots["brand"]
    cpu_a, sock_a, cpu_i, sock_i = CPU[uc]
    cpu, sock = (cpu_i, sock_i) if brand == "intel" else (cpu_a, sock_a)
    gpu, watts = GPU[uc][1] if brand == "amd" else GPU[uc][0]
    ram = "16GB DDR5" if sock == "AM5" else "16GB DDR4"
    cand = [dict(type="cpu", name=cpu, socket=sock), dict(type="motherboard", name=BOARD[sock], socket=sock, form_factor="mATX"),
            dict(type="gpu", name=gpu, watts=watts), dict(type="ram", name=ram), dict(type="storage", name="1TB NVMe"),
            dict(type="psu", name="650W 80+ Bronze", wattage=650), dict(type="case", name="ATX Mid Tower")]
    owned = {p["type"]: p for p in s.slots["existing_parts"]}
    # an owned part replaces the candidate entirely; unknown fields stay unknown (never guessed)
    s.parts = [{**{k: v for k, v in owned[c["type"]].items() if v is not None}, "owned": True} if c["type"] in owned
               else {**c, "owned": False} for c in cand]
    for p in s.parts:  # keep gpu watts for owned GPUs we recognise
        if p["type"] == "gpu" and p["owned"] and not p.get("watts"): p["watts"] = 200
    return "fetch"

async def fetch(s: AgentState):
    names = [p["name"] for p in s.parts if not p["owned"]]
    uc = s.slots["use_case"] or "gaming"
    calls = {"price": {"names": names}, "stock": {"names": names}, "benchmark": {"use_case": uc}}
    results = await asyncio.gather(*(call_tool(s, k, v) for k, v in calls.items()), return_exceptions=True)
    for name, res in zip(calls, results):
        if isinstance(res, BudgetExceeded): raise res
        if isinstance(res, (ToolFailed, ToolDenied)):
            s.errors.append(str(res)); s.degraded_services.append(name)
        elif isinstance(res, Exception): raise res
        else: s.observations[name] = res
    return "integrate"

async def integrate(s: AgentState):
    prices = s.observations.get("price", {}).get("prices", {})
    stock = s.observations.get("stock", {}).get("stock", {})
    for p in s.parts:
        p["price"] = 0 if p["owned"] else prices.get(p["name"])
        p["in_stock"] = True if p["owned"] else stock.get(p["name"])   # None = unknown
    priced = [p["price"] for p in s.parts if p["price"] is not None]
    s.data_quality["total_price"] = sum(priced) if "price" not in s.degraded_services else None
    as_of = s.observations.get("price", {}).get("as_of")
    if as_of:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(as_of)).total_seconds()
        s.data_quality["price_age_seconds"] = round(age)
        if age > settings.price_max_age_seconds: s.data_quality["stale_price"] = True
    return "compatibility"

async def compatibility(s: AgentState):
    s.compatibility = check_compatibility(s.parts, s.slots["constraints"])
    if s.compatibility["unknown"]: s.needs_human_review += s.compatibility["unknown"]
    return "alternatives_rag"

async def alternatives_rag(s: AgentState):
    gpu = next(p for p in s.parts if p["type"] == "gpu")
    total, budget = s.data_quality.get("total_price"), s.slots["budget"]
    jobs = {"component_rag": {"gpu": gpu["name"]}}
    if total is not None and budget and total > budget and not gpu["owned"]: jobs["alternatives"] = {"gpu": gpu["name"]}
    results = await asyncio.gather(*(call_tool(s, k, v) for k, v in jobs.items()), return_exceptions=True)
    for name, res in zip(jobs, results):
        if isinstance(res, BudgetExceeded): raise res
        if isinstance(res, Exception): s.errors.append(str(res)); s.degraded_services.append(name)
        elif name == "alternatives": s.alternatives = res["alternatives"]
        else:  # untrusted text: kept as data, length-limited, flagged
            s.evidence += [{"text": re.sub(r"[\x00-\x1f]", " ", n.get("text", ""))[:300], "source": str(n.get("source", ""))[:60], "untrusted": True} for n in res["notes"]]
    return "quality"

async def quality(s: AgentState):
    need = {"price", "stock", "benchmark"}
    s.data_quality["missing_evidence"] = sorted(need & set(s.degraded_services))
    s.data_quality["freshness_ok"] = not s.data_quality.get("stale_price")
    return "package"

async def package(s: AgentState):
    s.data_quality["evidence_complete"] = not s.data_quality["missing_evidence"] and s.compatibility is not None
    return "finish"

NODES = {"classify": classify, "extract": extract, "ask_missing": ask_missing, "plan": plan, "fetch": fetch,
         "integrate": integrate, "compatibility": compatibility, "alternatives_rag": alternatives_rag,
         "quality": quality, "package": package}

def _result(s: AgentState, status: str) -> AgentResult:
    pkg = None
    if s.parts and status != "needs_info":
        pkg = {"request_summary": {k: s.slots.get(k) for k in ("budget", "use_case", "brand", "constraints")},
               "parts": s.parts, "price_breakdown": {p["type"]: p["price"] for p in s.parts if p.get("price") is not None},
               "benchmark": s.observations.get("benchmark"), "compatibility": s.compatibility, "alternatives": s.alternatives,
               "rag_notes": s.evidence, "data_quality": s.data_quality, "assumptions": s.assumptions,
               "sources": sorted({o["source"] for o in s.observations.values() if "source" in o}),
               "updated_at": datetime.now(timezone.utc).isoformat()}
    return AgentResult(status=status, intent=s.intent, questions=s.missing, evidence_package=pkg, errors=s.errors,
                       degraded_services=sorted(set(s.degraded_services)), needs_human_review=s.needs_human_review,
                       remaining_budget=s.remaining_budget, trace=s.trace,
                       versions={"prompt": settings.prompt_version, "policy": settings.policy_version, "graph": "1.0"},
                       request_id=s.request.request_id, conversation_id=s.request.conversation_id or s.request.request_id)

async def run_agent(req: AgentRequest) -> AgentResult:
    s = AgentState(request=req); s.start()
    node, status = "classify", None
    try:
        while node != "finish":
            s.use_step(node)
            node = await NODES[node](s)
    except BudgetExceeded as e:
        s.errors.append(f"budget_exhausted:{e.kind}"); status = "budget_exhausted"
    if status is None:
        status = "needs_info" if s.missing else "degraded" if (s.degraded_services or s.needs_human_review) else "complete"
    if status in ("complete", "degraded"):
        CHECKPOINTS[req.conversation_id or req.request_id] = {"slots": s.slots, "status": status}   # small checkpoint
    return _result(s, status)
