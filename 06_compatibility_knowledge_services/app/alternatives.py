"""Substitution graph: discontinued parts / wrong socket-chipset are hard constraints, never suggested."""
from .config import settings
from .models import AlternativeBuildOptions, AlternativeOption

# name -> (price, perf_index, socket_or_None, discontinued)
CATALOG = {
    "RTX 4070 Super": (25500, 92, None, False), "RTX 4060 Ti": (15500, 80, None, False),
    "RTX 4060": (10500, 70, None, False), "RX 7600": (8900, 66, None, False),
    "Core i7-13700K": (14900, 90, "LGA1700", False), "Core i5-13600K": (11900, 82, "LGA1700", False),
    "Ryzen 9 7900": (17500, 88, "AM5", False), "Ryzen 7 7700": (11500, 80, "AM5", False), "Ryzen 5 7600": (7500, 70, "AM5", False),
}
GRAPH = {  # part -> one-hop neighbours (cheaper/similar-tier substitutions), like an in-memory networkx graph
    "RTX 4070 Super": ["RTX 4060 Ti"], "RTX 4060 Ti": ["RTX 4060"], "RTX 4060": ["RX 7600"],
    "Core i7-13700K": ["Core i5-13600K"], "Ryzen 9 7900": ["Ryzen 7 7700"], "Ryzen 7 7700": ["Ryzen 5 7600"],
}

def find_alternatives(part_name: str, socket_lock: str | None, budget_left: int | None) -> AlternativeBuildOptions:
    if part_name not in CATALOG:
        return AlternativeBuildOptions(options=[], excluded=[f"{part_name}: not in substitution graph"])
    base_price, base_perf, base_socket, _ = CATALOG[part_name]
    options, excluded, frontier, seen, hop = [], [], [part_name], {part_name}, 0
    while frontier and hop < settings.substitution_max_hops:
        hop += 1
        nxt = []
        for node in frontier:
            for cand in GRAPH.get(node, []):
                if cand in seen: continue
                seen.add(cand); nxt.append(cand)
                price, perf, socket, discontinued = CATALOG[cand]
                if discontinued:
                    excluded.append(f"{cand}: discontinued"); continue
                if socket_lock and socket and socket != socket_lock:
                    excluded.append(f"{cand}: socket {socket} != {socket_lock}"); continue
                if budget_left is not None and price > budget_left + base_price:
                    excluded.append(f"{cand}: over budget"); continue
                price_delta, perf_delta = price - base_price, perf - base_perf
                value = round((perf_delta - price_delta / 1000) / hop, 2)   # cheaper & faster scores higher, farther hops discounted
                options.append(AlternativeOption(swap_type="gpu" if "RTX" in part_name or "RX" in part_name else "cpu",
                                                 from_part=part_name, to_part=cand, price_delta=price_delta,
                                                 performance_delta=perf_delta, value_score=value, hops=hop,
                                                 freshness=settings.knowledge_cutoff))
        frontier = nxt
    options.sort(key=lambda o: -o.value_score)
    return AlternativeBuildOptions(options=options, excluded=excluded)
