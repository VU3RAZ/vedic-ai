"""House lordship feature extraction.

Maps each house to its lord, the lord's placement, and the lord's dignity.
"""

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Graha
from vedic_ai.features.base import DUSTHANA_HOUSES, HOUSE_TYPES, KENDRA_HOUSES, TRIKONA_HOUSES
from vedic_ai.features.strength import full_dignity

# ── Step 3.1: Natural house karakas (significators) ──────────────────────────
# Based on B.V. Raman HTJH.
HOUSE_KARAKAS: dict[int, list[str]] = {
    1:  ["Sun"],
    2:  ["Jupiter"],
    3:  ["Mars"],
    4:  ["Moon", "Venus"],
    5:  ["Jupiter"],
    6:  ["Mars", "Saturn"],
    7:  ["Venus"],
    8:  ["Saturn"],
    9:  ["Jupiter", "Sun"],
    10: ["Sun", "Mercury", "Jupiter", "Saturn"],
    11: ["Jupiter"],
    12: ["Saturn", "Ketu"],
}


def compute_house_lordships(bundle: ChartBundle) -> dict[int, dict]:
    """Map each house to its lord and the lord's full placement profile.

    Returns:
        dict[house_number, lordship_record] where each record contains:
        - lord graha name
        - lord's house, rasi, dignity
        - whether lord is in a kendra, trikona, or dusthana
        - whether lord is retrograde
    """
    result: dict[int, dict] = {}
    for house_num, house in bundle.d1.houses.items():
        lord_name = house.lord.value
        lord_placement = bundle.d1.planets[lord_name]
        lord_graha = Graha(lord_name)

        lord_house = lord_placement.house
        lord_rasi = lord_placement.rasi.rasi
        lord_deg = lord_placement.rasi.degree_in_rasi
        lord_dignity_str = full_dignity(lord_graha, lord_rasi, lord_deg)

        # Karaka (natural significator) condition
        karakas = HOUSE_KARAKAS.get(house_num, [])
        karaka_conditions: list[dict] = []
        for kname in karakas:
            try:
                kp = bundle.d1.planets[kname]
                kdig = full_dignity(Graha(kname), kp.rasi.rasi, kp.rasi.degree_in_rasi)
                karaka_conditions.append({
                    "karaka": kname,
                    "house": kp.house,
                    "rasi": kp.rasi.rasi.value,
                    "dignity": kdig,
                    "is_retrograde": kp.is_retrograde,
                    "in_dusthana": kp.house in DUSTHANA_HOUSES,
                    "in_kendra": kp.house in KENDRA_HOUSES,
                    "in_trikona": kp.house in TRIKONA_HOUSES,
                })
            except (KeyError, ValueError):
                pass

        result[house_num] = {
            "house": house_num,
            "rasi": house.rasi.value,
            "lord": lord_name,
            "lord_house": lord_house,
            "lord_rasi": lord_rasi.value,
            "lord_degree_in_rasi": round(lord_deg, 4),
            "lord_dignity": lord_dignity_str,
            "lord_is_retrograde": lord_placement.is_retrograde,
            "lord_nakshatra": lord_placement.nakshatra.nakshatra.value,
            "lord_in_kendra": lord_house in KENDRA_HOUSES,
            "lord_in_trikona": lord_house in TRIKONA_HOUSES,
            "lord_in_dusthana": lord_house in DUSTHANA_HOUSES,
            "lord_house_type": HOUSE_TYPES[lord_house],
            "occupants": [g.value for g in house.occupants],
            "is_occupied": len(house.occupants) > 0,
            "karakas": karakas,
            "karaka_conditions": karaka_conditions,
        }
    return result
