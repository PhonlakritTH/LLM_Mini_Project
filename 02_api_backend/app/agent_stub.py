"""Stand-in for module 03 (PC Build AI Agent) + 04 price/stock APIs.
Compatibility & value decisions live HERE (server), never in the web app."""
import random
from datetime import datetime, timezone
from .schemas import BuildRequest, Part

TIERS = {  # use_case -> (cpu_amd, cpu_intel, gpu_nvidia, gpu_amd)
    "gaming": [("Ryzen 5 7600", "AM5", 7500), ("Core i5-13400F", "LGA1700", 7900), ("RTX 4060", 10500), ("RX 7600", 8900)],
    "video_editing": [("Ryzen 7 7700", "AM5", 11500), ("Core i7-13700", "LGA1700", 13500), ("RTX 4060 Ti", 15500), ("RX 7700 XT", 14500)],
    "office": [("Ryzen 5 5600G", "AM4", 5500), ("Core i3-12100", "LGA1700", 4200), ("Integrated", 0), ("Integrated", 0)],
    "streaming": [("Ryzen 7 7700", "AM5", 11500), ("Core i5-13600K", "LGA1700", 11900), ("RTX 4060", 10500), ("RX 7600", 8900)],
    "ai_rendering": [("Ryzen 9 7900", "AM5", 17500), ("Core i7-13700K", "LGA1700", 14900), ("RTX 4070 Super", 25500), ("RX 7800 XT", 19500)],
}
WATTS = {"Integrated": 0, "RX 7600": 165, "RTX 4060": 115, "RTX 4060 Ti": 160, "RX 7700 XT": 245, "RTX 4070 Super": 220, "RX 7800 XT": 263}

async def fetch_prices(part_names):
    """Mock retailer call. Returns (stock map, degraded_services)."""
    degraded = ["stock_api"] if random.random() < 0.15 else []
    return {n: {"in_stock": None if degraded else True} for n in part_names}, degraded

async def recommend(req: BuildRequest) -> dict:
    cpu_amd, cpu_intel, gpu_nv, gpu_amd = TIERS[req.use_case]
    cpu = cpu_intel if req.preferred_brand == "intel" else cpu_amd
    gpu = gpu_amd if req.preferred_brand == "amd" else gpu_nv
    gpu_w = WATTS.get(gpu[0], 200)
    board = {"AM5": ("B650M", 3900), "AM4": ("B550M", 3200), "LGA1700": ("B760M", 3600)}[cpu[1]]
    src = "mock-retailer"
    parts = [Part(type="cpu", name=cpu[0], price=cpu[2], source=src),
             Part(type="motherboard", name=f"{board[0]} ({cpu[1]})", price=board[1], source=src),
             Part(type="gpu", name=gpu[0], price=gpu[1], source=src),
             Part(type="ram", name="16GB DDR5" if cpu[1] == "AM5" else "16GB DDR4", price=1800, source=src),
             Part(type="storage", name="1TB NVMe", price=2200, source=src),
             Part(type="psu", name="650W 80+ Bronze", price=1900, source=src),
             Part(type="case", name="ATX Mid Tower", price=1500, source=src)]
    owned = {p.type for p in req.existing_parts}
    for p in parts:
        if p.type in owned:
            p.price = 0
    stock, degraded = await fetch_prices([p.name for p in parts])
    for p in parts:
        p.in_stock = stock[p.name]["in_stock"]

    conflicts, fix = [], None
    for ep in req.existing_parts:  # deterministic compatibility rules
        if ep.type == "motherboard" and ep.socket and ep.socket != cpu[1]:
            conflicts.append(f"Motherboard socket {ep.socket} does not fit {cpu[0]} ({cpu[1]}).")
            fix = f"Choose a {ep.socket} CPU or replace the motherboard."
        if ep.type == "psu" and ep.wattage and ep.wattage < gpu_w * 2 + 250:
            conflicts.append(f"PSU {ep.wattage}W is below the recommended {gpu_w * 2 + 250}W.")
            fix = fix or "Upgrade to a 650W+ PSU."
    total = sum(p.price for p in parts)
    if conflicts:
        code, status, conf, summary = "avoid_combination", "incompatible", 0.9, "This combination has compatibility conflicts."
    elif total > req.budget:
        code, status, conf = "swap_component", "warning", 0.75
        summary = f"Build is {total - req.budget:,} THB over budget; swap a component."
        fix = "Downgrade the GPU one tier or reuse an existing part."
    elif degraded:
        code, status, conf, summary = "wait_for_price_drop", "warning", 0.55, "Stock could not be verified. Check again shortly."
    else:
        code, status, conf, summary = "finalize_build", "compatible", 0.88, "All parts are compatible, in budget and in stock."
    reasons = [f"Total {total:,} THB vs budget {req.budget:,} THB.",
               f"{cpu[0]} + {gpu[0]} suit {req.use_case.replace('_', ' ')}."]
    score = {"gaming": 85, "video_editing": 78, "office": 60, "streaming": 80, "ai_rendering": 88}[req.use_case]
    return dict(recommendation_code=code, compatibility_status=status, confidence=conf, summary=summary,
                reasons=reasons, conflicts=conflicts, suggested_fix=fix, parts_list=parts,
                price_breakdown={p.type: p.price for p in parts},
                benchmark_estimate={"relative_score": float(score), "est_fps_1080p": round(score * 1.4, 1)},
                sources=["mock-retailer (replace with module 04)", "mock-benchmark"],
                partial_result=bool(degraded), degraded_services=degraded,
                updated_at=datetime.now(timezone.utc).isoformat())
