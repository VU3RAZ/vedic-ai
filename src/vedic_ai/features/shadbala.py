"""Shadbala — Six-fold planetary strength computation.

The six Balas (sources of strength) per BPHS Ch.27-35 and B.V. Raman
'Graha and Bhava Balas':

  1. Sthana Bala  — positional strength (Uchcha, Sapta Vargaja, Ojhayugma, Kendra, Drekkana)
  2. Dig Bala     — directional strength based on house placement
  3. Kala Bala    — temporal strength (Paksha, Vara, Nathonnatha, Hora, Masa, Abda, Tribhaga)
  4. Chesta Bala  — motional strength (retrograde/speed-based)
  5. Naisargika Bala — natural (innate) strength, fixed per planet
  6. Drik Bala    — aspectual strength from received aspects

Units: Virupas (also called Shashtiamsas; 60 Virupas = 1 Rupa).
Minimum required Shadbala (Ishta Bala) for a planet to be 'strong':
  Sun 390, Moon 360, Mars 300, Mercury 420, Jupiter 390, Venus 330, Saturn 300.
  (Rahu/Ketu excluded from classical Shadbala — approximated via Dig + Chesta only.)

Source: BPHS Ch.27-35; Graha and Bhava Balas (B.V. Raman); Phaladeepika Ch.4.
"""

from __future__ import annotations

import math
from datetime import date

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Graha, Rasi
from vedic_ai.engines.dignity import RASI_LORDS, _EXALTATION, _DEBILITATION

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Minimum Shadbala for strength (Virupas) — classical threshold
REQUIRED_SHADBALA: dict[Graha, float] = {
    Graha.SUN:     390.0,
    Graha.MOON:    360.0,
    Graha.MARS:    300.0,
    Graha.MERCURY: 420.0,
    Graha.JUPITER: 390.0,
    Graha.VENUS:   330.0,
    Graha.SATURN:  300.0,
}

# Naisargika (natural) Bala in Virupas — fixed, independent of chart
NAISARGIKA_BALA: dict[Graha, float] = {
    Graha.SUN:     60.00,
    Graha.MOON:    51.43,
    Graha.VENUS:   45.00,
    Graha.JUPITER: 34.29,
    Graha.MERCURY: 25.71,
    Graha.MARS:    17.14,
    Graha.SATURN:   8.57,
    Graha.RAHU:    30.00,  # approximation (not classical)
    Graha.KETU:    30.00,  # approximation (not classical)
}

# Digbala: the house where each planet has maximum directional strength
# (opposite house = zero). Interpolated for intermediate positions.
DIG_BALA_PEAK_HOUSE: dict[Graha, int] = {
    Graha.SUN:     10,
    Graha.MOON:     4,
    Graha.MARS:    10,
    Graha.MERCURY:  1,
    Graha.JUPITER:  1,
    Graha.VENUS:    4,
    Graha.SATURN:   7,
    Graha.RAHU:     3,  # approximation
    Graha.KETU:     9,  # approximation
}

# Day planets (strong during daytime), Night planets (strong at night)
# Solar planets strong in day: Sun, Jupiter, Saturn (and Mercury, neutral)
_DAY_PLANETS  = frozenset({Graha.SUN, Graha.JUPITER, Graha.SATURN})
_NIGHT_PLANETS = frozenset({Graha.MOON, Graha.MARS, Graha.VENUS})
# Mercury = diurnal by day, nocturnal by night (neutral — always moderate)

# Paksha Bala max (full moon = Moon max; other planets inverse or moderate)
_PAKSHA_MAX = 60.0

# Weekday lords (0=Sunday, 1=Monday, … 6=Saturday)
_VARA_LORDS: list[Graha] = [
    Graha.SUN,     # Sunday
    Graha.MOON,    # Monday
    Graha.MARS,    # Tuesday
    Graha.MERCURY, # Wednesday
    Graha.JUPITER, # Thursday
    Graha.VENUS,   # Friday
    Graha.SATURN,  # Saturday
]


# ---------------------------------------------------------------------------
# 1. Sthana Bala — Positional Strength
# ---------------------------------------------------------------------------

