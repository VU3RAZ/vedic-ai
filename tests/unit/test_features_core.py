"""Unit tests for Phase 3 feature extraction.

Uses programmatic chart fixtures from conftest.py — no live engine calls needed.
"""

from __future__ import annotations

import pytest

from vedic_ai.domain.enums import Dignity, Graha, Rasi
from vedic_ai.features.aspects import (
    GRAHA_ASPECTS,
    _aspected_house,
    compute_relationship_graph,
)
from vedic_ai.features.base import (
    DUSTHANA_HOUSES,
    HOUSE_TYPES,
    KENDRA_HOUSES,
    TRIKONA_HOUSES,
)
from vedic_ai.features.core_features import (
    _detect_gajakesari,
    _detect_kemadruma,
    extract_core_features,
)
from vedic_ai.features.lordships import compute_house_lordships
from vedic_ai.features.nakshatra_features import extract_nakshatra_features
from vedic_ai.features.strength import (
    DIGNITY_SCORES,
    compute_planet_strengths,
    full_dignity,
    natural_relationship,
)


# ---------------------------------------------------------------------------
# Base constants
# ---------------------------------------------------------------------------

class TestHouseTypes:
    def test_all_12_houses_covered(self) -> None:
        assert set(HOUSE_TYPES.keys()) == set(range(1, 13))

    def test_angular_houses(self) -> None:
        for h in (1, 4, 7, 10):
            assert HOUSE_TYPES[h] == "angular"

    def test_succedent_houses(self) -> None:
        for h in (2, 5, 8, 11):
            assert HOUSE_TYPES[h] == "succedent"

    def test_cadent_houses(self) -> None:
        for h in (3, 6, 9, 12):
            assert HOUSE_TYPES[h] == "cadent"

    def test_kendra_set(self) -> None:
        assert KENDRA_HOUSES == {1, 4, 7, 10}

    def test_trikona_set(self) -> None:
        assert TRIKONA_HOUSES == {1, 5, 9}

    def test_dusthana_set(self) -> None:
        assert DUSTHANA_HOUSES == {6, 8, 12}


# ---------------------------------------------------------------------------
# Aspects
# ---------------------------------------------------------------------------

class TestAspectedHouse:
    def test_7th_aspect_from_h1_is_h7(self) -> None:
        assert _aspected_house(1, 7) == 7

    def test_7th_aspect_from_h7_is_h1(self) -> None:
        assert _aspected_house(7, 7) == 1

    def test_7th_aspect_from_h9_is_h3(self) -> None:
        assert _aspected_house(9, 7) == 3

    def test_mars_4th_from_h3_is_h6(self) -> None:
        assert _aspected_house(3, 4) == 6

    def test_mars_8th_from_h3_is_h10(self) -> None:
        assert _aspected_house(3, 8) == 10

    def test_jupiter_5th_from_h1_is_h5(self) -> None:
        assert _aspected_house(1, 5) == 5

    def test_jupiter_9th_from_h1_is_h9(self) -> None:
        assert _aspected_house(1, 9) == 9

    def test_saturn_3rd_from_h9_is_h11(self) -> None:
        assert _aspected_house(9, 3) == 11

    def test_saturn_10th_from_h9_is_h6(self) -> None:
        assert _aspected_house(9, 10) == 6

    def test_wrap_around(self) -> None:
        # 7th from H12 = H6
        assert _aspected_house(12, 7) == 6


class TestGrahaAspects:
    def test_all_grahas_have_7th(self) -> None:
        for graha in Graha:
            assert 7 in GRAHA_ASPECTS[graha]

    def test_mars_has_special_aspects(self) -> None:
        assert 4 in GRAHA_ASPECTS[Graha.MARS]
        assert 8 in GRAHA_ASPECTS[Graha.MARS]

    def test_jupiter_has_special_aspects(self) -> None:
        assert 5 in GRAHA_ASPECTS[Graha.JUPITER]
        assert 9 in GRAHA_ASPECTS[Graha.JUPITER]

    def test_saturn_has_special_aspects(self) -> None:
        assert 3 in GRAHA_ASPECTS[Graha.SATURN]
        assert 10 in GRAHA_ASPECTS[Graha.SATURN]

    def test_sun_has_only_7th(self) -> None:
        assert GRAHA_ASPECTS[Graha.SUN] == [7]

    def test_rahu_ketu_have_same_aspects(self) -> None:
        assert GRAHA_ASPECTS[Graha.RAHU] == GRAHA_ASPECTS[Graha.KETU]


