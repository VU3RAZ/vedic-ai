"""Unit tests for the deterministic raman_method interpretation path.

These test the scope-extraction and interpretation-building logic in
vedic_ai.features.raman_flowchart against a synthetic flowchart fixture
(shaped like build_raman_flowchart's real output) — not the flowchart
engine's own astrological rules, which are exercised elsewhere.
"""

from __future__ import annotations

from vedic_ai.features.raman_flowchart import (
    _status3,
    build_raman_scope_interpretation,
    scope_flowchart_excerpt,
    scope_to_house,
)


class TestStatus3TieBreak:
    def test_tie_resolves_to_mixed_not_concern(self):
        assert _status3(pos=2, neg=2) == "mixed"

    def test_tie_at_higher_counts_still_mixed(self):
        assert _status3(pos=3, neg=3) == "mixed"

    def test_clean_favorable_unaffected(self):
        assert _status3(pos=2, neg=0) == "favorable"

    def test_clean_concern_unaffected(self):
        assert _status3(pos=0, neg=2) == "concern"

    def test_neg_dominant_still_concern(self):
        assert _status3(pos=1, neg=2) == "concern"

    def test_pos_dominant_still_favorable(self):
        assert _status3(pos=2, neg=1) == "favorable"

    def test_no_signals_mixed(self):
        assert _status3(pos=0, neg=0) == "mixed"


def _synthetic_features() -> dict:
    house7_step = {
        "id": "4.7",
        "title": "STEP 4.7",
        "status": "favorable",
        "findings": [
            "Sign: Libra (Movable/Air)",
            "Occupant: Venus (benefic, own)",
            "No planetary aspects on this house.",
            "House lord: Venus in H7 (own) — own house (self-reliant) placement",
            "  ✓ Venus is strong (own) — house significations well supported.",
            "—",
            "HTJH ANALYSIS:",
            "✓ Venus own-house in H7 — HTJH: harmonious, devoted partnership.",
        ],
        "table": [],
    }
    return {
        "flowchart": {
            "modules": [
                {"id": "M4", "title": "MODULE 4: House-by-House Detailed Analysis (HTJH)",
                 "steps": [house7_step]},
            ],
            "final_assessment": {
                "grade": "B",
                "grade_label": "Good",
                "score": 64,
                "verdict": "This is a good chart (Score 64/100).",
                "lagna": "Aries",
                "lagna_lord": "Mars (own) in H1",
                "moon": "exalted in Taurus H2",
                "timing_outlook": "Venus Mahadasha (ends 2030-01-01): benefic, own, placed in H7.",
                "yogas_positive": ["Gajakesari"],
                "yogas_negative": [],
                "life_areas": [
                    {"house": 7, "area": "Marriage & Partnerships",
                     "status": "favorable", "key_finding": "Venus own-house in H7."},
                ],
            },
        }
    }


class TestScopeToHouse:
    def test_legacy_scopes(self):
        assert scope_to_house("personality") == 1
        assert scope_to_house("career") == 10
        assert scope_to_house("relationships") == 7
        assert scope_to_house("health") == 6

    def test_bhava_scope(self):
        assert scope_to_house("bhava_7") == 7
        assert scope_to_house("bhava_12") == 12

    def test_unknown_scope_defaults_to_lagna(self):
        assert scope_to_house("unknown_scope") == 1

    def test_malformed_bhava_scope_defaults_to_lagna(self):
        assert scope_to_house("bhava_x") == 1


class TestScopeFlowchartExcerpt:
    def test_extracts_relevant_house_step(self):
        ex = scope_flowchart_excerpt(_synthetic_features(), "relationships")
        assert ex["house"] == 7
        assert ex["house_step"]["id"] == "4.7"
        assert ex["house_step"]["status"] == "favorable"

    def test_missing_flowchart_degrades_gracefully(self):
        ex = scope_flowchart_excerpt({}, "career")
        assert ex["house"] == 10
        assert ex["house_step"] is None
        assert ex["lagna"] is None

    def test_life_area_finding_matched_by_house(self):
        ex = scope_flowchart_excerpt(_synthetic_features(), "relationships")
        assert ex["life_area_finding"] == "Venus own-house in H7."


class TestBuildRamanScopeInterpretation:
    def test_summary_grounded_in_flowchart(self):
        result = build_raman_scope_interpretation(_synthetic_features(), "relationships", [], [])
        assert "Marriage & Partnerships" in result["summary"]
        assert "House 7" in result["summary"]
        assert "B (64/100)" in result["summary"]

    def test_details_include_htjh_finding_verbatim(self):
        result = build_raman_scope_interpretation(_synthetic_features(), "relationships", [], [])
        assert any("harmonious, devoted partnership" in d for d in result["details"])

    def test_details_include_dasha_and_yogas(self):
        result = build_raman_scope_interpretation(_synthetic_features(), "relationships", [], [])
        joined = " ".join(result["details"])
        assert "Venus Mahadasha" in joined
        assert "Gajakesari" in joined

    def test_no_flowchart_still_returns_valid_shape(self):
        result = build_raman_scope_interpretation({}, "career", [], [])
        assert isinstance(result["summary"], str)
        assert isinstance(result["details"], list)
        assert result["rule_refs"] == []
        assert result["passage_refs"] == []
