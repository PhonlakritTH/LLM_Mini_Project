"""Explicit state graph: fixed nodes, bounded steps. No open-ended agent loop."""
import asyncio, re
from datetime import datetime, timezone
from .config import settings
from .state import AgentState, AgentRequest, AgentResult, BudgetExceeded
from .tools import call_tool, ToolFailed, ToolDenied
from .compat import check_compatibility
from .knowledge_base import BY_ID, BY_TYPE

CHECKPOINTS: dict[str, dict] = {}   # swap for Redis/PostgreSQL

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
               "gpu_brand": r.preferred_gpu_brand if r.preferred_gpu_brand != "any" else
                   ("nvidia" if r.preferred_brand == "nvidia" else prev.get("gpu_brand", "any")),
               "cpu_model": r.preferred_cpu_model or prev.get("cpu_model"),
               "gpu_model": r.preferred_gpu_model or prev.get("gpu_model"),
               "constraints": r.constraints.model_dump(exclude_none=True) or prev.get("constraints", {}),
               "existing_parts": [p.model_dump() for p in r.existing_parts] or prev.get("existing_parts", [])}
    if not s.slots["constraints"].get("case_form_factor"):
        s.slots["constraints"]["case_form_factor"] = "mATX"
        s.assumptions.append("Using a sourced mATX case and motherboard combination.")
    return "ask_missing"

async def ask_missing(s: AgentState):
    if s.intent == "spec_question": s.missing = []
    else:
        if not s.slots["budget"]: s.missing.append("What is your budget in THB?")
        if not s.slots["use_case"]: s.missing.append("What will you use the PC for (gaming, video editing, office, streaming, AI/rendering)?")
        if s.intent == "check_compatibility" and len(s.slots["existing_parts"]) < 2: s.missing.append("List at least two parts to check.")
    return "finish" if s.missing else "plan"

async def plan(s: AgentState):
    s.plan = ["knowledge_base", "price_reference", "integrate", "compatibility", "quality", "package"]
    brand = s.slots["brand"]
    cpus = [part for part in BY_TYPE["cpu"] if brand in ("any", "nvidia") or part["brand"] == brand]
    if s.slots.get("cpu_model"):
        query = s.slots["cpu_model"].casefold()
        cpus = [part for part in cpus if query in part["name"].casefold()]
        if not cpus:
            s.missing.append("The requested CPU model is not in the sourced component knowledge base.")
            return "finish"

    use_case = s.slots["use_case"] or "gaming"
    wants_gpu = use_case != "office" or bool(s.slots.get("gpu_model")) or s.slots["gpu_brand"] != "any"
    if not wants_gpu:
        cpus = [part for part in cpus if part["specs"].get("integrated_graphics")]
    gpus = BY_TYPE["gpu"] if wants_gpu else [None]
    gpu_brand = s.slots["gpu_brand"]
    if wants_gpu and gpu_brand != "any":
        gpus = [part for part in gpus if part["brand"] == gpu_brand]
    if wants_gpu and s.slots.get("gpu_model"):
        query = s.slots["gpu_model"].casefold()
        gpus = [part for part in gpus if query in part["name"].casefold()]
        if not gpus:
            s.missing.append("The requested GPU model is not in the sourced component knowledge base.")
            return "finish"

    cand_builds = []
    for cpu in cpus:
        board = next((part for part in BY_TYPE["motherboard"]
                      if cpu["part_id"] in part["specs"]["supported_cpu_ids"]), None)
        ram = next((part for part in BY_TYPE["ram"]
                    if part["specs"]["memory_type"] == cpu["specs"]["memory_type"]), None)
        if not board or not ram:
            continue
        fixed = [cpu, board, ram, *[BY_ID["storage-wd-blue-sn580-1tb"],
                BY_ID["psu-corsair-cv650"], BY_ID["case-msi-mag-forge-m100a"]]]
        for gpu in gpus:
            chosen = fixed + ([gpu] if gpu else [])
            owned = {p["type"]: p for p in s.slots["existing_parts"]}
            build = []
            for component in chosen:
                if component["type"] in owned:
                    old = owned[component["type"]]
                    build.append({"part_id": f"owned-{component['type']}", "type": component["type"],
                                  "name": old["name"], "specs": {
                                      "socket": old.get("socket"), "wattage": old.get("wattage")},
                                  "source": None, "rank": 0, "owned": True})
                else:
                    build.append({**component, "owned": False})
            cand_builds.append(build)
    s.candidate_builds = cand_builds
    if not cand_builds:
        s.missing.append("No sourced component combination matches the requested preferences.")
        return "finish"
    return "fetch"