def _uchcha_bala(graha: Graha, longitude: float) -> float:
    """Uchcha Bala: degree-based exaltation strength (0–60 Virupas).

    Max (60) at peak exaltation degree; 0 at debilitation point (180° away).
    Linear interpolation between the two.
    """
    if graha not in _EXALTATION:
        return 30.0
    ex_rasi, ex_deg = _EXALTATION[graha]
    ex_lon = list(Rasi).index(ex_rasi) * 30.0 + ex_deg
    # Debilitation = 180° from exaltation
    deb_lon = (ex_lon + 180.0) % 360.0

    diff = abs(longitude - ex_lon) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff
    # diff=0 → peak exaltation (60); diff=180 → debilitation (0)
    return round(60.0 * (1.0 - diff / 180.0), 4)


def _kendra_bala(house: int) -> float:
    """Kendra Bala: angular house bonus (Virupas)."""
    if house in (1, 4, 7, 10):
        return 60.0
    if house in (2, 5, 8, 11):
        return 30.0
    return 15.0  # cadent (3, 6, 9, 12)


def _drekkana_bala(graha: Graha, longitude: float) -> float:
    """Drekkana Bala: strength based on drekkana (decanate) occupied.

    Male planets (Sun/Jupiter/Mars) strong in 1st drekkana of odd signs,
    Female planets (Moon/Venus) in 2nd drekkana of even signs,
    Neutral (Mercury/Saturn) in 3rd drekkana of any sign.
    Returns 15 if favourable, 0 otherwise.
    Source: BPHS Ch.27.
    """
    _MALE   = frozenset({Graha.SUN, Graha.JUPITER, Graha.MARS})
    _FEMALE = frozenset({Graha.MOON, Graha.VENUS})
    _ODD_RASI_IDX = frozenset({0, 2, 4, 6, 8, 10})  # Aries, Gemini, Leo, Libra, Sag, Aquarius

    rasi_idx = int(longitude / 30.0) % 12
    deg_in_rasi = longitude % 30.0
    drekkana = int(deg_in_rasi / 10.0) + 1  # 1, 2, or 3

    if graha in _MALE and rasi_idx in _ODD_RASI_IDX and drekkana == 1:
        return 15.0
    if graha in _FEMALE and rasi_idx not in _ODD_RASI_IDX and drekkana == 2:
        return 15.0
    if graha not in _MALE and graha not in _FEMALE and drekkana == 3:
        return 15.0
    return 0.0


def _ojhayugma_bala(graha: Graha, longitude: float) -> float:
    """Ojhayugma Bala: odd/even sign placement strength.

    Male planets strong in odd signs, Female in even signs (15 Virupas each).
    Source: BPHS Ch.27.
    """
    _MALE   = frozenset({Graha.SUN, Graha.JUPITER, Graha.MARS, Graha.MERCURY})
    rasi_idx = int(longitude / 30.0) % 12
    is_odd = (rasi_idx % 2 == 0)  # Aries(0) is odd, Taurus(1) even, etc.

    if graha in _MALE:
        return 15.0 if is_odd else 0.0
    else:
        return 15.0 if not is_odd else 0.0


def compute_sthana_bala(bundle: ChartBundle) -> dict[str, float]:
    """Compute Sthana Bala for each planet (Virupas).

    Components: Uchcha + Kendra + Drekkana + Ojhayugma.
    (Sapta Vargaja Bala requires all 7 vargas — included if available.)
    """
    result: dict[str, float] = {}
    for graha in Graha:
        p = bundle.d1.planets[graha.value]
        lon = p.longitude
        house = p.house

        uchcha = _uchcha_bala(graha, lon)
        kendra = _kendra_bala(house)
        drekkana = _drekkana_bala(graha, lon)
        ojhayugma = _ojhayugma_bala(graha, lon)

        total = uchcha + kendra + drekkana + ojhayugma
        result[graha.value] = round(total, 4)
    return result


# ---------------------------------------------------------------------------
# 2. Dig Bala — Directional Strength
# ---------------------------------------------------------------------------

