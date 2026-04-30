"""Transit feature extraction: compare transiting planets to natal chart."""

from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle, TransitSnapshot
from vedic_ai.domain.enums import Graha

# Vedic aspect offsets in houses (1-based relative distance, whole-sign)
_GRAHA_ASPECTS: dict[Graha, list[int]] = {
    Graha.SUN:     [7],
    Graha.MOON:    [7],
    Graha.MARS:    [4, 7, 8],
    Graha.MERCURY: [7],
    Graha.JUPITER: [5, 7, 9],
    Graha.VENUS:   [7],
    Graha.SATURN:  [3, 7, 10],
    Graha.RAHU:    [5, 7, 9],
    Graha.KETU:    [5, 7, 9],
}


def _house_of_longitude(longitude: float, asc_longitude: float) -> int:
    """Return 1-based whole-sign house for a given sidereal longitude."""
    asc_sign = int(asc_longitude / 30.0)
    planet_sign = int(longitude / 30.0)
    return ((planet_sign - asc_sign) % 12) + 1


def compute_transit_features(
    natal_bundle: ChartBundle,
    transit_snapshot: TransitSnapshot,
) -> dict:
    """Return transit-to-natal feature dict with nested structure.

    Returns a dict with a single top-level key 'transit' containing per-graha
    sub-dicts, compatible with the dot-notation rule evaluator
    (e.g. transit.Sun.house).

    Per-graha keys:
      house           current whole-sign house in natal chart frame
      sign            current rasi name
      on_natal_<h>    True if transiting planet is in natal house h (self)
      aspects_house_<h>  True for each house aspected by transiting planet
    """
    asc_lon = natal_bundle.d1.ascendant_longitude
    graha_dicts: dict[str, dict] = {}

    for graha in Graha:
        gname = graha.value
        transit_placement = transit_snapshot.planets.get(gname)
        if transit_placement is None:
            continue

        t_lon = transit_placement.longitude
        t_house = _house_of_longitude(t_lon, asc_lon)
        t_sign = transit_placement.rasi.rasi.value

        graha_dict: dict = {
            "house": t_house,
            "sign": t_sign,
        }

        natal_placement = natal_bundle.d1.planets.get(gname)
        if natal_placement is not None:
            natal_house = natal_placement.house
            graha_dict[f"on_natal_{natal_house}"] = (t_house == natal_house)

        aspect_offsets = _GRAHA_ASPECTS.get(graha, [7])
        for offset in aspect_offsets:
            aspected_house = ((t_house - 1 + offset - 1) % 12) + 1
            graha_dict[f"aspects_house_{aspected_house}"] = True

        graha_dicts[gname] = graha_dict

    return {"transit": graha_dicts}
