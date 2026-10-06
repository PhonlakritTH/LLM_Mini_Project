"""Fail-closed compatibility checks over sourced component facts."""


def check_compatibility(parts: list[dict], constraints: dict) -> dict:
    by = {part["type"]: part for part in parts}
    conflicts, warnings, unknown = [], [], []
    cpu, board = by.get("cpu", {}), by.get("motherboard", {})
    ram, gpu, psu, case = (by.get(kind, {}) for kind in ("ram", "gpu", "psu", "case"))

    cpu_specs = cpu.get("specs", {})
    board_specs = board.get("specs", {})
    ram_specs = ram.get("specs", {})
    gpu_specs = gpu.get("specs", {})
    psu_specs = psu.get("specs", {})
    case_specs = case.get("specs", {})

    if cpu and board:
        cpu_socket, board_socket = cpu_specs.get("socket"), board_specs.get("socket")
        if cpu_socket and board_socket and cpu_socket != board_socket:
            conflicts.append(f"CPU socket {cpu_socket} does not match motherboard socket {board_socket}.")
        if not cpu_socket or not board_socket or not cpu.get("spec_source") or not board.get("spec_source"):
            unknown.append("CPU or motherboard socket lacks sourced specification data.")
        supported = board_specs.get("supported_cpu_ids")
        if not supported or board_specs.get("cpu_support_list_status") != "verified" or not cpu.get("part_id"):
            unknown.append("Motherboard CPU support list is not verified.")
        elif cpu["part_id"] not in supported:
            conflicts.append(f"Motherboard CPU support list does not include {cpu['name']}.")
        if board_specs.get("bios_version_status") != "verified":
            unknown.append("Motherboard BIOS version support has not been verified.")

    memory_types = [cpu_specs.get("memory_type"), board_specs.get("memory_type"), ram_specs.get("memory_type")]
    if len(memory_types) < 3 or any(not value for value in memory_types) or not all(
            part.get("spec_source") for part in (cpu, board, ram) if part):
        unknown.append("CPU, motherboard, or memory generation lacks sourced specification data.")
    elif len(set(memory_types)) != 1:
        conflicts.append(f"Memory generation mismatch: {', '.join(memory_types)}.")
    if board and board_specs.get("ram_qvl_status") != "verified":
        unknown.append("Exact memory-kit QVL validation has not been verified.")

    required_watts = (cpu_specs.get("wattage_draw") or 0) + (gpu_specs.get("wattage_draw") or 0) + 150
    if cpu and cpu_specs.get("wattage_draw") is None:
        unknown.append(f"Power draw of {cpu['name']} is unknown.")
    if gpu and gpu_specs.get("wattage_draw") is None:
        unknown.append(f"Power draw of {gpu['name']} is unknown.")
    psu_watts = psu_specs.get("wattage") or psu_specs.get("wattage_draw")
    if psu:
        if psu_watts is None or not psu.get("spec_source"):
            unknown.append(f"Wattage of {psu['name']} lacks sourced specification data.")
        elif psu_watts < required_watts:
            conflicts.append(f"PSU {psu_watts}W is below the conservative {required_watts}W system target.")
        elif psu_watts < required_watts * 1.2:
            warnings.append(f"PSU {psu_watts}W leaves less than 20% headroom over {required_watts}W.")

    required_connectors = gpu_specs.get("power_connectors", [])
    available_connectors = psu_specs.get("power_connectors", [])
    if gpu and required_connectors:
        if not available_connectors:
            unknown.append("PSU connector specification is unavailable.")
        elif any(connector not in available_connectors for connector in required_connectors):
            conflicts.append("PSU power connectors do not satisfy the graphics card requirement.")

    if gpu and case:
        gpu_length, case_limit = gpu_specs.get("length_mm"), case_specs.get("max_gpu_length_mm")
        if gpu_length is None or case_limit is None:
            unknown.append("Graphics card or case clearance is unknown.")
        elif gpu_length > case_limit:
            conflicts.append(f"Graphics card length {gpu_length}mm exceeds case clearance {case_limit}mm.")

    if board and case:
        board_form = board_specs.get("form_factor")
        supported_forms = case_specs.get("form_factor_support")
        if not board_form or not supported_forms:
            unknown.append("Motherboard/case form-factor support is unknown.")
        elif board_form not in supported_forms:
            conflicts.append(f"Case does not support {board_form} motherboards.")

    if constraints.get("max_wattage") and required_watts > constraints["max_wattage"]:
        warnings.append(f"Estimated system target {required_watts}W exceeds the requested {constraints['max_wattage']}W limit.")

    status = "incompatible" if conflicts else "warning" if warnings or unknown else "compatible"
    return {"status": status, "conflicts": conflicts, "warnings": warnings,
            "unknown": unknown, "estimated_watts": required_watts}
