"""Functional planetary nature per lagna — B.V. Raman methodology (HTJH).

Each planet's benefic/malefic role is determined by the houses it lords relative
to the lagna, NOT by its natural character.  This is the foundation of Raman's
house-by-house prediction method.

Yogakaraka rule: a planet that lords one house in {4,7,10} (pure kendra) AND one
house in {5,9} (pure trikona) — being lord of two different houses — is the most
powerful functional benefic and the prime engine of raja yoga.
"""
from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Graha, Rasi
from vedic_ai.engines.dignity import RASI_LORDS
from vedic_ai.features.base import KENDRA_HOUSES, TRIKONA_HOUSES

# ── Step 1.2: Functional nature table (B.V. Raman, HTJH) ──────────────────────
# Values: "yogakaraka" | "benefic" | "neutral" | "malefic"
# Rahu/Ketu take on the nature of their sign lord; marked neutral here and
# overridden in compute_functional_nature() by dispositor mapping.
_NATURE_TABLE: dict[Rasi, dict[Graha, str]] = {
    Rasi.ARIES: {
        Graha.SUN:     "benefic",
        Graha.MOON:    "neutral",
        Graha.MARS:    "benefic",
        Graha.MERCURY: "malefic",
        Graha.JUPITER: "benefic",
        Graha.VENUS:   "malefic",
        Graha.SATURN:  "malefic",
    },
    Rasi.TAURUS: {
        Graha.SUN:     "benefic",
        Graha.MOON:    "malefic",
        Graha.MARS:    "benefic",
        Graha.MERCURY: "benefic",
        Graha.JUPITER: "malefic",
        Graha.VENUS:   "malefic",   # lagna lord — HTJH marks as malefic (owns 1+6)
        Graha.SATURN:  "yogakaraka",
    },
    Rasi.GEMINI: {
        Graha.SUN:     "malefic",
        Graha.MOON:    "neutral",
        Graha.MARS:    "malefic",
        Graha.MERCURY: "neutral",
        Graha.JUPITER: "malefic",
        Graha.VENUS:   "benefic",   # sole benefic per Raman
        Graha.SATURN:  "neutral",
    },
    Rasi.CANCER: {
        Graha.SUN:     "neutral",
        Graha.MOON:    "neutral",
        Graha.MARS:    "yogakaraka",
        Graha.MERCURY: "malefic",
        Graha.JUPITER: "benefic",
        Graha.VENUS:   "malefic",
        Graha.SATURN:  "neutral",
    },
    Rasi.LEO: {
        Graha.SUN:     "benefic",
        Graha.MOON:    "neutral",
        Graha.MARS:    "yogakaraka",
        Graha.MERCURY: "malefic",
        Graha.JUPITER: "neutral",
        Graha.VENUS:   "malefic",
        Graha.SATURN:  "neutral",
    },
    Rasi.VIRGO: {
        Graha.SUN:     "neutral",
        Graha.MOON:    "malefic",
        Graha.MARS:    "malefic",
        Graha.MERCURY: "neutral",
        Graha.JUPITER: "malefic",
        Graha.VENUS:   "benefic",   # best benefic (owns 2+9)
        Graha.SATURN:  "neutral",
    },
    Rasi.LIBRA: {
        Graha.SUN:     "malefic",
        Graha.MOON:    "malefic",
        Graha.MARS:    "neutral",   # feeble benefic → treated as neutral
        Graha.MERCURY: "benefic",
        Graha.JUPITER: "malefic",
        Graha.VENUS:   "benefic",
        Graha.SATURN:  "yogakaraka",
    },
    Rasi.SCORPIO: {
        Graha.SUN:     "benefic",
        Graha.MOON:    "benefic",   # best benefic (owns 9)
        Graha.MARS:    "neutral",
        Graha.MERCURY: "malefic",
        Graha.JUPITER: "benefic",
        Graha.VENUS:   "malefic",
        Graha.SATURN:  "neutral",
    },
    Rasi.SAGITTARIUS: {
        Graha.SUN:     "benefic",
        Graha.MOON:    "neutral",
        Graha.MARS:    "benefic",
        Graha.MERCURY: "malefic",
        Graha.JUPITER: "neutral",
        Graha.VENUS:   "malefic",
        Graha.SATURN:  "malefic",
    },
    Rasi.CAPRICORN: {
        Graha.SUN:     "malefic",
        Graha.MOON:    "malefic",
        Graha.MARS:    "malefic",
        Graha.MERCURY: "benefic",
        Graha.JUPITER: "malefic",
        Graha.VENUS:   "yogakaraka",
        Graha.SATURN:  "benefic",
    },
    Rasi.AQUARIUS: {
        Graha.SUN:     "benefic",
        Graha.MOON:    "malefic",
        Graha.MARS:    "benefic",
        Graha.MERCURY: "neutral",
        Graha.JUPITER: "malefic",
        Graha.VENUS:   "yogakaraka",
        Graha.SATURN:  "benefic",
    },
    Rasi.PISCES: {
        Graha.SUN:     "malefic",
        Graha.MOON:    "benefic",
        Graha.MARS:    "benefic",
        Graha.MERCURY: "malefic",
        Graha.JUPITER: "neutral",
        Graha.VENUS:   "malefic",
        Graha.SATURN:  "malefic",
    },
}