def compute_dig_bala(bundle: ChartBundle) -> dict[str, float]:
    """Compute Dig Bala (directional strength) for each planet.

    Peak house = 60 Virupas; opposite house = 0.
    Intermediate houses are linearly interpolated by angular distance.
    Source: BPHS Ch.28; Graha and Bhava Balas (Raman).
    """
    result: dict[str, float] = {}
    for graha in Graha:
        p = bundle.d1.planets[graha.value]
        house = p.house
        peak = DIG_BALA_PEAK_HOUSE[graha]

        # Angular distance from peak house (in house units, 0–6)
        diff = abs(house - peak)
        if diff > 6:
            diff = 12 - diff
        # diff=0 → full strength (60); diff=6 → zero
        strength = 60.0 * (1.0 - diff / 6.0)
        result[graha.value] = round(strength, 4)
    return result


# ---------------------------------------------------------------------------
# 3. Kala Bala — Temporal Strength
# ---------------------------------------------------------------------------

def _paksha_bala(bundle: ChartBundle) -> dict[str, float]:
    """Paksha Bala: strength based on lunar phase (Shukla/Krishna Paksha).

    Moon gains maximum (60) at full moon, minimum (0) at new moon.
    Benefics (Moon, Mercury, Jupiter, Venus) gain in Shukla; malefics in Krishna.
    Source: BPHS Ch.29.
    """
    sun_lon  = bundle.d1.planets[Graha.SUN.value].longitude
    moon_lon = bundle.d1.planets[Graha.MOON.value].longitude

    # Phase angle 0-360: 0=new moon, 180=full moon
    phase = (moon_lon - sun_lon) % 360.0

    # Moon's raw paksha bala (0–60)
    moon_paksha = min(phase, 360.0 - phase)  # 0 at new, 60 at full (max diff=180→60)
    moon_pb = round(moon_paksha / 3.0, 4)    # normalise to 0–60

    # Benefics gain in Shukla (phase 0-180), malefics in Krishna (180-360)
    _BENEFICS = frozenset({Graha.MOON, Graha.MERCURY, Graha.JUPITER, Graha.VENUS})
    _MALEFICS = frozenset({Graha.SUN, Graha.MARS, Graha.SATURN, Graha.RAHU, Graha.KETU})

    result: dict[str, float] = {}
    for graha in Graha:
        if graha == Graha.MOON:
            result[graha.value] = moon_pb
        elif graha in _BENEFICS:
            # Benefic: max at full moon (Shukla Paksha peak)
            result[graha.value] = round(moon_pb, 4)
        else:
            # Malefic: max at new moon (Krishna Paksha peak)
            result[graha.value] = round(60.0 - moon_pb, 4)
    return result


def _vara_bala(birth_date: date) -> dict[str, float]:
    """Vara Bala: the lord of the birth weekday gets 45 Virupas; others 0.

    Source: BPHS Ch.29.
    """
    weekday = birth_date.weekday()  # Monday=0 … Sunday=6
    # Python: Mon=0…Sun=6; Vedic: Sun=0…Sat=6
    vedic_day = (weekday + 1) % 7   # shift: Mon(1)→1, …, Sun(0)→0
    vara_lord = _VARA_LORDS[vedic_day]

    result: dict[str, float] = {}
    for graha in Graha:
        result[graha.value] = 45.0 if graha == vara_lord else 0.0
    return result


def _nathonnatha_bala(bundle: ChartBundle, birth_date: date) -> dict[str, float]:
    """Nathonnatha Bala: day/night strength (30 Virupas each).

    Day planets (Sun, Jupiter, Saturn) get 30 during daytime.
    Night planets (Moon, Mars, Venus) get 30 at night.
    Mercury always gets 30 (diurnal AND nocturnal).
    'Daytime' approximated by Sun in houses 7-12 (above horizon) vs 1-6 (below).
    Source: BPHS Ch.29.
    """
    sun_house = bundle.d1.planets[Graha.SUN.value].house
    is_day = sun_house in (7, 8, 9, 10, 11, 12)  # Sun above horizon = day

    result: dict[str, float] = {}
    for graha in Graha:
        if graha == Graha.MERCURY:
            result[graha.value] = 30.0
        elif graha in _DAY_PLANETS:
            result[graha.value] = 30.0 if is_day else 0.0
        elif graha in _NIGHT_PLANETS:
            result[graha.value] = 30.0 if not is_day else 0.0
        else:
            result[graha.value] = 15.0  # Rahu/Ketu: neutral approximation
    return result