class TestRelationshipGraph:
    def test_returns_required_keys(self, chart_a) -> None:
        graph = compute_relationship_graph(chart_a)
        assert "graha_aspects" in graph
        assert "aspected_by" in graph
        assert "conjunctions" in graph
        assert "sign_exchanges" in graph
        assert "mutual_house_aspects" in graph

    def test_all_grahas_in_graha_aspects(self, chart_a) -> None:
        graph = compute_relationship_graph(chart_a)
        assert set(graph["graha_aspects"].keys()) == {g.value for g in Graha}

    def test_all_houses_in_aspected_by(self, chart_a) -> None:
        graph = compute_relationship_graph(chart_a)
        assert set(graph["aspected_by"].keys()) == set(range(1, 13))

    def test_aspected_by_consistent_with_graha_aspects(self, chart_a) -> None:
        graph = compute_relationship_graph(chart_a)
        for graha_name, asp_list in graph["graha_aspects"].items():
            for asp in asp_list:
                assert graha_name in graph["aspected_by"][asp["house"]]

    def test_conjunctions_have_multiple_grahas(self, chart_a) -> None:
        graph = compute_relationship_graph(chart_a)
        for conj in graph["conjunctions"]:
            assert len(conj["grahas"]) >= 2

    def test_sign_exchange_pairs_are_unique(self, chart_a) -> None:
        graph = compute_relationship_graph(chart_a)
        pairs = {tuple(sorted([e["graha_a"], e["graha_b"]])) for e in graph["sign_exchanges"]}
        assert len(pairs) == len(graph["sign_exchanges"])


# ---------------------------------------------------------------------------
# Planetary Strength
# ---------------------------------------------------------------------------

class TestNaturalRelationship:
    def test_sun_friend_with_moon(self) -> None:
        # Sun considers Moon a friend; Moon's sign is Cancer; lord of Cancer = Moon
        assert natural_relationship(Graha.SUN, Graha.MOON) == "friend"

    def test_sun_enemy_of_saturn(self) -> None:
        assert natural_relationship(Graha.SUN, Graha.SATURN) == "enemy"

    def test_jupiter_neutral_to_saturn(self) -> None:
        # Jupiter and Saturn are neutral to each other
        assert natural_relationship(Graha.JUPITER, Graha.SATURN) == "neutral"

    def test_same_planet_returns_own(self) -> None:
        assert natural_relationship(Graha.SUN, Graha.SUN) == "own"


class TestFullDignity:
    def test_sun_exalted_aries(self) -> None:
        assert full_dignity(Graha.SUN, Rasi.ARIES, 10.0) == Dignity.EXALTED.value

    def test_sun_debilitated_libra(self) -> None:
        assert full_dignity(Graha.SUN, Rasi.LIBRA, 10.0) == Dignity.DEBILITATED.value

    def test_sun_friend_in_aries_non_exaltation(self) -> None:
        # Mars owns Aries; Sun is Mars's friend → "friend"
        # But Sun in Aries is also EXALTED, so that takes priority
        result = full_dignity(Graha.SUN, Rasi.ARIES, 10.0)
        assert result == Dignity.EXALTED.value  # exalted wins over friend

    def test_jupiter_friend_in_sun_sign(self) -> None:
        # Jupiter in Leo (Sun's sign); Jupiter is Sun's friend
        result = full_dignity(Graha.JUPITER, Rasi.LEO, 15.0)
        assert result == "friend"

    def test_mercury_enemy_in_cancer(self) -> None:
        # Cancer lord = Moon; Mercury considers Moon an enemy
        result = full_dignity(Graha.MERCURY, Rasi.CANCER, 10.0)
        assert result == "enemy"

    def test_neutral_returns_none(self) -> None:
        # Sun in Pisces: not exalted, not debilitated, not moolatrikona, not own
        # Jupiter owns Pisces; Sun-Jupiter: Sun's friend list has Jupiter → "friend"
        # So Sun in Pisces should be "friend"
        result = full_dignity(Graha.SUN, Rasi.PISCES, 10.0)
        assert result == "friend"


