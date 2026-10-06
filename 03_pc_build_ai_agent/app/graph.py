"""Explicit state graph: fixed nodes, bounded steps. No open-ended agent loop."""
import asyncio, re
from datetime import datetime, timezone
from .config import settings
from .state import AgentState, AgentRequest, AgentResult, BudgetExceeded
from .tools import call_tool, ToolFailed, ToolDenied
from .compat import check_compatibility
from .knowledge_base import BY_ID, BY_TYPE
from .manufacturer_sources import fetch_manufacturer_facts_for_parts

CHECKPOINTS: dict[str, dict] = {}   # swap for Redis/PostgreSQL

COMPAT_KW = re.compile(r"compatib|เข้ากัน|ใช้ด้วยกัน|ใส่ได้", re.I)
SPEC_KW = re.compile(r"what is|spec|คืออะไร|ต่างกัน|difference", re.I)

def infer_part_specs(part: dict) -> dict:
    name = str(part.get("name") or "")
    ptype = str(part.get("type") or "")
    socket = part.get("socket")
    wattage = part.get("wattage")
    name_lower = name.lower()

    # Auto-extract PSU wattage
    if ptype == "psu" and not wattage:
        m_watt = re.search(r"(\d{3,4})\s*(?:w|watt)?", name_lower)
        if m_watt:
            val = int(m_watt.group(1))
            if 200 <= val <= 2500:
                wattage = val

    # Auto-extract Socket for CPU / Motherboard
    if ptype in ("cpu", "motherboard") and not socket:
        if any(kw in name_lower for kw in ("lga1700", "1700", "b760", "z790", "h610", "z690", "b660", "12400", "13400", "13600", "14400", "14600", "14700", "12600", "12700", "12900", "13700", "13900", "14900")):
            socket = "LGA1700"
        elif any(kw in name_lower for kw in ("am5", "b650", "x670", "a620", "7600", "7700", "7800", "7900", "7950", "9600", "9700", "9800", "9900", "9950")):
            socket = "AM5"
        elif any(kw in name_lower for kw in ("am4", "b450", "b550", "x570", "a520", "5600", "5700", "5800", "5900", "3600", "3700", "2600")):
            socket = "AM4"
        elif any(kw in name_lower for kw in ("lga1200", "1200", "b560", "z590", "h510", "b460", "z490", "10400", "10700", "11400", "11700")):
            socket = "LGA1200"
        elif any(kw in name_lower for kw in ("lga1851", "1851", "z890", "b860", "ultra 5", "ultra 7", "ultra 9", "245k", "265k", "285k")):
            socket = "LGA1851"

    res = dict(part)
    if socket:
        res["socket"] = socket
    if wattage:
        res["wattage"] = wattage
    return res

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
    raw_existing = [p.model_dump() for p in r.existing_parts] or prev.get("existing_parts", [])
    inferred_existing = [infer_part_specs(p) for p in raw_existing]

    constraints = r.constraints.model_dump(exclude_none=True) or prev.get("constraints", {})

    # Extract free-text requirements from question
    q = (r.question or "").lower()
    if any(w in q for w in ("wi-fi", "wifi", "ไวไฟ")):
        constraints["wifi_required"] = True
        s.assumptions.append("ผู้ใช้ต้องการเมนบอร์ดที่มี Wi-Fi ในตัว")
    if any(w in q for w in ("เงียบ", "quiet", "silent")):
        constraints["low_noise"] = True
        s.assumptions.append("ผู้ใช้เน้นความเงียบในการทำงาน")
    if any(w in q for w in ("ขาว", "white")):
        constraints["white_theme"] = True
        s.assumptions.append("ผู้ใช้ต้องการเคสและโทนชิ้นส่วนสีขาว")
    elif any(w in q for w in ("ดำ", "black")):
        constraints["black_theme"] = True
    
    if any(w in q for w in ("2tb", "2 tb", "2000gb")):
        constraints["min_storage_gb"] = 2000
    elif any(w in q for w in ("500gb", "500 gb", "512")):
        constraints["min_storage_gb"] = 500
    elif any(w in q for w in ("1tb", "1 tb", "1000gb")):
        constraints["min_storage_gb"] = 1000

    if any(w in q for w in ("32gb", "32 gb", "32")):
        constraints["min_ram_gb"] = 32
    elif any(w in q for w in ("16gb", "16 gb")):
        constraints["min_ram_gb"] = 16

    if any(w in q for w in ("valorant", "fps", "gta", "elden", "genshin")):
        constraints["gaming_focus"] = True

    s.slots = {"budget": r.budget or prev.get("budget"), "use_case": r.use_case or prev.get("use_case"),
               "brand": r.preferred_brand if r.preferred_brand != "any" else prev.get("brand", "any"),
               "gpu_brand": r.preferred_gpu_brand if r.preferred_gpu_brand != "any" else
                   ("nvidia" if r.preferred_brand == "nvidia" else prev.get("gpu_brand", "any")),
               "cpu_model": r.preferred_cpu_model or prev.get("cpu_model"),
               "gpu_model": r.preferred_gpu_model or prev.get("gpu_model"),
               "constraints": constraints,
               "existing_parts": inferred_existing}
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
    s.plan = ["knowledge_base", "price_reference", "integrate", "manufacturer_specs",
              "compatibility", "quality", "package"]
    brand = s.slots["brand"]
    budget = s.slots["budget"] or 40000
    constraints = s.slots["constraints"]

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

    # Select matching Cases
    cases = BY_TYPE.get("case", [])
    if constraints.get("white_theme"):
        white_cases = [c for c in cases if c["specs"].get("color") == "white"]
        if white_cases: cases = white_cases
    elif constraints.get("black_theme"):
        black_cases = [c for c in cases if c["specs"].get("color") == "black"]
        if black_cases: cases = black_cases

    # Select matching Storage
    min_storage = constraints.get("min_storage_gb", 1000 if budget >= 25000 else 500)
    storages = [st for st in BY_TYPE.get("storage", []) if st["specs"].get("capacity_gb", 0) >= min_storage]
    if not storages: storages = BY_TYPE.get("storage", [])

    cand_builds = []
    for cpu in cpus:
        matching_boards = [b for b in BY_TYPE["motherboard"] if cpu["part_id"] in b["specs"].get("supported_cpu_ids", [])]
        if constraints.get("wifi_required"):
            wifi_boards = [b for b in matching_boards if b["specs"].get("has_wifi")]
            if wifi_boards: matching_boards = wifi_boards
        if constraints.get("white_theme"):
            white_boards = [b for b in matching_boards if b["specs"].get("color") == "white"]
            if white_boards: matching_boards = white_boards
        if not matching_boards:
            continue

        matching_rams = [r for r in BY_TYPE["ram"] if r["specs"].get("memory_type") == cpu["specs"].get("memory_type")]
        min_ram = constraints.get("min_ram_gb", 32 if budget >= 35000 else 16)
        targeted_rams = [r for r in matching_rams if r["specs"].get("capacity_gb", 0) >= min_ram]
        if targeted_rams: matching_rams = targeted_rams
        if constraints.get("white_theme"):
            white_rams = [r for r in matching_rams if r["specs"].get("color") == "white"]
            if white_rams: matching_rams = white_rams
        if not matching_rams:
            continue

        for board in matching_boards:
            for ram in matching_rams:
                for storage in storages:
                    for case in cases:
                        for gpu in gpus:
                            # Verify PSU headroom
                            cpu_w = cpu["specs"].get("wattage_draw", 65)
                            gpu_w = gpu["specs"].get("wattage_draw", 0) if gpu else 0
                            req_w = cpu_w + gpu_w + 150
                            matching_psus = [p for p in BY_TYPE.get("psu", []) if p["specs"].get("wattage", 0) >= req_w * 1.15]
                            psu = matching_psus[0] if matching_psus else BY_TYPE.get("psu", [])[0]

                            chosen = [cpu, board, ram, storage, psu, case] + ([gpu] if gpu else [])
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