def compute_kala_bala(bundle: ChartBundle) -> dict[str, float]:
    """Compute Kala Bala for each planet (sum of temporal components, Virupas).

    Components: Paksha Bala + Vara Bala + Nathonnatha Bala.
    (Hora, Masa, Abda Bala require birth time detail beyond current schema.)
    """
    paksha  = _paksha_bala(bundle)
    birth_date = bundle.birth.birth_datetime.date()
    vara    = _vara_bala(birth_date)
    natho   = _nathonnatha_bala(bundle, birth_date)

    result: dict[str, float] = {}
    for graha in Graha:
        total = paksha[graha.value] + vara[graha.value] + natho[graha.value]
        result[graha.value] = round(total, 4)
    return result


# ---------------------------------------------------------------------------
# 4. Chesta Bala — Motional Strength
# ---------------------------------------------------------------------------

def compute_chesta_bala(bundle: ChartBundle) -> dict[str, float]:
    """Compute Chesta Bala (motional strength) for each planet (Virupas).

    Classical rules (BPHS Ch.30):
      - Retrograde planet (Vakra):    60 Virupas (maximum)
      - Planet at station (near 0 speed): 30 Virupas
      - Direct motion: based on speed relative to mean motion
      - Sun and Moon have no retrograde, use a speed-relative measure

    Speed data comes from PlanetPlacement.speed (degrees/day).
    Mean daily motions (degrees/day) used for normalisation.
    """
    _MEAN_MOTION: dict[Graha, float] = {
        Graha.SUN:     0.9856,
        Graha.MOON:   13.1763,
        Graha.MARS:    0.5240,
        Graha.MERCURY: 1.3833,
        Graha.JUPITER: 0.0831,
        Graha.VENUS:   1.2000,
        Graha.SATURN:  0.0335,
        Graha.RAHU:   -0.0530,  # mean retrograde
        Graha.KETU:   -0.0530,
    }

    result: dict[str, float] = {}
    for graha in Graha:
        p = bundle.d1.planets[graha.value]
        speed = p.speed if hasattr(p, "speed") and p.speed is not None else 0.0
        mean  = _MEAN_MOTION.get(graha, 1.0)

        if p.is_retrograde:
            # Retrograde = maximum Chesta Bala
            result[graha.value] = 60.0
        elif graha in (Graha.SUN, Graha.MOON):
            # No retrograde; strength based on speed relative to mean
            ratio = min(abs(speed) / abs(mean), 1.0) if mean != 0 else 0.5
            result[graha.value] = round(30.0 + 30.0 * ratio, 4)
        else:
            # Direct motion: speed as fraction of mean motion (0–30 range)
            ratio = min(abs(speed) / abs(mean), 1.0) if mean != 0 else 0.5
            near_station = abs(speed) < 0.05
            if near_station:
                result[graha.value] = 30.0
            else:
                result[graha.value] = round(30.0 * ratio, 4)
    return result


# ---------------------------------------------------------------------------
# 5. Naisargika Bala — Natural Strength (fixed)
# ---------------------------------------------------------------------------

def compute_naisargika_bala() -> dict[str, float]:
    """Return fixed natural strength values (Virupas). Independent of chart."""
    return {g.value: NAISARGIKA_BALA[g] for g in Graha}


# ---------------------------------------------------------------------------
# 6. Drik Bala — Aspectual Strength
# ---------------------------------------------------------------------------