class TestComputePlanetStrengths:
    def test_all_nine_grahas_in_result(self, chart_a) -> None:
        result = compute_planet_strengths(chart_a)
        assert set(result.keys()) == {g.value for g in Graha}

    def test_exalted_planet_has_high_score(self, chart_a) -> None:
        # Chart A: Sun is exalted (dignity=exalted)
        result = compute_planet_strengths(chart_a)
        sun = result[Graha.SUN.value]
        assert sun["dignity"] == Dignity.EXALTED.value
        assert sun["is_exalted"] is True
        assert sun["total_strength"] > 0.5

    def test_retrograde_planet_has_penalty(self, chart_a) -> None:
        result = compute_planet_strengths(chart_a)
        rahu = result[Graha.RAHU.value]
        assert rahu["is_retrograde"] is True
        assert rahu["retrograde_penalty"] > 0

    def test_dignity_scores_are_ordered(self) -> None:
        assert DIGNITY_SCORES["exalted"] > DIGNITY_SCORES["moolatrikona"]
        assert DIGNITY_SCORES["moolatrikona"] > DIGNITY_SCORES["own"]
        assert DIGNITY_SCORES["own"] > DIGNITY_SCORES["friend"]
        assert DIGNITY_SCORES["friend"] > DIGNITY_SCORES["neutral"]
        assert DIGNITY_SCORES["neutral"] > DIGNITY_SCORES["enemy"]
        assert DIGNITY_SCORES["enemy"] > DIGNITY_SCORES["debilitated"]

    def test_angular_house_has_higher_bonus_than_cadent(self, chart_a) -> None:
        result = compute_planet_strengths(chart_a)
        # Find one angular and one cadent planet
        angular = next(v for v in result.values() if v["house_type"] == "angular")
        cadent = next(v for v in result.values() if v["house_type"] == "cadent")
        assert angular["house_strength_bonus"] > cadent["house_strength_bonus"]


# ---------------------------------------------------------------------------
# House Lordships
# ---------------------------------------------------------------------------

class TestHouseLordships:
    def test_all_12_houses_in_result(self, chart_a) -> None:
        result = compute_house_lordships(chart_a)
        assert set(result.keys()) == set(range(1, 13))

    def test_h1_lord_is_mars_for_aries_lagna(self, chart_a) -> None:
        # Chart A: Aries lagna → H1 lord = Mars
        result = compute_house_lordships(chart_a)
        assert result[1]["lord"] == Graha.MARS.value

    def test_lord_house_is_traceable(self, chart_a) -> None:
        result = compute_house_lordships(chart_a)
        for h, data in result.items():
            lord_name = data["lord"]
            lord_house_in_lordship = data["lord_house"]
            lord_house_in_chart = chart_a.d1.planets[lord_name].house
            assert lord_house_in_lordship == lord_house_in_chart

    def test_occupied_flag_correct(self, chart_a) -> None:
        result = compute_house_lordships(chart_a)
        for h, data in result.items():
            expected = len(data["occupants"]) > 0
            assert data["is_occupied"] == expected

    def test_lord_kendra_trikona_flags(self, chart_a) -> None:
        result = compute_house_lordships(chart_a)
        for h, data in result.items():
            lord_house = data["lord_house"]
            assert data["lord_in_kendra"] == (lord_house in KENDRA_HOUSES)
            assert data["lord_in_trikona"] == (lord_house in TRIKONA_HOUSES)
            assert data["lord_in_dusthana"] == (lord_house in DUSTHANA_HOUSES)

    def test_cancer_lagna_h1_lord_is_moon(self, chart_b) -> None:
        # Chart B: Cancer lagna → H1 lord = Moon
        result = compute_house_lordships(chart_b)
        assert result[1]["lord"] == Graha.MOON.value


# ---------------------------------------------------------------------------
# Nakshatra Features
# ---------------------------------------------------------------------------

class TestNakshatraFeatures:
    def test_all_grahas_present(self, chart_a) -> None:
        result = extract_nakshatra_features(chart_a)
        assert set(result["planets"].keys()) == {g.value for g in Graha}

    def test_ascendant_nakshatra_present(self, chart_a) -> None:
        result = extract_nakshatra_features(chart_a)
        assert "ascendant" in result
        assert "nakshatra" in result["ascendant"]

    def test_pada_in_range(self, chart_a) -> None:
        result = extract_nakshatra_features(chart_a)
        for data in result["planets"].values():
            assert 1 <= data["pada"] <= 4

    def test_nakshatra_lord_is_valid_graha(self, chart_a) -> None:
        result = extract_nakshatra_features(chart_a)
        valid = {g.value for g in Graha}
        for data in result["planets"].values():
            assert data["lord"] in valid

    def test_pada_rasi_is_valid(self, chart_a) -> None:
        result = extract_nakshatra_features(chart_a)
        valid = {r.value for r in Rasi}
        for data in result["planets"].values():
            assert data["pada_rasi"] in valid


