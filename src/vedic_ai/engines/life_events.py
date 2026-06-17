"""Life Events Timeline Engine — classical Jyotiṣa timing.

Timing of life events is derived from explicit śāstric techniques, not generic
house overlap. For every Vimśottarī Mahādaśā/Antardaśā window each event is
scored against:

  1. BPHS Ch.46-47 — Daśā-phala: a bhāva fructifies in the daśā/antardaśā of
       (a) its lord, (b) its occupants, (c) planets aspecting it (graha-dṛṣṭi),
       (d) its natural kāraka.
  2. Jaimini Sūtra 1.1.10-18 — Chara Kārakas: Darākāraka→marriage,
       Putrakāraka→children, Amātyakāraka→career, Gnātikāraka→disease,
       Mātṛkāraka→property/education/vehicle, Ātmakāraka→spiritual life.
  3. BPHS Ch.7 — Ṣoḍaśavarga: the relevant divisional chart must confirm
       (D9 marriage, D7 children, D10 career, D4 property, D16 vehicle,
        D24 education, D20 spirituality).
  4. Jātaka Pārijāta — Indu (Dhana) Lagna for wealth timing.
  5. Phaladīpikā Ch.26 — Gochara of Guru & Śani from the natal Moon as the
       triggering transit at the antardaśā midpoint.

Reference legend used in factor strings:
  BPHS = Bṛhat Parāśara Horā Śāstra · JS = Jaimini Sūtras
  PD = Phaladīpikā · JP = Jātaka Pārijāta · SAR = Sārāvalī
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vedic_ai.engines.base import AstrologyEngine

from vedic_ai.domain.chart import ChartBundle, DivisionalChart
from vedic_ai.domain.dasha import DashaPeriod
from vedic_ai.domain.enums import Graha, Rasi
from vedic_ai.engines.vimshottari import (
    compute_antardasha_periods,
    compute_vimshottari_dashas,
)
from vedic_ai.features.strength import full_dignity


# ── Reference strings (śāstric citations) ───────────────────────────────────────

REF_DASHA_LORD   = "BPHS 47 (bhāva-lord daśā)"
REF_DASHA_OCC    = "BPHS 47 (occupant daśā)"
REF_DASHA_ASPECT = "BPHS 47 + graha-dṛṣṭi (aspecting-planet daśā)"
REF_KARAKA       = "BPHS (naisargika kāraka)"
REF_JAIMINI      = "JS 1.1.10-18 (Chara Kāraka)"
REF_VARGA        = "BPHS 7 (Ṣoḍaśavarga)"
REF_INDU         = "JP (Indu/Dhana Lagna)"
REF_GOCHARA      = "PD 26 (Gochara of Guru/Śani from Moon)"
REF_AGE          = "PD/SAR (classical age-window)"


# ── Event category ─────────────────────────────────────────────────────────────

class EventCategory(str, Enum):
    EDUCATION    = "Education"
    CAREER       = "Career"
    MARRIAGE     = "Marriage"
    CHILDREN     = "Children"
    PROPERTY     = "Property"
    VEHICLE      = "Vehicle"
    HEALTH       = "Health"
    WEALTH       = "Wealth"
    SPIRITUALITY = "Spirituality"
    TRAVEL       = "Foreign Travel"


# ── Jaimini Chara Kāraka roles (8-kāraka scheme incl. Rāhu) ─────────────────────

# Highest longitude-in-sign → AK, descending. Rāhu uses (30 − degree).
_KARAKA_ROLES: list[str] = ["AK", "AmK", "BK", "MK", "PiK", "PK", "GK", "DK"]
_KARAKA_PLANETS: list[Graha] = [
    Graha.SUN, Graha.MOON, Graha.MARS, Graha.MERCURY,
    Graha.JUPITER, Graha.VENUS, Graha.SATURN, Graha.RAHU,
]

# Jātaka Pārijāta kalā values for Indu Lagna
_INDU_KALA: dict[Graha, int] = {
    Graha.SUN: 30, Graha.MOON: 16, Graha.MARS: 6, Graha.MERCURY: 8,
    Graha.JUPITER: 10, Graha.VENUS: 12, Graha.SATURN: 1,
}

# Graha-dṛṣṭi special aspects (besides the universal 7th)
_SPECIAL_ASPECTS: dict[Graha, set[int]] = {
    Graha.MARS:    {4, 8},
    Graha.JUPITER: {5, 9},
    Graha.SATURN:  {3, 10},
    Graha.RAHU:    {5, 9},
    Graha.KETU:    {5, 9},
}

_GOOD_DIGNITIES   = {"exalted", "moolatrikona", "own", "friend"}
_BAD_DIGNITIES    = {"debilitated", "enemy"}
_NATURAL_MALEFICS = {Graha.SATURN, Graha.MARS, Graha.RAHU, Graha.KETU}
_NATURAL_BENEFICS = {Graha.JUPITER, Graha.VENUS, Graha.MERCURY, Graha.MOON}

# Classical Gochara of Jupiter/Saturn from natal Moon
_JUP_FAVORABLE_GOCHARA = {2, 5, 7, 9, 11}
_JUP_CHALLENGE_GOCHARA = {1, 3, 4, 6, 8, 10, 12}
_SAT_FAVORABLE_GOCHARA = {3, 6, 11}
_SAT_CHALLENGE_GOCHARA = {1, 2, 4, 5, 7, 8, 9, 10, 12}


# ── Event domain specification ────────────────────────────────────────────────

@dataclass
class EventDomain:
    key: str
    label: str
    category: EventCategory
    emoji: str
    relevant_houses: list[int]            # D1 bhāvas governing the event
    karakas: list[Graha]                  # naisargika (natural) kārakas
    chara_karaka: str | None              # Jaimini role (e.g. "DK")
    expected_age_min: float
    expected_age_max: float
    varga: str | None = None              # confirming divisional chart
    varga_houses: list[int] = field(default_factory=list)
    favorable_transit_houses: list[int] = field(default_factory=list)
    is_malefic_event: bool = False
    can_repeat: bool = False
    use_indu_lagna: bool = False
    method_note: str = ""                 # one-line śāstric methodology


_DOMAINS: list[EventDomain] = [
    EventDomain(
        key="education_higher", label="Higher Education / Degree",
        category=EventCategory.EDUCATION, emoji="🎓",
        relevant_houses=[4, 5, 9], karakas=[Graha.JUPITER, Graha.MERCURY],
        chara_karaka="MK", expected_age_min=16, expected_age_max=30,
        varga="D24", varga_houses=[5, 9],
        favorable_transit_houses=[5, 9, 11],
        method_note="4th=vidyā, 9th=higher knowledge; Budha/Guru kārakas; D24 (Siddhāṁśa) confirms (BPHS 7).",
    ),
    EventDomain(
        key="education_primary", label="Primary / Secondary Education",
        category=EventCategory.EDUCATION, emoji="📚",
        relevant_houses=[2, 4, 5], karakas=[Graha.MERCURY, Graha.JUPITER],
        chara_karaka="MK", expected_age_min=5, expected_age_max=18,
        varga="D24", varga_houses=[4, 5],
        favorable_transit_houses=[2, 5, 9],
        method_note="4th bhāva of schooling; D24 Siddhāṁśa governs learning (BPHS 7).",
    ),
    EventDomain(
        key="career_start", label="Career / First Employment",
        category=EventCategory.CAREER, emoji="💼",
        relevant_houses=[6, 10, 11], karakas=[Graha.SUN, Graha.SATURN, Graha.MERCURY],
        chara_karaka="AmK", expected_age_min=18, expected_age_max=35,
        varga="D10", varga_houses=[1, 10, 11],
        favorable_transit_houses=[10, 11, 2],
        method_note="10th=karma, 6th=service; Amātyakāraka (JS) = profession; D10 Daśāṁśa confirms.",
    ),
    EventDomain(
        key="career_peak", label="Career Peak / Major Promotion",
        category=EventCategory.CAREER, emoji="⭐",
        relevant_houses=[9, 10, 11], karakas=[Graha.SUN, Graha.JUPITER, Graha.SATURN],
        chara_karaka="AmK", expected_age_min=30, expected_age_max=65,
        varga="D10", varga_houses=[10, 1, 9],
        favorable_transit_houses=[10, 11, 9],
        method_note="10th-lord + Amātyakāraka daśā with strong D10 lagna (BPHS 7, JS).",
    ),
    EventDomain(
        key="marriage", label="Marriage / Partnership",
        category=EventCategory.MARRIAGE, emoji="💍",
        relevant_houses=[2, 7, 11], karakas=[Graha.VENUS, Graha.JUPITER],
        chara_karaka="DK", expected_age_min=18, expected_age_max=50,
        varga="D9", varga_houses=[7, 2, 11],
        favorable_transit_houses=[2, 7, 11],
        method_note="7th-lord/Darākāraka (JS) daśā; Śukra=Kalatra-kāraka; D9 Navāṁśa confirms (BPHS 7).",
    ),
    EventDomain(
        key="first_child", label="First Child / Parenthood",
        category=EventCategory.CHILDREN, emoji="👶",
        relevant_houses=[5, 9], karakas=[Graha.JUPITER],
        chara_karaka="PK", expected_age_min=22, expected_age_max=55,
        varga="D7", varga_houses=[5, 9],
        favorable_transit_houses=[5, 9, 1],
        method_note="5th-lord/Putrakāraka (JS) daśā; Guru=Santāna-kāraka; D7 Saptāṁśa confirms.",
    ),
    EventDomain(
        key="property_house", label="Property / House Acquisition",
        category=EventCategory.PROPERTY, emoji="🏠",
        relevant_houses=[4, 11, 12], karakas=[Graha.MARS, Graha.MOON, Graha.SATURN],
        chara_karaka="MK", expected_age_min=25, expected_age_max=70,
        varga="D4", varga_houses=[4, 12],
        favorable_transit_houses=[4, 11, 2], can_repeat=True,
        method_note="4th-lord/Mātṛkāraka daśā; Maṅgala=Bhūmi-kāraka; D4 Chaturthāṁśa confirms.",
    ),
    EventDomain(
        key="vehicle", label="Vehicle Acquisition",
        category=EventCategory.VEHICLE, emoji="🚗",
        relevant_houses=[4, 11], karakas=[Graha.VENUS, Graha.MARS],
        chara_karaka="MK", expected_age_min=18, expected_age_max=70,
        varga="D16", varga_houses=[4, 1],
        favorable_transit_houses=[4, 11, 2], can_repeat=True,
        method_note="4th=vāhana-sukha; Śukra=vāhana-kāraka; D16 Ṣoḍaśāṁśa confirms (BPHS 7).",
    ),
    EventDomain(
        key="financial_success", label="Financial Wealth / Prosperity",
        category=EventCategory.WEALTH, emoji="💰",
        relevant_houses=[2, 9, 11], karakas=[Graha.JUPITER, Graha.VENUS, Graha.MERCURY],
        chara_karaka=None, expected_age_min=28, expected_age_max=75,
        favorable_transit_houses=[2, 5, 9, 11], can_repeat=True, use_indu_lagna=True,
        method_note="2nd/11th Dhana-yoga lords + Indu Lagna lord daśā (JP).",
    ),
    EventDomain(
        key="health_challenge", label="Health Challenge / Illness",
        category=EventCategory.HEALTH, emoji="🏥",
        relevant_houses=[6, 8, 12], karakas=[Graha.SATURN, Graha.MARS, Graha.RAHU],
        chara_karaka="GK", expected_age_min=1, expected_age_max=90,
        is_malefic_event=True, can_repeat=True,
        method_note="6/8/12 Trika lords + Gnātikāraka (JS) daśā; Śani longevity; Sāḍe-Sātī Gochara (PD).",
    ),
    EventDomain(
        key="foreign_travel", label="Foreign Travel / Relocation",
        category=EventCategory.TRAVEL, emoji="✈️",
        relevant_houses=[9, 12, 3], karakas=[Graha.RAHU, Graha.SATURN],
        chara_karaka=None, expected_age_min=18, expected_age_max=80,
        favorable_transit_houses=[9, 12, 3], can_repeat=True,
        method_note="12th=foreign land, 9th=long journeys; Rāhu/Śani daśā (BPHS).",
    ),
    EventDomain(
        key="spiritual_awakening", label="Spiritual Growth / Renunciation",
        category=EventCategory.SPIRITUALITY, emoji="🕉️",
        relevant_houses=[9, 12, 5], karakas=[Graha.JUPITER, Graha.KETU, Graha.SATURN],
        chara_karaka="AK", expected_age_min=35, expected_age_max=120,
        varga="D20", varga_houses=[1, 9, 12],
        favorable_transit_houses=[9, 12, 5],
        method_note="12th=mokṣa, Ketu=mokṣa-kāraka, Ātmakāraka (JS); D20 Viṁśāṁśa of upāsanā confirms.",
    ),
]


DOMAIN_BY_KEY: dict[str, EventDomain] = {d.key: d for d in _DOMAINS}


def list_domains() -> list[dict]:
    """Return the event-domain catalog for UI selectors."""
    return [
        {
            "key": d.key, "label": d.label, "category": d.category.value,
            "emoji": d.emoji, "age_min": d.expected_age_min, "age_max": d.expected_age_max,
        }
        for d in _DOMAINS
    ]


# ── Output model ──────────────────────────────────────────────────────────────

@dataclass
class LifeEventPrediction:
    domain_key: str
    label: str
    category: str
    emoji: str
    start_date: date
    end_date: date
    age_start: float
    age_end: float
    score: int
    confidence: str
    mahadasha_lord: str
    antardasha_lord: str
    method_note: str
    supporting_factors: list[str]
    divisional_signal: str | None = None
    transit_signal: str | None = None


# ── Jaimini Chara Kāraka computation (JS 1.1.10-18) ─────────────────────────────

def compute_chara_karakas(bundle: ChartBundle) -> dict[Graha, str]:
    """Return {graha: chara-kāraka role} using the 8-kāraka Jaimini scheme.

    Planets are ranked by longitude-within-sign (descending). Rāhu's degree is
    reckoned as (30 − degree) since it is retrograde.
    """
    degs: dict[Graha, float] = {}
    for g in _KARAKA_PLANETS:
        d = bundle.d1.planets[g.value].rasi.degree_in_rasi
        if g == Graha.RAHU:
            d = 30.0 - d
        degs[g] = d
    ordered = sorted(degs, key=lambda g: -degs[g])
    return {graha: _KARAKA_ROLES[i] for i, graha in enumerate(ordered)}


def _role_to_graha(chara: dict[Graha, str], role: str) -> Graha | None:
    for g, r in chara.items():
        if r == role:
            return g
    return None


# ── Indu (Dhana) Lagna — Jātaka Pārijāta ────────────────────────────────────────

def compute_indu_lagna(bundle: ChartBundle) -> tuple[int, Graha] | None:
    """Return (indu_house_number, indu_lagna_lord) per Jātaka Pārijāta.

    Sum the kalās of the 9th-lord from Lagna and the 9th-lord from the Moon;
    take the sum mod 12 (0→12) and count that many signs from the Moon-sign.
    """
    try:
        ninth_from_lagna_lord = bundle.d1.houses[9].lord
        moon_house = bundle.d1.planets[Graha.MOON.value].house
        ninth_from_moon_house = ((moon_house - 1 + 8) % 12) + 1
        ninth_from_moon_lord = bundle.d1.houses[ninth_from_moon_house].lord

        total = _INDU_KALA.get(ninth_from_lagna_lord, 0) + _INDU_KALA.get(ninth_from_moon_lord, 0)
        rem = total % 12 or 12
        indu_house = ((moon_house - 1 + (rem - 1)) % 12) + 1
        return indu_house, bundle.d1.houses[indu_house].lord
    except (KeyError, Exception):
        return None


# ── Graha-dṛṣṭi: which planets aspect a given D1 bhāva ──────────────────────────

def _planets_aspecting_house(bundle: ChartBundle, house_num: int) -> list[Graha]:
    aspectors: list[Graha] = []
    for g in Graha:
        ph = bundle.d1.planets[g.value].house
        dist = ((house_num - ph) % 12) + 1
        aspects = {7} | _SPECIAL_ASPECTS.get(g, set())
        if dist in aspects:
            aspectors.append(g)
    return aspectors


# ── Bhāva significator set (BPHS 47) ────────────────────────────────────────────

def _build_significators(
    bundle: ChartBundle,
    domain: EventDomain,
    chara: dict[Graha, str],
    indu: tuple[int, Graha] | None,
) -> dict[Graha, list[tuple[int, str]]]:
    """Map each contributing graha → list of (weight, reference) entries.

    Weights follow the BPHS Ch.47 fructification hierarchy:
        bhāva lord 4 · chara-kāraka 3 · naisargika kāraka 3
        · occupant 2 · aspecting planet 2 · Indu-lord 3
    """
    sig: dict[Graha, list[tuple[int, str]]] = {}

    def add(g: Graha, weight: int, ref: str):
        sig.setdefault(g, []).append((weight, ref))

    for h in domain.relevant_houses:
        house = bundle.d1.houses.get(h)
        if not house:
            continue
        add(house.lord, 4, f"lord of H{h} [{REF_DASHA_LORD}]")
        for occ in house.occupants:
            add(occ, 2, f"occupies H{h} [{REF_DASHA_OCC}]")
        for asp in _planets_aspecting_house(bundle, h):
            add(asp, 2, f"aspects H{h} [{REF_DASHA_ASPECT}]")

    for k in domain.karakas:
        add(k, 3, f"naisargika kāraka [{REF_KARAKA}]")

    if domain.chara_karaka:
        ck = _role_to_graha(chara, domain.chara_karaka)
        if ck:
            add(ck, 3, f"{domain.chara_karaka} Chara-kāraka [{REF_JAIMINI}]")

    if domain.use_indu_lagna and indu:
        indu_house, indu_lord = indu
        add(indu_lord, 3, f"Indu-Lagna lord [{REF_INDU}]")
        for occ in bundle.d1.houses[indu_house].occupants:
            add(occ, 2, f"in Indu-Lagna [{REF_INDU}]")

    return sig


# ── Scoring helpers ────────────────────────────────────────────────────────────

def _planet_dignity(bundle: ChartBundle, g: Graha) -> str:
    p = bundle.d1.planets[g.value]
    return full_dignity(g, p.rasi.rasi, p.rasi.degree_in_rasi)


def _confidence(score: int) -> str:
    if score >= 18: return "Very High"
    if score >= 13: return "High"
    if score >= 8:  return "Moderate"
    if score >= 4:  return "Low"
    return "Very Low"


def _midpoint(antar: DashaPeriod) -> date:
    return antar.start_date + timedelta(days=(antar.end_date - antar.start_date).days // 2)


def _from_moon(planet_house: int, moon_house: int) -> int:
    return ((planet_house - moon_house) % 12) + 1


# ── Daśā-activation scoring (BPHS 46-47 + Jaimini + Indu) ────────────────────────

def _score_dasha(
    bundle: ChartBundle,
    domain: EventDomain,
    maha: DashaPeriod,
    antar: DashaPeriod,
    birth_date: date,
    sig: dict[Graha, list[tuple[int, str]]],
    include_age_prior: bool = True,
) -> tuple[int, list[str]]:
    score = 0
    factors: list[str] = []

    for lord, label, mult in [(maha.graha, "MD", 1.0), (antar.graha, "AD", 0.5)]:
        entries = sig.get(lord, [])
        for weight, ref in entries:
            pts = max(1, round(weight * mult))
            score += pts
            factors.append(f"{lord.value} ({label}) {ref} +{pts}")
        # dignity modifier for an activating lord
        if entries:
            dig = _planet_dignity(bundle, lord)
            if dig in _GOOD_DIGNITIES:
                score += 1
                factors.append(f"{lord.value} ({label}) in {dig} — strengthens result [BPHS 7]")
            elif dig in _BAD_DIGNITIES and not domain.is_malefic_event:
                score -= 1
                factors.append(f"{lord.value} ({label}) in {dig} — weakens result")

    # Classical age-window prior (PD/Sārāvalī) — skipped in rectification fit mode,
    # where the event date is supplied by the user and must not be re-biased by age.
    if include_age_prior:
        age_s = (antar.start_date - birth_date).days / 365.25
        age_e = (antar.end_date - birth_date).days / 365.25
        mid = (age_s + age_e) / 2
        if domain.expected_age_min <= mid <= domain.expected_age_max:
            score += 3
            factors.append(f"age {age_s:.0f}–{age_e:.0f} within classical window {domain.expected_age_min:.0f}–{domain.expected_age_max:.0f} [{REF_AGE}]")
        elif age_s <= domain.expected_age_max and age_e >= domain.expected_age_min:
            score += 1
            factors.append(f"age {age_s:.0f}–{age_e:.0f} partially overlaps classical window [{REF_AGE}]")
        else:
            score -= 8
            factors.append(f"age {age_s:.0f}–{age_e:.0f} outside classical window {domain.expected_age_min:.0f}–{domain.expected_age_max:.0f}")

    # Malefic-event reinforcement (Trika activation)
    if domain.is_malefic_event:
        if maha.graha in _NATURAL_MALEFICS:
            score += 2
            factors.append(f"{maha.graha.value} (MD) natural malefic activates Trika [BPHS]")
        if antar.graha in _NATURAL_MALEFICS:
            score += 1
            factors.append(f"{antar.graha.value} (AD) natural malefic [BPHS]")

    return score, factors


# ── Varga confirmation (BPHS 7 Ṣoḍaśavarga) ─────────────────────────────────────

def _score_varga(
    domain: EventDomain,
    varga: DivisionalChart,
    maha_lord: Graha,
    antar_lord: Graha,
) -> tuple[int, list[str]]:
    score = 0
    factors: list[str] = []
    vcode = domain.varga or "?"
    rel = set(domain.varga_houses)

    for lord, label in [(maha_lord, "MD"), (antar_lord, "AD")]:
        if lord.value not in varga.planets:
            continue
        p = varga.planets[lord.value]
        dig = full_dignity(lord, p.rasi.rasi, p.rasi.degree_in_rasi)
        for h_num, h in varga.houses.items():
            if h_num in rel and h.lord == lord:
                score += 2
                factors.append(f"{lord.value} ({label}) rules H{h_num} in {vcode} [{REF_VARGA}]")
        if p.house in rel:
            score += 2
            factors.append(f"{lord.value} ({label}) in H{p.house} of {vcode} [{REF_VARGA}]")
        if dig in _GOOD_DIGNITIES:
            score += 1
            factors.append(f"{lord.value} {dig} in {vcode} [{REF_VARGA}]")
        elif dig in _BAD_DIGNITIES:
            score -= 1
            factors.append(f"{lord.value} {dig} in {vcode} — weak confirmation")

    for k in domain.karakas:
        if k.value not in varga.planets:
            continue
        kp = varga.planets[k.value]
        kd = full_dignity(k, kp.rasi.rasi, kp.rasi.degree_in_rasi)
        if kd in _GOOD_DIGNITIES:
            score += 1
            factors.append(f"kāraka {k.value} {kd} in {vcode} [{REF_VARGA}]")
        if kp.house in rel:
            score += 1
            factors.append(f"kāraka {k.value} occupies H{kp.house} of {vcode} [{REF_VARGA}]")

    return score, factors


# ── Gochara confirmation (PD 26: Guru/Śani from Moon) ───────────────────────────

def _score_gochara(domain: EventDomain, jup_from_moon: int, sat_from_moon: int) -> tuple[int, str | None]:
    score = 0
    sig: list[str] = []
    fav = set(domain.favorable_transit_houses)

    if domain.is_malefic_event:
        if jup_from_moon in _JUP_CHALLENGE_GOCHARA:
            score += 1
            sig.append(f"Guru H{jup_from_moon} from Moon (aśubha gochara)")
        if sat_from_moon in _SAT_CHALLENGE_GOCHARA:
            score += 2
            sig.append(f"Śani H{sat_from_moon} from Moon (aśubha gochara)")
        if sat_from_moon in {12, 1, 2}:
            score += 2
            sig.append(f"Śani H{sat_from_moon} from Moon — Sāḍe-Sātī active")
    else:
        if jup_from_moon in _JUP_FAVORABLE_GOCHARA and jup_from_moon in fav:
            score += 3
            sig.append(f"Guru śubha-gochara H{jup_from_moon} from Moon — triggers event")
        elif jup_from_moon in _JUP_FAVORABLE_GOCHARA:
            score += 1
            sig.append(f"Guru favorable H{jup_from_moon} from Moon")
        elif jup_from_moon in _JUP_CHALLENGE_GOCHARA:
            score -= 1
            sig.append(f"Guru aśubha-gochara H{jup_from_moon} from Moon")

        if sat_from_moon in _SAT_FAVORABLE_GOCHARA and sat_from_moon in fav:
            score += 2
            sig.append(f"Śani śubha-gochara H{sat_from_moon} from Moon")
        elif sat_from_moon in _SAT_FAVORABLE_GOCHARA:
            score += 1
            sig.append(f"Śani favorable H{sat_from_moon} from Moon")
        elif sat_from_moon in {1, 2, 12}:
            score -= 2
            sig.append(f"Śani H{sat_from_moon} from Moon — Sāḍe-Sātī suppresses event")

    summary = f"[{REF_GOCHARA}] " + " | ".join(sig) if sig else None
    return score, summary


# ── Single-date scoring (used by birth-time rectification) ───────────────────────

def _active_maha_antar(
    mahadashas: list[DashaPeriod], target: date
) -> tuple[DashaPeriod | None, DashaPeriod | None]:
    """Return the (Mahādaśā, Antardaśā) periods active on `target`."""
    for maha in mahadashas:
        if maha.start_date <= target < maha.end_date:
            for antar in compute_antardasha_periods(maha):
                if antar.start_date <= target < antar.end_date:
                    return maha, antar
            return maha, None
    return None, None


def _transit_from_moon(
    bundle: ChartBundle, engine: "AstrologyEngine", on_date: date
) -> tuple[int, int]:
    """Return (Jupiter, Saturn) house counted from natal Moon on `on_date`."""
    moon_house = bundle.d1.planets[Graha.MOON.value].house
    tz = bundle.birth.birth_datetime.tzinfo or timezone.utc
    snap = engine.compute_transits(
        bundle.birth, datetime(on_date.year, on_date.month, on_date.day, 12, 0, tzinfo=tz)
    )
    return (
        _from_moon(snap.planets[Graha.JUPITER.value].house, moon_house),
        _from_moon(snap.planets[Graha.SATURN.value].house, moon_house),
    )


def score_event_fit(
    bundle: ChartBundle,
    domain_key: str,
    target_date: date,
    chara: dict[Graha, str] | None = None,
    indu: tuple[int, Graha] | None = None,
    engine: "AstrologyEngine | None" = None,
) -> dict | None:
    """Score how strongly the chart activates `domain_key` on `target_date`.

    This is the inverse of the timeline: instead of asking *when* an event is
    likely, it measures the daśā/varga/gochara activation strength for a known
    date. The classical age-window prior is intentionally disabled — the date is
    a fact supplied by the user. Used by the birth-time rectification engine.

    Returns a dict with the activation score and the active daśā lords, or None
    if the domain is unknown or the date is out of range.
    """
    domain = DOMAIN_BY_KEY.get(domain_key)
    if domain is None:
        return None

    birth_date = bundle.birth.birth_datetime.date()
    if target_date <= birth_date:
        return None

    moon_lon = bundle.d1.planets[Graha.MOON.value].longitude
    mahadashas = compute_vimshottari_dashas(moon_lon, birth_date, span_years=120)
    maha, antar = _active_maha_antar(mahadashas, target_date)
    if maha is None or antar is None:
        return None

    if chara is None:
        chara = compute_chara_karakas(bundle)
    if indu is None:
        indu = compute_indu_lagna(bundle)

    sig = _build_significators(bundle, domain, chara, indu)
    d_score, d_factors = _score_dasha(
        bundle, domain, maha, antar, birth_date, sig, include_age_prior=False
    )

    v_score, v_factors = 0, []
    if domain.varga and domain.varga in bundle.vargas:
        v_score, v_factors = _score_varga(
            domain, bundle.vargas[domain.varga], maha.graha, antar.graha
        )

    t_score, t_summary = 0, None
    if engine is not None:
        try:
            jm, sm = _transit_from_moon(bundle, engine, target_date)
            t_score, t_summary = _score_gochara(domain, jm, sm)
        except Exception:
            pass

    factors = d_factors + v_factors + ([t_summary] if t_summary else [])
    return {
        "domain_key":      domain_key,
        "label":           domain.label,
        "emoji":           domain.emoji,
        "mahadasha_lord":  maha.graha.value,
        "antardasha_lord": antar.graha.value,
        "score":           d_score + v_score + t_score,
        "dasha_score":     d_score,
        "varga_score":     v_score,
        "transit_score":   t_score,
        "factors":         factors,
    }


# ── Main computation ────────────────────────────────────────────────────────────

def compute_life_events(
    bundle: ChartBundle,
    engine: "AstrologyEngine | None" = None,
) -> list[LifeEventPrediction]:
    """Compute the 120-year life-events timeline using classical timing rules.

    Combines Vimśottarī daśā-phala (BPHS 47), Jaimini Chara Kārakas (JS),
    Ṣoḍaśavarga confirmation (BPHS 7), Indu Lagna (JP) and Guru/Śani Gochara
    (PD 26). Pass `engine` to enable transit (Gochara) confirmation.
    """
    birth_date = bundle.birth.birth_datetime.date()
    moon_lon = bundle.d1.planets[Graha.MOON.value].longitude
    moon_house = bundle.d1.planets[Graha.MOON.value].house

    mahadashas = compute_vimshottari_dashas(moon_lon, birth_date, span_years=120)
    chara = compute_chara_karakas(bundle)
    indu = compute_indu_lagna(bundle)

    # Pre-build each domain's significator set (chart-specific, computed once)
    sig_by_domain = {d.key: _build_significators(bundle, d, chara, indu) for d in _DOMAINS}

    _transit_cache: dict[str, tuple[int, int] | None] = {}

    def transit_positions(mid: date) -> tuple[int, int] | None:
        if engine is None:
            return None
        key = f"{mid.year}-{(mid.month - 1) // 3}"
        if key in _transit_cache:
            return _transit_cache[key]
        try:
            tz = bundle.birth.birth_datetime.tzinfo or timezone.utc
            snap = engine.compute_transits(
                bundle.birth, datetime(mid.year, mid.month, mid.day, 12, 0, tzinfo=tz)
            )
            res = (
                _from_moon(snap.planets[Graha.JUPITER.value].house, moon_house),
                _from_moon(snap.planets[Graha.SATURN.value].house, moon_house),
            )
        except Exception:
            res = None
        _transit_cache[key] = res
        return res

    predictions: list[LifeEventPrediction] = []

    for domain in _DOMAINS:
        sig = sig_by_domain[domain.key]
        candidates: list[tuple[int, LifeEventPrediction]] = []

        for maha in mahadashas:
            for antar in compute_antardasha_periods(maha):
                age_s = (antar.start_date - birth_date).days / 365.25
                if age_s > 120:
                    break

                d_score, d_factors = _score_dasha(bundle, domain, maha, antar, birth_date, sig)

                v_score, v_factors, v_summary = 0, [], None
                if domain.varga and domain.varga in bundle.vargas:
                    v_score, v_factors = _score_varga(
                        domain, bundle.vargas[domain.varga], maha.graha, antar.graha
                    )
                    if v_factors:
                        v_summary = "; ".join(v_factors[:2])

                t_score, t_summary = 0, None
                pos = transit_positions(_midpoint(antar))
                if pos is not None:
                    t_score, t_summary = _score_gochara(domain, pos[0], pos[1])

                total = d_score + v_score + t_score
                age_e = (antar.end_date - birth_date).days / 365.25
                all_factors = d_factors + v_factors
                if t_summary:
                    all_factors.append(t_summary)

                candidates.append((total, LifeEventPrediction(
                    domain_key=domain.key, label=domain.label,
                    category=domain.category.value, emoji=domain.emoji,
                    start_date=antar.start_date, end_date=antar.end_date,
                    age_start=round(age_s, 1), age_end=round(age_e, 1),
                    score=total, confidence=_confidence(total),
                    mahadasha_lord=maha.graha.value, antardasha_lord=antar.graha.value,
                    method_note=domain.method_note,
                    supporting_factors=all_factors,
                    divisional_signal=v_summary, transit_signal=t_summary,
                )))

        if not candidates:
            continue
        candidates.sort(key=lambda x: -x[0])

        if domain.can_repeat:
            selected: list[LifeEventPrediction] = []
            for sc, p in candidates:
                if sc < 4:
                    break
                if not any(p.start_date < s.end_date and p.end_date > s.start_date for s in selected):
                    selected.append(p)
                if len(selected) >= 3:
                    break
            predictions.extend(selected)
        else:
            predictions.append(candidates[0][1])

    predictions.sort(key=lambda p: p.start_date)
    return predictions
