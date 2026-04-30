"""Unit tests for domain schema round-trip serialization and validation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from vedic_ai.core.exceptions import SchemaError
from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.domain.chart import (
    ChartBundle,
    build_chart_schema_version,
    deserialize_chart_bundle,
    serialize_chart_bundle,
    validate_chart_bundle,
)
from vedic_ai.domain.enums import Graha


# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

class TestSchemaVersion:
    def test_returns_string(self) -> None:
        assert isinstance(build_chart_schema_version(), str)

    def test_semver_format(self) -> None:
        parts = build_chart_schema_version().split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_version_preserved_in_bundle(self, chart_a: ChartBundle) -> None:
        payload = serialize_chart_bundle(chart_a)
        assert payload["schema_version"] == build_chart_schema_version()


# ---------------------------------------------------------------------------
# Round-trip serialization
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_chart_a_roundtrip(self, chart_a: ChartBundle) -> None:
        payload = serialize_chart_bundle(chart_a)
        restored = deserialize_chart_bundle(payload)
        assert restored.birth.name == chart_a.birth.name
        assert restored.schema_version == chart_a.schema_version
        assert set(restored.d1.planets.keys()) == set(chart_a.d1.planets.keys())
        assert set(restored.d1.houses.keys()) == set(chart_a.d1.houses.keys())

    def test_chart_b_roundtrip(self, chart_b: ChartBundle) -> None:
        payload = serialize_chart_bundle(chart_b)
        restored = deserialize_chart_bundle(payload)
        assert restored.d1.ascendant_longitude == chart_b.d1.ascendant_longitude

    def test_chart_c_roundtrip(self, chart_c: ChartBundle) -> None:
        payload = serialize_chart_bundle(chart_c)
        restored = deserialize_chart_bundle(payload)
        assert len(restored.dashas) == len(chart_c.dashas)

    def test_serialized_form_is_json_safe(self, chart_a: ChartBundle) -> None:
        import json
        payload = serialize_chart_bundle(chart_a)
        # Should not raise
        json_str = json.dumps(payload)
        reparsed = json.loads(json_str)
        restored = deserialize_chart_bundle(reparsed)
        assert restored.birth.birth_datetime.tzinfo is not None

    def test_all_nine_grahas_preserved(self, chart_a: ChartBundle) -> None:
        payload = serialize_chart_bundle(chart_a)
        restored = deserialize_chart_bundle(payload)
        grahas = {Graha(k) for k in restored.d1.planets}
        assert grahas == set(Graha)

    def test_all_twelve_houses_preserved(self, chart_a: ChartBundle) -> None:
        payload = serialize_chart_bundle(chart_a)
        restored = deserialize_chart_bundle(payload)
        assert set(restored.d1.houses.keys()) == set(range(1, 13))

    def test_planet_dignity_preserved(self, chart_a: ChartBundle) -> None:
        payload = serialize_chart_bundle(chart_a)
        restored = deserialize_chart_bundle(payload)
        assert restored.d1.planets[Graha.SUN.value].dignity is not None

    def test_dasha_dates_preserved(self, chart_a: ChartBundle) -> None:
        payload = serialize_chart_bundle(chart_a)
        restored = deserialize_chart_bundle(payload)
        original = chart_a.dashas[0]
        restored_d = restored.dashas[0]
        assert restored_d.start_date == original.start_date
        assert restored_d.end_date == original.end_date

    def test_timezone_aware_datetime_preserved(self, chart_a: ChartBundle) -> None:
        payload = serialize_chart_bundle(chart_a)
        restored = deserialize_chart_bundle(payload)
        assert restored.birth.birth_datetime.tzinfo is not None

    def test_provenance_preserved(self, chart_a: ChartBundle) -> None:
        payload = serialize_chart_bundle(chart_a)
        restored = deserialize_chart_bundle(payload)
        assert restored.provenance == chart_a.provenance


# ---------------------------------------------------------------------------
# Validation — valid payloads
# ---------------------------------------------------------------------------

class TestValidateChartBundle:
    def test_valid_chart_returns_no_errors(self, chart_a: ChartBundle) -> None:
        payload = serialize_chart_bundle(chart_a)
        errors = validate_chart_bundle(payload)
        assert errors == []

    def test_valid_chart_b_returns_no_errors(self, chart_b: ChartBundle) -> None:
        errors = validate_chart_bundle(serialize_chart_bundle(chart_b))
        assert errors == []

    def test_valid_chart_c_returns_no_errors(self, chart_c: ChartBundle) -> None:
        errors = validate_chart_bundle(serialize_chart_bundle(chart_c))
        assert errors == []


# ---------------------------------------------------------------------------
# Validation — invalid payloads
# ---------------------------------------------------------------------------

class TestInvalidPayloads:
    def test_missing_required_field_returns_errors(self, chart_a: ChartBundle) -> None:
        payload = serialize_chart_bundle(chart_a)
        del payload["birth"]
        errors = validate_chart_bundle(payload)
        assert len(errors) > 0

    def test_missing_d1_returns_errors(self, chart_a: ChartBundle) -> None:
        payload = serialize_chart_bundle(chart_a)
        del payload["d1"]
        errors = validate_chart_bundle(payload)
        assert len(errors) > 0

    def test_deserialize_invalid_raises_schema_error(self) -> None:
        with pytest.raises(SchemaError):
            deserialize_chart_bundle({"not": "a chart"})


# ---------------------------------------------------------------------------
# Validator — BirthData
# ---------------------------------------------------------------------------

class TestBirthDataValidation:
    def test_naive_datetime_rejected(self) -> None:
        with pytest.raises(Exception):
            BirthData(
                birth_datetime=datetime(1990, 4, 5, 10, 0),  # no tzinfo
                location=GeoLocation(latitude=28.6, longitude=77.2),
            )

    def test_timezone_aware_accepted(self) -> None:
        bd = BirthData(
            birth_datetime=datetime(1990, 4, 5, 10, 0, tzinfo=timezone.utc),
            location=GeoLocation(latitude=28.6, longitude=77.2),
        )
        assert bd.birth_datetime.tzinfo is not None

    def test_latitude_out_of_range(self) -> None:
        with pytest.raises(Exception):
            GeoLocation(latitude=91.0, longitude=77.2)

    def test_longitude_out_of_range(self) -> None:
        with pytest.raises(Exception):
            GeoLocation(latitude=28.6, longitude=181.0)


# ---------------------------------------------------------------------------
# Validator — PlanetPlacement
# ---------------------------------------------------------------------------

class TestPlanetPlacementValidation:
    def test_rahu_must_be_retrograde(self) -> None:
        from vedic_ai.domain.planet import NakshatraPlacement, PlanetPlacement, RasiPlacement
        from vedic_ai.domain.enums import NakshatraName, Rasi

        with pytest.raises(Exception, match="retrograde"):
            PlanetPlacement(
                graha=Graha.RAHU,
                longitude=70.0,
                is_retrograde=False,  # invalid
                rasi=RasiPlacement(rasi=Rasi.GEMINI, degree_in_rasi=10.0),
                nakshatra=NakshatraPlacement(
                    nakshatra=NakshatraName.ARDRA, pada=1,
                    nakshatra_lord=Graha.RAHU, degree_in_nakshatra=3.33,
                ),
                house=3,
            )

    def test_ketu_must_be_retrograde(self) -> None:
        from vedic_ai.domain.planet import NakshatraPlacement, PlanetPlacement, RasiPlacement
        from vedic_ai.domain.enums import NakshatraName, Rasi

        with pytest.raises(Exception, match="retrograde"):
            PlanetPlacement(
                graha=Graha.KETU,
                longitude=250.0,
                is_retrograde=False,  # invalid
                rasi=RasiPlacement(rasi=Rasi.SAGITTARIUS, degree_in_rasi=10.0),
                nakshatra=NakshatraPlacement(
                    nakshatra=NakshatraName.MULA, pada=4,
                    nakshatra_lord=Graha.KETU, degree_in_nakshatra=10.0,
                ),
                house=9,
            )

    def test_longitude_below_zero_rejected(self) -> None:
        from vedic_ai.domain.planet import NakshatraPlacement, PlanetPlacement, RasiPlacement
        from vedic_ai.domain.enums import NakshatraName, Rasi

        with pytest.raises(Exception):
            PlanetPlacement(
                graha=Graha.SUN,
                longitude=-1.0,  # invalid
                rasi=RasiPlacement(rasi=Rasi.PISCES, degree_in_rasi=29.0),
                nakshatra=NakshatraPlacement(
                    nakshatra=NakshatraName.REVATI, pada=4,
                    nakshatra_lord=Graha.MERCURY, degree_in_nakshatra=10.0,
                ),
                house=12,
            )

    def test_longitude_360_rejected(self) -> None:
        from vedic_ai.domain.planet import NakshatraPlacement, PlanetPlacement, RasiPlacement
        from vedic_ai.domain.enums import NakshatraName, Rasi

        with pytest.raises(Exception):
            PlanetPlacement(
                graha=Graha.SUN,
                longitude=360.0,  # invalid — must be lt 360
                rasi=RasiPlacement(rasi=Rasi.ARIES, degree_in_rasi=0.0),
                nakshatra=NakshatraPlacement(
                    nakshatra=NakshatraName.ASHWINI, pada=1,
                    nakshatra_lord=Graha.KETU, degree_in_nakshatra=0.0,
                ),
                house=1,
            )


# ---------------------------------------------------------------------------
# Validator — HousePlacement
# ---------------------------------------------------------------------------

class TestHousePlacementValidation:
    def test_house_zero_rejected(self) -> None:
        from vedic_ai.domain.house import HousePlacement
        from vedic_ai.domain.enums import Rasi

        with pytest.raises(Exception):
            HousePlacement(number=0, rasi=Rasi.ARIES, cusp_longitude=0.0, lord=Graha.MARS)

    def test_house_thirteen_rejected(self) -> None:
        from vedic_ai.domain.house import HousePlacement
        from vedic_ai.domain.enums import Rasi

        with pytest.raises(Exception):
            HousePlacement(number=13, rasi=Rasi.ARIES, cusp_longitude=0.0, lord=Graha.MARS)


# ---------------------------------------------------------------------------
# Nakshatra reference data
# ---------------------------------------------------------------------------

class TestNakshatraData:
    def test_all_27_nakshatras_present(self) -> None:
        from vedic_ai.domain.nakshatra import NAKSHATRA_DATA
        from vedic_ai.domain.enums import NakshatraName
        assert len(NAKSHATRA_DATA) == 27
        assert set(NAKSHATRA_DATA.keys()) == set(NakshatraName)

    def test_each_nakshatra_has_four_pada_rasis(self) -> None:
        from vedic_ai.domain.nakshatra import NAKSHATRA_DATA
        for detail in NAKSHATRA_DATA.values():
            assert len(detail.pada_rasis) == 4

    def test_indices_are_unique_and_sequential(self) -> None:
        from vedic_ai.domain.nakshatra import NAKSHATRA_DATA
        indices = sorted(d.index for d in NAKSHATRA_DATA.values())
        assert indices == list(range(1, 28))
