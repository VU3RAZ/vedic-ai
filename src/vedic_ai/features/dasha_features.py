"""Dasha timing features: active Mahadasha / Antardasha at a given date."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.dasha import DashaPeriod
from vedic_ai.engines.vimshottari import compute_antardasha_periods


def get_active_mahadasha(dashas: list[DashaPeriod], at_date: date) -> DashaPeriod | None:
    """Return the level-1 Mahadasha period that contains at_date, or None."""
    for period in dashas:
        if period.level == 1 and period.start_date <= at_date < period.end_date:
            return period
    return None


def get_active_antardasha(mahadasha: DashaPeriod, at_date: date) -> DashaPeriod | None:
    """Return the level-2 Antardasha within mahadasha that contains at_date, or None."""
    sub_periods = compute_antardasha_periods(mahadasha)
    for sub in sub_periods:
        if sub.start_date <= at_date < sub.end_date:
            return sub
    return None


def compute_timing_features(bundle: ChartBundle, at_time: datetime) -> dict:
    """Return active dasha timing facts for a given moment as a nested feature dict.

    Returns a dict with a single top-level key 'timing' containing nested dicts
    for 'mahadasha', 'antardasha', and 'reference_date', compatible with the
    dot-notation rule evaluator (e.g. timing.mahadasha.lord).
    """
    at_date = at_time.astimezone(timezone.utc).date()

    dashas = bundle.dashas
    maha = get_active_mahadasha(dashas, at_date)

    maha_dict: dict = {
        "lord": maha.graha.value if maha else None,
        "start": maha.start_date.isoformat() if maha else None,
        "end": maha.end_date.isoformat() if maha else None,
    }

    antar_dict: dict = {"lord": None, "start": None, "end": None}
    if maha is not None:
        antar = get_active_antardasha(maha, at_date)
        if antar:
            antar_dict = {
                "lord": antar.graha.value,
                "start": antar.start_date.isoformat(),
                "end": antar.end_date.isoformat(),
            }

    return {
        "timing": {
            "reference_date": at_date.isoformat(),
            "mahadasha": maha_dict,
            "antardasha": antar_dict,
        }
    }


def assess_dasha_lord(
    lord_name: str,
    bundle: ChartBundle,
    lordships: dict[int, dict],
    aspects: dict[str, Any],
    vargottama: dict[str, bool],
    functional_nature: dict,
) -> dict:
    """7-point Raman dasha lord strength assessment (HTJH Step 5.3).

    Returns a dict with each point assessed plus an overall score (0–1).
    """
    if not lord_name or lord_name not in bundle.d1.planets:
        return {}

    p = bundle.d1.planets[lord_name]

    # 1. Houses owned and functional role
    houses_owned: list[int] = [
        h for h, rec in lordships.items() if rec["lord"] == lord_name
    ]
    fn_planet = functional_nature.get("planets", {}).get(lord_name, {})
    role = fn_planet.get("role", "neutral")
    is_yk = fn_planet.get("is_yogakaraka", False)

    # 2. Placement house
    placement_house = p.house

    # 3. Sign strength
    sign_strength = lordships.get(
        next((h for h, r in lordships.items() if r["lord"] == lord_name), 1), {}
    ).get("lord_dignity") or "neutral"
    # Use planet's own dignity directly
    from vedic_ai.features.strength import full_dignity
    from vedic_ai.domain.enums import Graha
    try:
        g_enum = Graha(lord_name)
        sign_strength = full_dignity(g_enum, p.rasi.rasi, p.rasi.degree_in_rasi) or "neutral"
    except ValueError:
        pass

    # 4. Aspects received (by graha name)
    aspected_by: list[str] = aspects.get("aspected_by", {}).get(placement_house, [])

    # 5. Conjunctions (planets in same house)
    conjunctions: list[str] = []
    for conj in aspects.get("conjunctions", []):
        if lord_name in conj.get("planets", []):
            conjunctions = [pl for pl in conj["planets"] if pl != lord_name]
            break

    # 6. Vargottama
    is_vargottama = vargottama.get(lord_name, False)

    # 7. Retrograde
    is_retrograde = p.is_retrograde

    # ── Score (heuristic 0–1) ──────────────────────────────────────────────
    _STRENGTH_MAP = {
        "exalted": 1.0, "moolatrikona": 0.85, "own": 0.70,
        "friend": 0.45, "neutral": 0.30, "enemy": 0.15, "debilitated": 0.0,
    }
    score = _STRENGTH_MAP.get(sign_strength, 0.30)
    if is_yk:
        score = min(1.0, score + 0.20)
    elif role == "benefic":
        score = min(1.0, score + 0.10)
    elif role == "malefic":
        score = max(0.0, score - 0.10)
    if is_vargottama:
        score = min(1.0, score + 0.10)

    from vedic_ai.features.base import KENDRA_HOUSES, TRIKONA_HOUSES, DUSTHANA_HOUSES
    if placement_house in KENDRA_HOUSES or placement_house in TRIKONA_HOUSES:
        score = min(1.0, score + 0.05)
    if placement_house in DUSTHANA_HOUSES:
        score = max(0.0, score - 0.10)

    # Notes
    notes: list[str] = []
    if is_yk:
        notes.append(f"{lord_name} is Yogakaraka for this lagna")
    if sign_strength in ("exalted", "moolatrikona", "own"):
        notes.append(f"{lord_name} is strong in {p.rasi.rasi.value} ({sign_strength})")
    elif sign_strength == "debilitated":
        notes.append(f"{lord_name} is debilitated in {p.rasi.rasi.value} — dasha results weakened")
    if placement_house in DUSTHANA_HOUSES:
        notes.append(f"Placed in H{placement_house} (dusthana) — obstacles during dasha")
    if is_retrograde:
        notes.append("Retrograde — results may be delayed then intense")
    if is_vargottama:
        notes.append("Vargottama — strength doubled in D9")
    if houses_owned:
        notes.append(f"Lords H{',H'.join(str(h) for h in sorted(houses_owned))}")

    return {
        "lord": lord_name,
        "houses_owned": sorted(houses_owned),
        "functional_role": role,
        "is_yogakaraka": is_yk,
        "placement_house": placement_house,
        "sign_strength": sign_strength,
        "aspects_received": aspected_by,
        "conjunctions": conjunctions,
        "is_vargottama": is_vargottama,
        "is_retrograde": is_retrograde,
        "assessment_score": round(score, 3),
        "notes": notes,
    }