async def fetch(s: AgentState):
    candidates = {part["name"]: part for build in s.candidate_builds for part in build if not part["owned"]}
    names = sorted(candidates)
    calls = {"price": {"names": names,
                       "search_terms": {name: candidates[name]["search_terms"] for name in names}}}
    results = await asyncio.gather(*(call_tool(s, k, v) for k, v in calls.items()), return_exceptions=True)
    for name, res in zip(calls, results):
        if isinstance(res, BudgetExceeded): raise res
        if isinstance(res, (ToolFailed, ToolDenied)):
            s.errors.append(str(res)); s.degraded_services.append(name)
        elif isinstance(res, Exception): raise res
        else:
            s.observations[name] = res
            if res.get("missing"):
                s.degraded_services.append(name)
    return "integrate"

async def integrate(s: AgentState):
    prices = s.observations.get("price", {}).get("prices", {})
    ranges = s.observations.get("price", {}).get("ranges", {})
    for build in s.candidate_builds:
        for part in build:
            part["price"] = None if part["owned"] else prices.get(part["name"])
            part["price_low"], part["price_high"] = (None, None) if part["owned"] else ranges.get(part["name"], (None, None))
            part["spec_source"] = part.get("source")

    budget = s.slots["budget"] or 0
    complete = []
    for build in s.candidate_builds:
        priced = [p for p in build if not p["owned"]]
        if priced and all(p.get("price_low") is not None and p.get("price_high") is not None for p in priced):
            low = sum(p["price_low"] for p in priced)
            high = sum(p["price_high"] for p in priced)
            rank = sum(p.get("rank", 0) for p in build)
            complete.append((build, low, high, rank))

    affordable = [item for item in complete if item[2] <= budget]
    if affordable:
        chosen, low, high, _rank = max(affordable, key=lambda item: (item[3], item[2]))
        s.data_quality["budget_fit"] = "within_budget"
    elif complete:
        chosen, low, high, _rank = min(complete, key=lambda item: (item[2], -item[3]))
        s.data_quality["budget_fit"] = "over_budget"
    else:
        chosen = max(s.candidate_builds, key=lambda build: sum(part.get("rank", 0) for part in build))
        low = high = None
        s.data_quality["budget_fit"] = "unknown"
    s.parts = chosen
    s.data_quality["total_price_range"] = (
        {"low": low, "high": high, "currency": "THB"} if low is not None and high is not None else None)
    s.data_quality["total_price"] = (
        round(sum(p["price"] for p in chosen if not p["owned"]))
        if all(p["owned"] or p.get("price") is not None for p in chosen) else None)
    s.data_quality["unpriced_parts"] = [p["name"] for p in chosen if not p["owned"] and p.get("price_low") is None]
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
    s.alternatives = []
    s.evidence = []
    return "quality"

async def quality(s: AgentState):
    s.data_quality["missing_evidence"] = sorted({"price"} & set(s.degraded_services))
    s.data_quality["freshness_ok"] = not s.data_quality.get("stale_price")
    s.data_quality["price_reference_source"] = "Google Shopping via SerpApi"
    s.data_quality["price_reference_note"] = "Indicative market range from matched search results; not a quote."
    s.data_quality["price_reference_observed_at"] = s.observations.get("price", {}).get("as_of")
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
        pkg = {"request_summary": {k: s.slots.get(k) for k in ("budget", "use_case", "brand", "gpu_brand", "cpu_model", "gpu_model", "constraints")},
               "parts": s.parts, "price_breakdown": {p["type"]: p["price"] for p in s.parts if p.get("price") is not None},
               "benchmark": s.observations.get("benchmark"), "compatibility": s.compatibility, "alternatives": s.alternatives,
               "rag_notes": s.evidence, "data_quality": s.data_quality, "assumptions": s.assumptions,
               "records": [record for observation in s.observations.values() for record in observation.get("records", [])],
               "sources": sorted({p["spec_source"] for p in s.parts if p.get("spec_source")} |
                                 {o["source"] for o in s.observations.values() if "source" in o}),
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