def _score_build(build: list[dict], use_case: str, constraints: dict, budget: int) -> float:
    """Calculate use-case fitness and user-preference alignment score."""
    parts = {p["type"]: p for p in build}
    cpu = parts.get("cpu", {})
    gpu = parts.get("gpu", {})
    ram = parts.get("ram", {})
    storage = parts.get("storage", {})
    case = parts.get("case", {})
    mobo = parts.get("motherboard", {})

    cpu_rank = cpu.get("rank", 1)
    gpu_rank = gpu.get("rank", 0) if gpu else 0
    ram_gb = ram.get("specs", {}).get("capacity_gb", 16)
    storage_gb = storage.get("specs", {}).get("capacity_gb", 500)

    # Base weighted score according to use-case
    if use_case == "gaming":
        score = (gpu_rank * 3.5) + (cpu_rank * 2.0) + (1.5 if ram_gb >= 32 else 1.0) + (1.0 if storage_gb >= 1000 else 0.5)
    elif use_case in ("video_editing", "streaming"):
        score = (cpu_rank * 3.5) + (2.5 if ram_gb >= 32 else 1.0) + (gpu_rank * 2.0) + (1.5 if storage_gb >= 1000 else 0.5)
    elif use_case in ("ai", "rendering"):
        cuda_bonus = 2.0 if gpu.get("brand") == "nvidia" else 0.0
        vram = gpu.get("specs", {}).get("vram_gb", 0) if gpu else 0
        score = (gpu_rank * 3.0) + cuda_bonus + (vram * 0.3) + (2.5 if ram_gb >= 32 else 1.0) + (cpu_rank * 1.5)
    else:  # office / general
        score = (cpu_rank * 2.0) + (1.5 if ram_gb >= 16 else 1.0) + (1.0 if storage_gb >= 500 else 0.5)

    # Preference bonuses
    if constraints.get("white_theme"):
        white_count = sum(1 for p in build if p.get("specs", {}).get("color") == "white")
        score += white_count * 0.5
    if constraints.get("wifi_required") and mobo.get("specs", {}).get("has_wifi"):
        score += 1.0
    if constraints.get("low_noise") and case.get("specs", {}).get("is_quiet"):
        score += 0.8
    if constraints.get("min_storage_gb") and storage_gb >= constraints["min_storage_gb"]:
        score += 0.8
    if constraints.get("min_ram_gb") and ram_gb >= constraints["min_ram_gb"]:
        score += 0.8

    return score

