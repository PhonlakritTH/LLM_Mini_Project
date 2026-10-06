"""Compatibility rules that require sourced specifications for a pass result."""
from .config import settings
from .models import CompatibilityAssessment


def assess(parts: list[dict], constraints: dict) -> CompatibilityAssessment:
    by = {part.get("category", part.get("type")): part for part in parts}
    cpu, board, ram = by.get("cpu"), by.get("motherboard"), by.get("ram")
    gpu, psu, case = by.get("gpu"), by.get("psu"), by.get("case")
    specs = {kind: (part or {}).get("specs", {}) for kind, part in {
        "cpu": cpu, "motherboard": board, "ram": ram, "gpu": gpu, "psu": psu, "case": case,
    }.items()}
    conflicts: list[str] = []
    unknown: list[str] = []

    for required in ("cpu", "motherboard", "ram", "psu", "case"):
        if required not in by:
            unknown.append(f"required_component_missing:{required}")

    def sourced(*selected: dict | None) -> bool:
        return all(part and part.get("spec_sources") for part in selected)

    if cpu and board:
        cpu_socket, board_socket = specs["cpu"].get("socket"), specs["motherboard"].get("socket")
        if cpu_socket and board_socket and cpu_socket != board_socket:
            conflicts.append(f"socket_mismatch:{cpu_socket}!={board_socket}")
        if not cpu_socket or not board_socket or not sourced(cpu, board):
            unknown.append("CPU/motherboard socket data is missing or has no source.")
        supported = specs["motherboard"].get("supported_cpu_ids")
        if (not supported or specs["motherboard"].get("cpu_support_list_status") != "verified"
                or not cpu.get("knowledge_id")):
            unknown.append("Motherboard CPU support-list evidence is missing.")
        elif cpu["knowledge_id"] not in supported:
            conflicts.append("cpu_not_in_motherboard_support_list")
        if specs["motherboard"].get("bios_version_status") != "verified":
            unknown.append("Motherboard BIOS version support has not been verified.")

    memory_types = (specs["cpu"].get("memory_type"), specs["motherboard"].get("memory_type"),
                    specs["ram"].get("memory_type"))
    if not all(memory_types) or not sourced(cpu, board, ram):
        unknown.append("CPU, motherboard, or RAM generation lacks sourced data.")
    elif len(set(memory_types)) != 1:
        conflicts.append(f"memory_type_mismatch:{'/'.join(memory_types)}")
    if board and specs["motherboard"].get("ram_qvl_status") != "verified":
        unknown.append("Exact memory-kit QVL validation has not been verified.")

    cpu_watts, gpu_watts = specs["cpu"].get("wattage_draw"), specs["gpu"].get("wattage_draw")
    psu_watts = specs["psu"].get("wattage")
    system_target = (cpu_watts or 0) + (gpu_watts or 0) + 150
    if cpu and (cpu_watts is None or not sourced(cpu)):
        unknown.append("cpu_power_requirement_unknown")
    if gpu and (gpu_watts is None or not sourced(gpu)):
        unknown.append("gpu_power_requirement_unknown")
    if psu:
        if psu_watts is None or not sourced(psu):
            unknown.append("psu_capacity_unknown")
        elif psu_watts < system_target:
            conflicts.append(f"psu_insufficient:{psu_watts}W<{system_target}W")
        elif psu_watts < system_target * 1.2:
            unknown.append("psu_headroom_below_20_percent")

    required_connectors = specs["gpu"].get("power_connectors", [])
    available_connectors = specs["psu"].get("power_connectors", [])
    if gpu and required_connectors:
        if not available_connectors or not sourced(gpu, psu):
            unknown.append("gpu_psu_connector_evidence_missing")
        elif any(connector not in available_connectors for connector in required_connectors):
            conflicts.append("gpu_psu_connector_mismatch")

    if gpu and case:
        gpu_length = specs["gpu"].get("length_mm")
        case_limit = specs["case"].get("max_gpu_length_mm")
        if gpu_length is None or case_limit is None or not sourced(gpu, case):
            unknown.append("case_gpu_clearance_unknown")
        elif gpu_length > case_limit:
            conflicts.append(f"gpu_exceeds_case_clearance:{gpu_length}>{case_limit}")

    if board and case:
        board_form = specs["motherboard"].get("form_factor")
        supported_forms = specs["case"].get("form_factor_support")
        if not board_form or not supported_forms or not sourced(board, case):
            unknown.append("case_motherboard_form_factor_unknown")
        elif board_form not in supported_forms:
            conflicts.append(f"case_does_not_support:{board_form}")

    if constraints.get("max_wattage") and system_target > constraints["max_wattage"]:
        unknown.append(f"requested_power_limit_exceeded:{system_target}>{constraints['max_wattage']}")

    status = "INCOMPATIBLE" if conflicts else "NEEDS_REVIEW" if unknown else "COMPATIBLE"
    score = 0.0 if conflicts else 0.5 if unknown else 1.0
    uncertainty = 0.0 if conflicts else 0.5 if unknown else 0.0
    reasons = conflicts + unknown
    if not reasons:
        reasons.append("all_sourced_checks_passed")
    return CompatibilityAssessment(status=status, score=score, uncertainty=uncertainty,
                                   reason_codes=reasons, hard_override=bool(conflicts),
                                   model_version=settings.model_version,
                                   feature_schema_version=settings.feature_schema_version)