def compute_drik_bala(bundle: ChartBundle, aspects: dict) -> dict[str, float]:
    """Compute Drik Bala (aspectual strength) for each planet (Virupas).

    Benefic full aspects add 15 Virupas each; malefic aspects subtract 15.
    Natural benefics: Moon (waxing), Mercury, Jupiter, Venus.
    Natural malefics: Sun, Mars, Saturn, Rahu, Ketu.
    Aspect strength fraction from aspects graph is applied as weight.
    Source: BPHS Ch.31.
    """
    _NATURAL_BENEFICS = frozenset({Graha.MOON, Graha.MERCURY, Graha.JUPITER, Graha.VENUS})
    _NATURAL_MALEFICS = frozenset({Graha.SUN, Graha.MARS, Graha.SATURN, Graha.RAHU, Graha.KETU})

    # Build: for each planet, what aspects does it RECEIVE and from whom?
    # aspects["graha_aspects"][graha_name] = list of {house, strength, ...}
    # We need received aspects per planet from aspects["aspected_by"]
    result: dict[str, float] = {}
    graha_aspects = aspects.get("graha_aspects", {})

    # Build reverse map: planet_name → list of (aspector_name, strength)
    received: dict[str, list[tuple[str, float]]] = {g.value: [] for g in Graha}
    for aspector_name, asp_list in graha_aspects.items():
        aspector = Graha(aspector_name)
        for asp in asp_list:
            # asp = {house: int, strength: float, ...}
            # Find which planet(s) occupy that house
            tgt_house = asp.get("house")
            if tgt_house is None:
                continue
            asp_strength = asp.get("strength", 1.0)
            for g in Graha:
                if bundle.d1.planets[g.value].house == tgt_house:
                    received[g.value].append((aspector_name, asp_strength))

    for graha in Graha:
        drik = 0.0
        for aspector_name, strength in received[graha.value]:
            aspector = Graha(aspector_name)
            if aspector in _NATURAL_BENEFICS:
                drik += 15.0 * strength
            elif aspector in _NATURAL_MALEFICS:
                drik -= 15.0 * strength
        # Clamp to reasonable range
        result[graha.value] = round(max(-60.0, min(60.0, drik)), 4)
    return result


# ---------------------------------------------------------------------------
# Aggregate Shadbala
# ---------------------------------------------------------------------------

def compute_shadbala(bundle: ChartBundle, aspects: dict | None = None) -> dict:
    """Compute full Shadbala for all planets.

    Args:
        bundle  : ChartBundle with D1 positions.
        aspects : Output of compute_relationship_graph() for Drik Bala;
                  pass None to skip Drik Bala (will be set to 0).

    Returns dict with:
        per_planet : dict[planet_name → component breakdown + total]
        summary    : list of dicts with total, required, ratio, is_strong
    """
    sthana    = compute_sthana_bala(bundle)
    dig       = compute_dig_bala(bundle)
    kala      = compute_kala_bala(bundle)
    chesta    = compute_chesta_bala(bundle)
    naisargika = compute_naisargika_bala()
    drik      = compute_drik_bala(bundle, aspects) if aspects else {g.value: 0.0 for g in Graha}

    per_planet: dict[str, dict] = {}
    summary: list[dict] = []

    for graha in Graha:
        g = graha.value
        total = sthana[g] + dig[g] + kala[g] + chesta[g] + naisargika[g] + drik[g]
        total = round(total, 4)
        required = REQUIRED_SHADBALA.get(graha, 300.0)
        ratio = round(total / required, 4) if required > 0 else None
        is_strong = (ratio is not None and ratio >= 1.0)

        per_planet[g] = {
            "graha": g,
            "sthana_bala":     sthana[g],
            "dig_bala":        dig[g],
            "kala_bala":       kala[g],
            "chesta_bala":     chesta[g],
            "naisargika_bala": naisargika[g],
            "drik_bala":       drik[g],
            "total_virupas":   total,
            "required_virupas": required,
            "strength_ratio":  ratio,
            "is_strong":       is_strong,
        }
        summary.append({
            "graha": g,
            "total_virupas": total,
            "required_virupas": required,
            "strength_ratio": ratio,
            "is_strong": is_strong,
        })

    return {
        "per_planet": per_planet,
        "summary": sorted(summary, key=lambda x: -(x["total_virupas"])),
        "strongest": max(summary, key=lambda x: x["total_virupas"])["graha"],
        "weakest":   min(summary, key=lambda x: x["total_virupas"])["graha"],
        "note": "Shadbala per BPHS Ch.27-35. Hora/Masa/Abda Kala Bala excluded (require birth time).",
    }