async def integrate(s: AgentState):
    prices = s.observations.get("price", {}).get("prices", {})
    ranges = s.observations.get("price", {}).get("ranges", {})
    for build in s.candidate_builds:
        for part in build:
            part["price"] = None if part["owned"] else prices.get(part["name"])
            part["price_low"], part["price_high"] = (None, None) if part["owned"] else ranges.get(part["name"], (None, None))
            part["spec_source"] = part.get("source")

    budget = s.slots["budget"] or 0
    use_case = s.slots.get("use_case") or "gaming"
    constraints = s.slots.get("constraints") or {}

    complete = []
    for build in s.candidate_builds:
        priced = [p for p in build if not p["owned"]]
        if priced and all(p.get("price_low") is not None and p.get("price_high") is not None for p in priced):
            low = sum(p["price_low"] for p in priced)
            high = sum(p["price_high"] for p in priced)
            mid = sum((p["price_low"] + p["price_high"]) / 2 for p in priced)
            score = _score_build(build, use_case, constraints, budget)
            complete.append((build, low, high, score, mid))

    affordable = [item for item in complete if item[4] <= budget]
    if affordable:
        max_score = max(item[3] for item in affordable)
        # Quality rule: filter only top-tier builds within 5% of max score
        top_tier = [item for item in affordable if item[3] >= max_score * 0.95]
        # Pick the best among top tier (highest score, optimal budget utilization)
        chosen, low, high, _score, mid = max(top_tier, key=lambda item: (item[3], item[4]))
        s.data_quality["budget_fit"] = "within_budget"
    elif complete:
        chosen, low, high, _score, mid = min(complete, key=lambda item: (item[4], -item[3]))
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
    return "manufacturer_specs"

async def manufacturer_specs(s: AgentState):
    parts = [part for part in s.parts if not part.get("owned")]
    records = await fetch_manufacturer_facts_for_parts(parts)
    s.observations["manufacturer_specs"] = {"records": records}
    for record in records:
        if record["status"] != "live":
            s.degraded_services.append("manufacturer_specs")
            s.errors.append(f"manufacturer_specs:{record['part_id']}:{record['status']}")
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
    unpriced = [p["name"] for p in s.parts if not p.get("owned") and p.get("price") is None]
    if not unpriced:
        s.degraded_services = [d for d in s.degraded_services if d != "price"]
    s.data_quality["missing_evidence"] = sorted({"price"} & set(s.degraded_services))
    s.data_quality["freshness_ok"] = not s.data_quality.get("stale_price")
    s.data_quality["price_reference_source"] = "Google Shopping via SerpApi"
    s.data_quality["price_reference_note"] = "Indicative market range from matched search results; not a quote."
    s.data_quality["price_reference_observed_at"] = s.observations.get("price", {}).get("as_of")
    spec_records = s.observations.get("manufacturer_specs", {}).get("records", [])
    s.data_quality["manufacturer_spec_sources"] = {
        "live_pages": sum(record["status"] == "live" for record in spec_records),
        "requested_pages": len(spec_records),
        "structured_spec_pages": sum(
            any(key not in {"name", "description", "page_title", "page_description"}
                for key in record["facts"])
            for record in spec_records
        ),
        "all_live": bool(spec_records) and all(record["status"] == "live" for record in spec_records),
        "records": spec_records,
    }
    return "package"

async def package(s: AgentState):
    s.data_quality["evidence_complete"] = not s.data_quality["missing_evidence"] and s.compatibility is not None
    return "finish"

NODES = {"classify": classify, "extract": extract, "ask_missing": ask_missing, "plan": plan, "fetch": fetch,
         "integrate": integrate, "manufacturer_specs": manufacturer_specs,
         "compatibility": compatibility, "alternatives_rag": alternatives_rag,
         "quality": quality, "package": package}

def _result(s: AgentState, status: str) -> AgentResult:
    pkg = None
    if s.parts and status != "needs_info":
        pkg = {"request_summary": {k: s.slots.get(k) for k in ("budget", "use_case", "brand", "gpu_brand", "cpu_model", "gpu_model", "constraints")},
               "parts": s.parts, "price_breakdown": {p["type"]: p["price"] for p in s.parts if p.get("price") is not None},
               "benchmark": s.observations.get("benchmark"), "compatibility": s.compatibility, "alternatives": s.alternatives,
               "rag_notes": s.evidence, "data_quality": s.data_quality, "assumptions": s.assumptions,
               "records": [record for observation in s.observations.values()
                           for record in observation.get("records", [])
                           if record.get("kind") in {"price", "spec"}],
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