# Pure kendras and trikonas (excluding H1 to avoid auto-qualifying lagna lord)
_PURE_KENDRA   = frozenset({4, 7, 10})
_PURE_TRIKONA  = frozenset({5, 9})


def _lagna_rasi(bundle: ChartBundle) -> Rasi:
    return bundle.d1.houses[1].rasi


def _house_lords(bundle: ChartBundle) -> dict[int, Graha]:
    """Map each house number to its lord Graha."""
    return {h: bundle.d1.houses[h].lord for h in range(1, 13)}


def _graha_to_houses(lords: dict[int, Graha]) -> dict[Graha, list[int]]:
    """Invert house→lord mapping to graha→[houses owned]."""
    result: dict[Graha, list[int]] = {}
    for h, g in lords.items():
        result.setdefault(g, []).append(h)
    return result


def compute_functional_nature(bundle: ChartBundle) -> dict:
    """Compute each planet's functional role for this lagna.

    Returns a dict with:
      lagna_rasi       : str
      planets          : {graha_name: {role, houses_owned, is_yogakaraka,
                                       is_maraka, label}}
      yogakarakas      : [graha_name, ...]
      maraka_lords     : [graha_name, ...]   (lords of H2 and H7)
    """
    lagna = _lagna_rasi(bundle)
    base_table = _NATURE_TABLE.get(lagna, {})
    lords = _house_lords(bundle)
    owned = _graha_to_houses(lords)

    # Detect yogakarakas dynamically (cross-check with table)
    dynamic_yk: set[Graha] = set()
    for g, houses in owned.items():
        owns_pure_kendra  = any(h in _PURE_KENDRA  for h in houses)
        owns_pure_trikona = any(h in _PURE_TRIKONA for h in houses)
        kendra_house  = next((h for h in houses if h in _PURE_KENDRA),  None)
        trikona_house = next((h for h in houses if h in _PURE_TRIKONA), None)
        if owns_pure_kendra and owns_pure_trikona and kendra_house != trikona_house:
            dynamic_yk.add(g)

    # Maraka lords (lords of H2 and H7)
    maraka_lords: list[str] = []
    for h in (2, 7):
        m = lords.get(h)
        if m and m.value not in maraka_lords:
            maraka_lords.append(m.value)

    planets_out: dict[str, dict] = {}
    for g in Graha:
        # Shadow planets follow dispositor nature
        if g in (Graha.RAHU, Graha.KETU):
            sign = bundle.d1.planets[g.value].rasi.rasi
            dispositor = RASI_LORDS[sign]
            role = base_table.get(dispositor, "neutral")
        else:
            role = base_table.get(g, "neutral")

        # Dynamic yogakaraka overrides table role
        is_yk_dynamic = g in dynamic_yk
        is_yk_table   = (base_table.get(g) == "yogakaraka")
        is_yk = is_yk_dynamic or is_yk_table
        if is_yk:
            role = "yogakaraka"

        is_maraka = g.value in maraka_lords

        houses = owned.get(g, [])
        label_parts: list[str] = []
        if is_yk:
            label_parts.append("Yogakaraka")
        if role == "benefic":
            label_parts.append("functional benefic")
        elif role == "malefic":
            label_parts.append("functional malefic")
        elif role == "neutral":
            label_parts.append("neutral")
        if is_maraka:
            label_parts.append("maraka")

        planets_out[g.value] = {
            "role": role,
            "is_yogakaraka": is_yk,
            "is_maraka": is_maraka,
            "houses_owned": sorted(houses),
            "label": ", ".join(label_parts) or "neutral",
        }

    yogakarakas = [n for n, d in planets_out.items() if d["is_yogakaraka"]]

    return {
        "lagna_rasi": lagna.value,
        "planets": planets_out,
        "yogakarakas": yogakarakas,
        "maraka_lords": maraka_lords,
    }
