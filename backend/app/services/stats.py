"""Usage statistics tracking for resource generation."""

from collections import defaultdict
from datetime import datetime

from app.models.resources import DiscoveredResource

# In-memory stats storage
_generation_stats: dict[str, int] = defaultdict(int)
_generation_history: list[dict] = []


def track_generation(resources: list[DiscoveredResource]) -> None:
    """Track which resource types were generated.

    Args:
        resources: List of resources that were generated.
    """
    for resource in resources:
        _generation_stats[resource.type.value] += 1

    _generation_history.append({
        "timestamp": datetime.now().isoformat(),
        "total_resources": len(resources),
        "types": dict(defaultdict(int, {
            r.type.value: sum(1 for res in resources if res.type == r.type)
            for r in resources
        })),
    })

    # Keep only last 100 entries
    if len(_generation_history) > 100:
        _generation_history.pop(0)


def get_stats() -> dict:
    """Get current generation statistics.

    Returns:
        Dictionary with generation counts by resource type and history.
    """
    # Sort by count descending
    sorted_stats = sorted(
        _generation_stats.items(), key=lambda x: x[1], reverse=True
    )

    return {
        "by_resource_type": dict(sorted_stats),
        "total_generated": sum(_generation_stats.values()),
        "total_jobs": len(_generation_history),
        "recent_jobs": _generation_history[-10:],
    }
