"""Tested, deterministic safety rules. Module 06 will replace this behind the same contract."""
def check_compatibility(parts: list[dict], constraints: dict) -> dict:
    by = {p["type"]: p for p in parts}
    conflicts, warnings, unknown = [], [], []
    cpu, mb = by.get("cpu"), by.get("motherboard")
    if cpu and mb:
        if not cpu.get("socket") or not mb.get("socket"):
            unknown.append(f"Socket of {cpu['name'] if not cpu.get('socket') else mb['name']} is unknown.")
        elif cpu["socket"] != mb["socket"]:
            conflicts.append(f"CPU socket {cpu['socket']} does not match motherboard socket {mb['socket']}.")
    cpu_w = 125 if cpu else 0
    gpu_w = (by.get("gpu") or {}).get("watts") or 0
    need = cpu_w + gpu_w + 150
    psu = by.get("psu", {})
    if psu.get("wattage"):
        if psu["wattage"] < need: conflicts.append(f"PSU {psu['wattage']}W is below the required {need}W.")
        elif psu["wattage"] < need * 1.2: warnings.append(f"PSU {psu['wattage']}W leaves under 20% headroom over {need}W.")
    if constraints.get("max_wattage") and need > constraints["max_wattage"]:
        warnings.append(f"Estimated draw {need}W exceeds your {constraints['max_wattage']}W limit.")
    if constraints.get("case_form_factor") == "ITX" and mb and mb.get("form_factor", "mATX") != "ITX":
        conflicts.append("A mATX/ATX motherboard does not fit an ITX case.")
    status = "incompatible" if conflicts else "warning" if warnings else "unknown" if unknown else "compatible"
    return {"status": status, "conflicts": conflicts, "warnings": warnings, "unknown": unknown, "estimated_watts": need}
