"""Usage statistics tracking for resource generation.

Persists stats to disk so they survive container restarts.
"""

from collections import defaultdict
from datetime import datetime

from app.models.resources import DiscoveredResource
from app.services.persistence import load, save

STATS_FILE = "generation_stats.json"


def _load_stats() -> tuple[dict[str, int], list[dict]]:
    """Load stats from disk."""
    data = load(STATS_FILE, {"by_resource_type": {}, "history": []})
    return (
        defaultdict(int, data.get("by_resource_type", {})),
        data.get("history", []),
    )


# Load on module init
_generation_stats, _generation_history = _load_stats()


def _save_stats() -> None:
    """Save current stats to disk."""
    save(STATS_FILE, {
        "by_resource_type": dict(_generation_stats),
        "history": _generation_history,
    })


def track_generation(resources: list[DiscoveredResource]) -> None:
    """Track which resource types were generated and persist."""
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

    _save_stats()


def get_stats() -> dict:
    """Get current generation statistics."""
    sorted_stats = sorted(
        _generation_stats.items(), key=lambda x: x[1], reverse=True
    )

    return {
        "by_resource_type": dict(sorted_stats),
        "total_generated": sum(_generation_stats.values()),
        "total_jobs": len(_generation_history),
        "recent_jobs": _generation_history[-10:],
    }
