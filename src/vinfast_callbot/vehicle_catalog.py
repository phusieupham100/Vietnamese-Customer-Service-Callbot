"""Vehicle catalog loader.

The catalog is stored in `resources/vehicle_models.yaml`. To keep this stage
dependency-light, the loader supports the simple YAML subset used by that file
instead of requiring PyYAML.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import VehicleType


@dataclass(frozen=True, slots=True)
class VehicleModel:
    """One canonical vehicle model entry."""

    canonical_name: str
    vehicle_type: VehicleType
    aliases: tuple[str, ...]


def default_catalog_path() -> Path:
    """Return the default resource path for the vehicle catalog."""
    return Path(__file__).resolve().parents[2] / "resources" / "vehicle_models.yaml"


def load_vehicle_catalog(path: str | Path | None = None) -> list[VehicleModel]:
    """Load the vehicle catalog from the repository YAML resource."""
    catalog_path = Path(path) if path is not None else default_catalog_path()
    if not catalog_path.exists():
        raise FileNotFoundError(f"Vehicle catalog not found: {catalog_path}")
    return _parse_vehicle_catalog_yaml(catalog_path.read_text(encoding="utf-8"))


def generate_hotwords(models: list[VehicleModel]) -> list[str]:
    """Generate ASR hotwords from canonical names and aliases."""
    seen: set[str] = set()
    hotwords: list[str] = []
    for model in models:
        for value in (model.canonical_name, *model.aliases):
            key = value.strip().casefold()
            if key and key not in seen:
                seen.add(key)
                hotwords.append(value)
    return hotwords


def _parse_vehicle_catalog_yaml(text: str) -> list[VehicleModel]:
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    in_aliases = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "models:":
            continue

        if stripped.startswith("- canonical_name:"):
            if current is not None:
                entries.append(current)
            current = {
                "canonical_name": _yaml_scalar(stripped.split(":", 1)[1]),
                "aliases": [],
            }
            in_aliases = False
            continue

        if current is None:
            continue

        if stripped.startswith("vehicle_type:"):
            current["vehicle_type"] = _yaml_scalar(stripped.split(":", 1)[1])
            in_aliases = False
            continue

        if stripped.startswith("aliases:"):
            current.setdefault("aliases", [])
            in_aliases = True
            continue

        if in_aliases and stripped.startswith("- "):
            aliases = current.setdefault("aliases", [])
            assert isinstance(aliases, list)
            aliases.append(_yaml_scalar(stripped[2:]))

    if current is not None:
        entries.append(current)

    models: list[VehicleModel] = []
    for entry in entries:
        canonical_name = str(entry["canonical_name"])
        vehicle_type = VehicleType(str(entry["vehicle_type"]))
        aliases = tuple(str(alias) for alias in entry.get("aliases", []))
        models.append(
            VehicleModel(
                canonical_name=canonical_name,
                vehicle_type=vehicle_type,
                aliases=aliases,
            )
        )
    return models


def _yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value

