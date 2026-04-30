"""Nakshatra feature extraction for all planets and the ascendant."""

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import NakshatraName
from vedic_ai.domain.nakshatra import NAKSHATRA_DATA
from vedic_ai.engines.normalizer import _longitude_to_nakshatra


def extract_nakshatra_features(bundle: ChartBundle) -> dict:
    """Return nakshatra metadata for all 9 grahas and the ascendant.

    Returns:
        dict with keys:
        - ``planets``: graha → nakshatra detail
        - ``ascendant``: nakshatra detail for the ascendant degree
    """
    planet_naks: dict[str, dict] = {}
    for graha_name, placement in bundle.d1.planets.items():
        nak_name = placement.nakshatra.nakshatra
        detail = NAKSHATRA_DATA[nak_name]
        planet_naks[graha_name] = {
            "nakshatra": nak_name.value,
            "index": detail.index,
            "pada": placement.nakshatra.pada,
            "lord": placement.nakshatra.nakshatra_lord.value,
            "deity": detail.deity,
            "degree_in_nakshatra": round(placement.nakshatra.degree_in_nakshatra, 4),
            "pada_rasi": detail.pada_rasis[placement.nakshatra.pada - 1].value,
            "qualities": detail.qualities,
        }

    # Ascendant nakshatra
    asc_lon = bundle.d1.ascendant_longitude
    asc_nak, asc_pada, asc_lord, asc_deg = _longitude_to_nakshatra(asc_lon)
    asc_detail = NAKSHATRA_DATA[asc_nak]
    ascendant_nak = {
        "nakshatra": asc_nak.value,
        "index": asc_detail.index,
        "pada": asc_pada,
        "lord": asc_lord.value,
        "deity": asc_detail.deity,
        "degree_in_nakshatra": round(asc_deg, 4),
        "pada_rasi": asc_detail.pada_rasis[asc_pada - 1].value,
        "qualities": asc_detail.qualities,
    }

    return {"planets": planet_naks, "ascendant": ascendant_nak}
