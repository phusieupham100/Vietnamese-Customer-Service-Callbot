"""Vehicle model matcher.

This module only normalizes and matches model names. It does not route intent,
extract category fields, or update final JSON.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from .models import VehicleMatchResult, VehicleMatchStatus, VehicleMatchType, VehicleType
from .vehicle_catalog import VehicleModel, load_vehicle_catalog
from .vehicle_normalizer import compact_vehicle_text, normalize_vehicle_text


@dataclass(frozen=True, slots=True)
class _Candidate:
    model: VehicleModel
    score: float


class VehicleMatcher:
    """Match raw ASR/user text to canonical vehicle models."""

    def __init__(self, models: list[VehicleModel] | None = None) -> None:
        self.models = models if models is not None else load_vehicle_catalog()
        self._canonical_index: dict[str, VehicleModel] = {}
        self._canonical_compact_index: dict[str, VehicleModel] = {}
        self._alias_index: dict[str, VehicleModel] = {}
        self._alias_compact_index: dict[str, VehicleModel] = {}
        self._build_indexes()

    def match(self, raw_text: str) -> VehicleMatchResult:
        """Match raw text to a vehicle model.

        Exact and alias matches are confirmed. Fuzzy and ambiguous candidates
        require confirmation. Unknown values are not mapped to nearby models.
        """
        normalized = normalize_vehicle_text(raw_text)
        compact = compact_vehicle_text(raw_text)
        if not normalized:
            return self._unknown(raw_text)

        exact = self._canonical_index.get(normalized) or self._canonical_compact_index.get(compact)
        if exact is not None:
            return VehicleMatchResult(
                raw_text=raw_text,
                canonical_name=exact.canonical_name,
                vehicle_type=exact.vehicle_type,
                match_type=VehicleMatchType.EXACT,
                confidence=1.0,
                status=VehicleMatchStatus.CONFIRMED,
            )

        alias = self._alias_index.get(normalized) or self._alias_compact_index.get(compact)
        if alias is not None:
            return VehicleMatchResult(
                raw_text=raw_text,
                canonical_name=alias.canonical_name,
                vehicle_type=alias.vehicle_type,
                match_type=VehicleMatchType.ALIAS,
                confidence=0.98,
                status=VehicleMatchStatus.CONFIRMED,
            )

        candidates = self._fuzzy_candidates(normalized)
        if not candidates:
            return self._unknown(raw_text)

        top_score = candidates[0].score
        close = [candidate for candidate in candidates if top_score - candidate.score <= 0.04]
        if len(close) > 1:
            vehicle_type = (
                close[0].model.vehicle_type
                if all(candidate.model.vehicle_type == close[0].model.vehicle_type for candidate in close)
                else VehicleType.UNKNOWN
            )
            return VehicleMatchResult(
                raw_text=raw_text,
                canonical_name=None,
                vehicle_type=vehicle_type,
                match_type=VehicleMatchType.AMBIGUOUS,
                confidence=round(top_score, 3),
                status=VehicleMatchStatus.NEEDS_CONFIRMATION,
                candidates=[candidate.model.canonical_name for candidate in close],
            )

        top = candidates[0]
        return VehicleMatchResult(
            raw_text=raw_text,
            canonical_name=top.model.canonical_name,
            vehicle_type=top.model.vehicle_type,
            match_type=VehicleMatchType.FUZZY,
            confidence=round(top.score, 3),
            status=VehicleMatchStatus.NEEDS_CONFIRMATION,
            candidates=[top.model.canonical_name],
        )

    def confirm_unknown(self, raw_text: str) -> VehicleMatchResult:
        """Keep an out-of-catalog model after the customer confirms it."""
        return VehicleMatchResult(
            raw_text=raw_text,
            canonical_name=raw_text.strip(),
            vehicle_type=VehicleType.UNKNOWN,
            match_type=VehicleMatchType.UNKNOWN,
            confidence=1.0,
            status=VehicleMatchStatus.UNKNOWN_CONFIRMED,
        )

    def _build_indexes(self) -> None:
        for model in self.models:
            canonical_norm = normalize_vehicle_text(model.canonical_name)
            canonical_compact = compact_vehicle_text(model.canonical_name)
            self._canonical_index[canonical_norm] = model
            self._canonical_compact_index[canonical_compact] = model
            for alias in model.aliases:
                alias_norm = normalize_vehicle_text(alias)
                alias_compact = compact_vehicle_text(alias)
                self._alias_index[alias_norm] = model
                self._alias_compact_index[alias_compact] = model

    def _fuzzy_candidates(self, normalized_raw_text: str) -> list[_Candidate]:
        candidates: dict[str, _Candidate] = {}
        for model in self.models:
            values = [normalize_vehicle_text(model.canonical_name)]
            values.extend(normalize_vehicle_text(alias) for alias in model.aliases)
            score = max(SequenceMatcher(None, normalized_raw_text, value).ratio() for value in values)
            if score >= 0.82:
                existing = candidates.get(model.canonical_name)
                if existing is None or score > existing.score:
                    candidates[model.canonical_name] = _Candidate(model=model, score=score)
        return sorted(candidates.values(), key=lambda candidate: candidate.score, reverse=True)

    @staticmethod
    def _unknown(raw_text: str) -> VehicleMatchResult:
        return VehicleMatchResult(
            raw_text=raw_text,
            canonical_name=None,
            vehicle_type=VehicleType.UNKNOWN,
            match_type=VehicleMatchType.UNKNOWN,
            confidence=0.0,
            status=VehicleMatchStatus.UNKNOWN,
        )

