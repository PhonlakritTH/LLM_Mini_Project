def performance_index(passmark=None, cinebench=None, threedmark=None, fps=None) -> float:
    """Blend whatever scores are available onto a common 0-100 index."""
    parts = []
    if passmark: parts.append(min(passmark / 300, 100))
    if cinebench: parts.append(min(cinebench / 30, 100))
    if threedmark: parts.append(min(threedmark / 250, 100))
    if fps: parts.append(min(fps / 1.6, 100))
    return round(sum(parts) / len(parts), 1) if parts else 0.0

def quality_score(coverage: float, freshness_ok: bool, completeness: float) -> float:
    return round(0.5 * coverage + 0.3 * (1.0 if freshness_ok else 0.0) + 0.2 * completeness, 3)