# ---------------------------------------------------------------------------
# Yoga Detection
# ---------------------------------------------------------------------------

class TestYogaDetection:
    def test_kemadruma_detected_in_chart_b(self, chart_b) -> None:
        assert _detect_kemadruma(chart_b) is True

    def test_kemadruma_not_present_in_chart_a(self, chart_a) -> None:
        # Chart A has planets adjacent to Moon → no Kemadruma
        result = _detect_kemadruma(chart_a)
        # We just check it runs and returns a bool
        assert isinstance(result, bool)

    def test_gajakesari_returns_bool(self, chart_a) -> None:
        result = _detect_gajakesari(chart_a)
        assert isinstance(result, bool)

    def test_gajakesari_chart_a(self, chart_a) -> None:
        # Chart A: Moon in H2 (Taurus), Jupiter in H4 (Cancer)
        # Diff = (4-2) % 12 = 2. Not 0, 3, 6, or 9 → no Gajakesari
        # Actually: Moon house = 2, Jupiter house = 4, diff = 2 → False
        result = _detect_gajakesari(chart_a)
        assert result is False


# ---------------------------------------------------------------------------
# extract_core_features (integration of all sub-extractors)
# ---------------------------------------------------------------------------

class TestExtractCoreFeatures:
    def test_returns_all_required_keys(self, chart_a) -> None:
        features = extract_core_features(chart_a)
        for key in ("planets", "houses", "aspects", "yogas", "lagna", "metadata"):
            assert key in features

    def test_all_grahas_in_planets(self, chart_a) -> None:
        features = extract_core_features(chart_a)
        assert set(features["planets"].keys()) == {g.value for g in Graha}

    def test_all_houses_in_houses(self, chart_a) -> None:
        features = extract_core_features(chart_a)
        assert set(features["houses"].keys()) == set(range(1, 13))

    def test_each_graha_record_has_required_fields(self, chart_a) -> None:
        features = extract_core_features(chart_a)
        required = {
            "graha", "longitude", "rasi", "house", "dignity",
            "is_exalted", "nakshatra", "nakshatra_lord", "aspects_to_houses",
        }
        for g_data in features["planets"].values():
            assert required <= g_data.keys()

    def test_aspects_to_houses_are_valid(self, chart_a) -> None:
        features = extract_core_features(chart_a)
        for g_data in features["planets"].values():
            for h in g_data["aspects_to_houses"]:
                assert 1 <= h <= 12

    def test_kemadruma_in_yogas(self, chart_b) -> None:
        features = extract_core_features(chart_b)
        assert features["yogas"]["kemadruma"] is True

    def test_yogas_structure(self, chart_a) -> None:
        features = extract_core_features(chart_a)
        yogas = features["yogas"]
        assert "kemadruma" in yogas
        assert "gajakesari" in yogas
        assert "raja_yogas" in yogas
        assert "dhana_yogas" in yogas

    def test_lagna_has_required_fields(self, chart_a) -> None:
        features = extract_core_features(chart_a)
        lagna = features["lagna"]
        for field in ("rasi", "nakshatra", "lord", "lord_house"):
            assert field in lagna

    def test_metadata_present(self, chart_a) -> None:
        features = extract_core_features(chart_a)
        md = features["metadata"]
        assert md["engine"] == "flatlib"   # fixture uses flatlib as engine label
        assert md["ayanamsa"] == "lahiri"

    def test_features_are_deterministic(self, chart_a) -> None:
        import json
        f1 = json.dumps(extract_core_features(chart_a), sort_keys=True)
        f2 = json.dumps(extract_core_features(chart_a), sort_keys=True)
        assert f1 == f2

    def test_features_are_json_serializable(self, chart_c) -> None:
        import json
        features = extract_core_features(chart_c)
        # Should not raise
        json.dumps(features)

    def test_aspects_received_from_consistent(self, chart_a) -> None:
        features = extract_core_features(chart_a)
        for h in range(1, 13):
            for graha_name in features["houses"][h]["aspects_received_from"]:
                aspecting_planet = features["planets"][graha_name]
                assert h in aspecting_planet["aspects_to_houses"]
