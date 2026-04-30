"""Nakshatra detail model and reference data table."""

from pydantic import BaseModel, ConfigDict, Field

from vedic_ai.domain.enums import Graha, NakshatraName, Rasi


class NakshatraDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    nakshatra: NakshatraName
    index: int = Field(ge=1, le=27, description="1-indexed position in the zodiac")
    lord: Graha
    deity: str
    start_longitude: float = Field(ge=0.0, lt=360.0, description="Ecliptic start of this nakshatra")
    pada_rasis: list[Rasi] = Field(min_length=4, max_length=4)
    qualities: list[str] = Field(default_factory=list)


# Reference table: all 27 nakshatras with lords, deities, and pada rasis.
# Pada rasis follow the navamsa sequence starting from the navamsa of the nakshatra's first pada.
# Each nakshatra spans exactly 13°20' (360/27 degrees).
NAKSHATRA_DATA: dict[NakshatraName, NakshatraDetail] = {
    NakshatraName.ASHWINI: NakshatraDetail(
        nakshatra=NakshatraName.ASHWINI, index=1, lord=Graha.KETU, deity="Ashwini Kumaras",
        start_longitude=0.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
    ),
    NakshatraName.BHARANI: NakshatraDetail(
        nakshatra=NakshatraName.BHARANI, index=2, lord=Graha.VENUS, deity="Yama",
        start_longitude=13.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
    ),
    NakshatraName.KRITTIKA: NakshatraDetail(
        nakshatra=NakshatraName.KRITTIKA, index=3, lord=Graha.SUN, deity="Agni",
        start_longitude=26.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
    ),
    NakshatraName.ROHINI: NakshatraDetail(
        nakshatra=NakshatraName.ROHINI, index=4, lord=Graha.MOON, deity="Brahma",
        start_longitude=40.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
    ),
    NakshatraName.MRIGASHIRSHA: NakshatraDetail(
        nakshatra=NakshatraName.MRIGASHIRSHA, index=5, lord=Graha.MARS, deity="Soma",
        start_longitude=53.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
    ),
    NakshatraName.ARDRA: NakshatraDetail(
        nakshatra=NakshatraName.ARDRA, index=6, lord=Graha.RAHU, deity="Rudra",
        start_longitude=66.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
    ),
    NakshatraName.PUNARVASU: NakshatraDetail(
        nakshatra=NakshatraName.PUNARVASU, index=7, lord=Graha.JUPITER, deity="Aditi",
        start_longitude=80.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
    ),
    NakshatraName.PUSHYA: NakshatraDetail(
        nakshatra=NakshatraName.PUSHYA, index=8, lord=Graha.SATURN, deity="Brihaspati",
        start_longitude=93.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
    ),
    NakshatraName.ASHLESHA: NakshatraDetail(
        nakshatra=NakshatraName.ASHLESHA, index=9, lord=Graha.MERCURY, deity="Sarpa",
        start_longitude=106.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
    ),
    NakshatraName.MAGHA: NakshatraDetail(
        nakshatra=NakshatraName.MAGHA, index=10, lord=Graha.KETU, deity="Pitrs",
        start_longitude=120.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
    ),
    NakshatraName.PURVA_PHALGUNI: NakshatraDetail(
        nakshatra=NakshatraName.PURVA_PHALGUNI, index=11, lord=Graha.VENUS, deity="Bhaga",
        start_longitude=133.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
    ),
    NakshatraName.UTTARA_PHALGUNI: NakshatraDetail(
        nakshatra=NakshatraName.UTTARA_PHALGUNI, index=12, lord=Graha.SUN, deity="Aryaman",
        start_longitude=146.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
    ),
    NakshatraName.HASTA: NakshatraDetail(
        nakshatra=NakshatraName.HASTA, index=13, lord=Graha.MOON, deity="Savitar",
        start_longitude=160.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
    ),
    NakshatraName.CHITRA: NakshatraDetail(
        nakshatra=NakshatraName.CHITRA, index=14, lord=Graha.MARS, deity="Vishwakarma",
        start_longitude=173.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
    ),
    NakshatraName.SWATI: NakshatraDetail(
        nakshatra=NakshatraName.SWATI, index=15, lord=Graha.RAHU, deity="Vayu",
        start_longitude=186.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
    ),
    NakshatraName.VISHAKHA: NakshatraDetail(
        nakshatra=NakshatraName.VISHAKHA, index=16, lord=Graha.JUPITER, deity="Indra-Agni",
        start_longitude=200.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
    ),
    NakshatraName.ANURADHA: NakshatraDetail(
        nakshatra=NakshatraName.ANURADHA, index=17, lord=Graha.SATURN, deity="Mitra",
        start_longitude=213.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
    ),
    NakshatraName.JYESHTHA: NakshatraDetail(
        nakshatra=NakshatraName.JYESHTHA, index=18, lord=Graha.MERCURY, deity="Indra",
        start_longitude=226.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
    ),
    NakshatraName.MULA: NakshatraDetail(
        nakshatra=NakshatraName.MULA, index=19, lord=Graha.KETU, deity="Nirriti",
        start_longitude=240.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
    ),
    NakshatraName.PURVA_ASHADHA: NakshatraDetail(
        nakshatra=NakshatraName.PURVA_ASHADHA, index=20, lord=Graha.VENUS, deity="Apas",
        start_longitude=253.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
    ),
    NakshatraName.UTTARA_ASHADHA: NakshatraDetail(
        nakshatra=NakshatraName.UTTARA_ASHADHA, index=21, lord=Graha.SUN, deity="Vishwadevas",
        start_longitude=266.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
    ),
    NakshatraName.SHRAVANA: NakshatraDetail(
        nakshatra=NakshatraName.SHRAVANA, index=22, lord=Graha.MOON, deity="Vishnu",
        start_longitude=280.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
    ),
    NakshatraName.DHANISHTHA: NakshatraDetail(
        nakshatra=NakshatraName.DHANISHTHA, index=23, lord=Graha.MARS, deity="Ashta Vasus",
        start_longitude=293.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
    ),
    NakshatraName.SHATABHISHA: NakshatraDetail(
        nakshatra=NakshatraName.SHATABHISHA, index=24, lord=Graha.RAHU, deity="Varuna",
        start_longitude=306.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
    ),
    NakshatraName.PURVA_BHADRAPADA: NakshatraDetail(
        nakshatra=NakshatraName.PURVA_BHADRAPADA, index=25, lord=Graha.JUPITER, deity="Aja Ekapad",
        start_longitude=320.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
    ),
    NakshatraName.UTTARA_BHADRAPADA: NakshatraDetail(
        nakshatra=NakshatraName.UTTARA_BHADRAPADA, index=26, lord=Graha.SATURN, deity="Ahir Budhnya",
        start_longitude=333.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
    ),
    NakshatraName.REVATI: NakshatraDetail(
        nakshatra=NakshatraName.REVATI, index=27, lord=Graha.MERCURY, deity="Pushan",
        start_longitude=346.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
    ),
}
