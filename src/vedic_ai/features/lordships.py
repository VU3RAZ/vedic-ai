"""House lordship feature extraction.

Maps each house to its lord, the lord's placement, and the lord's dignity.
"""

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Graha
from vedic_ai.features.base import DUSTHANA_HOUSES, HOUSE_TYPES, KENDRA_HOUSES, TRIKONA_HOUSES
from vedic_ai.features.strength import full_dignity


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
        }
    return result
