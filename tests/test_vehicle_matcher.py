"""Tests for vehicle model recognition."""

from __future__ import annotations

import pytest

from vinfast_callbot.models import VehicleMatchStatus, VehicleMatchType
from vinfast_callbot.vehicle_catalog import generate_hotwords, load_vehicle_catalog
from vinfast_callbot.vehicle_matcher import VehicleMatcher


@pytest.fixture(scope="module")
def matcher() -> VehicleMatcher:
    return VehicleMatcher()


@pytest.fixture(scope="module")
def catalog():
    return load_vehicle_catalog()


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("VF8", "VF 8"),
        ("ép tám", "VF 8"),
        ("Feliz", "Feliz"),
        ("Feliz hai", "FELIZ II"),
        ("Green Bus tám mét", "Green Bus 8M"),
    ],
)
def test_required_aliases_match_confirmed(matcher: VehicleMatcher, raw_text: str, expected: str) -> None:
    result = matcher.match(raw_text)

    assert result.canonical_name == expected
    assert result.status == VehicleMatchStatus.CONFIRMED
    assert result.match_type in {VehicleMatchType.EXACT, VehicleMatchType.ALIAS}


def test_klara_s_does_not_map_to_klara_s2(matcher: VehicleMatcher) -> None:
    result = matcher.match("Klara S")

    assert result.canonical_name == "Klara S"
    assert result.canonical_name != "KLARA S2"
    assert result.status == VehicleMatchStatus.CONFIRMED


def test_unknown_model_does_not_map_to_nearby_catalog_model(matcher: VehicleMatcher) -> None:
    result = matcher.match("Zumo")

    assert result.canonical_name is None
    assert result.status == VehicleMatchStatus.UNKNOWN
    assert result.match_type == VehicleMatchType.UNKNOWN


def test_confirmed_unknown_model_keeps_raw_value(matcher: VehicleMatcher) -> None:
    result = matcher.confirm_unknown("Zumo")

    assert result.canonical_name == "Zumo"
    assert result.status == VehicleMatchStatus.UNKNOWN_CONFIRMED
    assert result.match_type == VehicleMatchType.UNKNOWN


def test_all_canonical_models_exact_match(catalog) -> None:
    matcher = VehicleMatcher(catalog)

    for model in catalog:
        result = matcher.match(model.canonical_name)
        assert result.canonical_name == model.canonical_name
        assert result.vehicle_type == model.vehicle_type
        assert result.status == VehicleMatchStatus.CONFIRMED
        assert result.match_type == VehicleMatchType.EXACT


def test_car_models_return_vehicle_type_car(catalog) -> None:
    matcher = VehicleMatcher(catalog)

    for model in catalog:
        if model.vehicle_type.value == "car":
            assert matcher.match(model.canonical_name).to_dict()["vehicle_type"] == "car"


def test_motorbike_models_return_vehicle_type_motorbike(catalog) -> None:
    matcher = VehicleMatcher(catalog)

    for model in catalog:
        if model.vehicle_type.value == "motorbike":
            assert matcher.match(model.canonical_name).to_dict()["vehicle_type"] == "motorbike"


def test_fuzzy_result_requires_confirmation(matcher: VehicleMatcher) -> None:
    result = matcher.match("VF 88")

    assert result.match_type in {VehicleMatchType.FUZZY, VehicleMatchType.AMBIGUOUS}
    assert result.status == VehicleMatchStatus.NEEDS_CONFIRMATION
    assert result.canonical_name != "VF 8" or result.status == VehicleMatchStatus.NEEDS_CONFIRMATION


def test_ambiguous_result_requires_confirmation(matcher: VehicleMatcher) -> None:
    result = matcher.match("Green Bus")

    assert result.match_type == VehicleMatchType.AMBIGUOUS
    assert result.status == VehicleMatchStatus.NEEDS_CONFIRMATION
    assert {"Green Bus 6M", "Green Bus 8M", "Green Bus 10M"}.intersection(result.candidates)


def test_hotwords_generated_from_canonical_names_and_aliases(catalog) -> None:
    hotwords = generate_hotwords(catalog)

    assert "VF 8" in hotwords
    assert "ép tám" in hotwords
    assert "Green Bus 8M" in hotwords
    assert "green bus tám mét" in hotwords

