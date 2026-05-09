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
    # Structured qualities (BPHS / Parasara / Jataka Chandrika)
    gana: str = Field(default="", description="Deva / Manushya / Rakshasa — used in Gana Kuta")
    nadi: str = Field(default="", description="Aadi / Madhya / Antya (Vata/Pitta/Kapha) — Nadi Kuta")
    yoni: str = Field(default="", description="Animal symbol pair — Yoni Kuta compatibility")
    nature: str = Field(default="", description="Dhruva/Chara/Ugra/Tikshna/Mridu/Laghu/Mishra — Muhurta quality")
    qualities: list[str] = Field(default_factory=list, description="Concatenated quality tags")


# Reference table: all 27 nakshatras with lords, deities, pada rasis, and qualities.
# Sources: BPHS (Parasara), Jataka Chandrika, Muhurta Chintamani, Phaladeepika.
# Each nakshatra spans exactly 13°20' (360/27 degrees).
NAKSHATRA_DATA: dict[NakshatraName, NakshatraDetail] = {
    NakshatraName.ASHWINI: NakshatraDetail(
        nakshatra=NakshatraName.ASHWINI, index=1, lord=Graha.KETU, deity="Ashwini Kumaras",
        start_longitude=0.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
        gana="Deva", nadi="Aadi", yoni="Ashwa", nature="Laghu",
        qualities=["Deva", "Aadi", "Ashwa", "Laghu"],
    ),
    NakshatraName.BHARANI: NakshatraDetail(
        nakshatra=NakshatraName.BHARANI, index=2, lord=Graha.VENUS, deity="Yama",
        start_longitude=13.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
        gana="Manushya", nadi="Madhya", yoni="Gaja", nature="Ugra",
        qualities=["Manushya", "Madhya", "Gaja", "Ugra"],
    ),
    NakshatraName.KRITTIKA: NakshatraDetail(
        nakshatra=NakshatraName.KRITTIKA, index=3, lord=Graha.SUN, deity="Agni",
        start_longitude=26.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
        gana="Rakshasa", nadi="Antya", yoni="Mesha", nature="Mishra",
        qualities=["Rakshasa", "Antya", "Mesha", "Mishra"],
    ),
    NakshatraName.ROHINI: NakshatraDetail(
        nakshatra=NakshatraName.ROHINI, index=4, lord=Graha.MOON, deity="Brahma",
        start_longitude=40.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
        gana="Manushya", nadi="Antya", yoni="Sarpa", nature="Dhruva",
        qualities=["Manushya", "Antya", "Sarpa", "Dhruva"],
    ),
    NakshatraName.MRIGASHIRSHA: NakshatraDetail(
        nakshatra=NakshatraName.MRIGASHIRSHA, index=5, lord=Graha.MARS, deity="Soma",
        start_longitude=53.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
        gana="Deva", nadi="Madhya", yoni="Sarpa", nature="Mridu",
        qualities=["Deva", "Madhya", "Sarpa", "Mridu"],
    ),
    NakshatraName.ARDRA: NakshatraDetail(
        nakshatra=NakshatraName.ARDRA, index=6, lord=Graha.RAHU, deity="Rudra",
        start_longitude=66.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
        gana="Manushya", nadi="Aadi", yoni="Shwana", nature="Tikshna",
        qualities=["Manushya", "Aadi", "Shwana", "Tikshna"],
    ),
    NakshatraName.PUNARVASU: NakshatraDetail(
        nakshatra=NakshatraName.PUNARVASU, index=7, lord=Graha.JUPITER, deity="Aditi",
        start_longitude=80.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
        gana="Deva", nadi="Aadi", yoni="Marjara", nature="Chara",
        qualities=["Deva", "Aadi", "Marjara", "Chara"],
    ),
    NakshatraName.PUSHYA: NakshatraDetail(
        nakshatra=NakshatraName.PUSHYA, index=8, lord=Graha.SATURN, deity="Brihaspati",
        start_longitude=93.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
        gana="Deva", nadi="Madhya", yoni="Mesha", nature="Laghu",
        qualities=["Deva", "Madhya", "Mesha", "Laghu"],
    ),
    NakshatraName.ASHLESHA: NakshatraDetail(
        nakshatra=NakshatraName.ASHLESHA, index=9, lord=Graha.MERCURY, deity="Sarpa",
        start_longitude=106.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
        gana="Rakshasa", nadi="Antya", yoni="Marjara", nature="Tikshna",
        qualities=["Rakshasa", "Antya", "Marjara", "Tikshna"],
    ),
    NakshatraName.MAGHA: NakshatraDetail(
        nakshatra=NakshatraName.MAGHA, index=10, lord=Graha.KETU, deity="Pitrs",
        start_longitude=120.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
        gana="Rakshasa", nadi="Antya", yoni="Mushaka", nature="Ugra",
        qualities=["Rakshasa", "Antya", "Mushaka", "Ugra"],
    ),
    NakshatraName.PURVA_PHALGUNI: NakshatraDetail(
        nakshatra=NakshatraName.PURVA_PHALGUNI, index=11, lord=Graha.VENUS, deity="Bhaga",
        start_longitude=133.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
        gana="Manushya", nadi="Madhya", yoni="Mushaka", nature="Ugra",
        qualities=["Manushya", "Madhya", "Mushaka", "Ugra"],
    ),
    NakshatraName.UTTARA_PHALGUNI: NakshatraDetail(
        nakshatra=NakshatraName.UTTARA_PHALGUNI, index=12, lord=Graha.SUN, deity="Aryaman",
        start_longitude=146.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
        gana="Manushya", nadi="Aadi", yoni="Vrishabha", nature="Dhruva",
        qualities=["Manushya", "Aadi", "Vrishabha", "Dhruva"],
    ),
    NakshatraName.HASTA: NakshatraDetail(
        nakshatra=NakshatraName.HASTA, index=13, lord=Graha.MOON, deity="Savitar",
        start_longitude=160.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
        gana="Deva", nadi="Aadi", yoni="Mahisha", nature="Laghu",
        qualities=["Deva", "Aadi", "Mahisha", "Laghu"],
    ),
    NakshatraName.CHITRA: NakshatraDetail(
        nakshatra=NakshatraName.CHITRA, index=14, lord=Graha.MARS, deity="Vishwakarma",
        start_longitude=173.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
        gana="Rakshasa", nadi="Madhya", yoni="Vyaghra", nature="Mridu",
        qualities=["Rakshasa", "Madhya", "Vyaghra", "Mridu"],
    ),
    NakshatraName.SWATI: NakshatraDetail(
        nakshatra=NakshatraName.SWATI, index=15, lord=Graha.RAHU, deity="Vayu",
        start_longitude=186.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
        gana="Deva", nadi="Antya", yoni="Mahisha", nature="Chara",
        qualities=["Deva", "Antya", "Mahisha", "Chara"],
    ),
    NakshatraName.VISHAKHA: NakshatraDetail(
        nakshatra=NakshatraName.VISHAKHA, index=16, lord=Graha.JUPITER, deity="Indra-Agni",
        start_longitude=200.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
        gana="Rakshasa", nadi="Antya", yoni="Vyaghra", nature="Mishra",
        qualities=["Rakshasa", "Antya", "Vyaghra", "Mishra"],
    ),
    NakshatraName.ANURADHA: NakshatraDetail(
        nakshatra=NakshatraName.ANURADHA, index=17, lord=Graha.SATURN, deity="Mitra",
        start_longitude=213.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
        gana="Deva", nadi="Madhya", yoni="Mriga", nature="Mridu",
        qualities=["Deva", "Madhya", "Mriga", "Mridu"],
    ),
    NakshatraName.JYESHTHA: NakshatraDetail(
        nakshatra=NakshatraName.JYESHTHA, index=18, lord=Graha.MERCURY, deity="Indra",
        start_longitude=226.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
        gana="Rakshasa", nadi="Aadi", yoni="Mriga", nature="Tikshna",
        qualities=["Rakshasa", "Aadi", "Mriga", "Tikshna"],
    ),
    NakshatraName.MULA: NakshatraDetail(
        nakshatra=NakshatraName.MULA, index=19, lord=Graha.KETU, deity="Nirriti",
        start_longitude=240.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
        gana="Rakshasa", nadi="Aadi", yoni="Shwana", nature="Tikshna",
        qualities=["Rakshasa", "Aadi", "Shwana", "Tikshna"],
    ),
    NakshatraName.PURVA_ASHADHA: NakshatraDetail(
        nakshatra=NakshatraName.PURVA_ASHADHA, index=20, lord=Graha.VENUS, deity="Apas",
        start_longitude=253.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
        gana="Manushya", nadi="Madhya", yoni="Vanara", nature="Ugra",
        qualities=["Manushya", "Madhya", "Vanara", "Ugra"],
    ),
    NakshatraName.UTTARA_ASHADHA: NakshatraDetail(
        nakshatra=NakshatraName.UTTARA_ASHADHA, index=21, lord=Graha.SUN, deity="Vishwadevas",
        start_longitude=266.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
        gana="Manushya", nadi="Antya", yoni="Nakula", nature="Dhruva",
        qualities=["Manushya", "Antya", "Nakula", "Dhruva"],
    ),
    NakshatraName.SHRAVANA: NakshatraDetail(
        nakshatra=NakshatraName.SHRAVANA, index=22, lord=Graha.MOON, deity="Vishnu",
        start_longitude=280.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
        gana="Deva", nadi="Antya", yoni="Vanara", nature="Chara",
        qualities=["Deva", "Antya", "Vanara", "Chara"],
    ),
    NakshatraName.DHANISHTHA: NakshatraDetail(
        nakshatra=NakshatraName.DHANISHTHA, index=23, lord=Graha.MARS, deity="Ashta Vasus",
        start_longitude=293.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
        gana="Rakshasa", nadi="Madhya", yoni="Simha", nature="Chara",
        qualities=["Rakshasa", "Madhya", "Simha", "Chara"],
    ),
    NakshatraName.SHATABHISHA: NakshatraDetail(
        nakshatra=NakshatraName.SHATABHISHA, index=24, lord=Graha.RAHU, deity="Varuna",
        start_longitude=306.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
        gana="Rakshasa", nadi="Aadi", yoni="Ashwa", nature="Chara",
        qualities=["Rakshasa", "Aadi", "Ashwa", "Chara"],
    ),
    NakshatraName.PURVA_BHADRAPADA: NakshatraDetail(
        nakshatra=NakshatraName.PURVA_BHADRAPADA, index=25, lord=Graha.JUPITER, deity="Aja Ekapad",
        start_longitude=320.0,
        pada_rasis=[Rasi.ARIES, Rasi.TAURUS, Rasi.GEMINI, Rasi.CANCER],
        gana="Manushya", nadi="Aadi", yoni="Simha", nature="Ugra",
        qualities=["Manushya", "Aadi", "Simha", "Ugra"],
    ),
    NakshatraName.UTTARA_BHADRAPADA: NakshatraDetail(
        nakshatra=NakshatraName.UTTARA_BHADRAPADA, index=26, lord=Graha.SATURN, deity="Ahir Budhnya",
        start_longitude=333.333,
        pada_rasis=[Rasi.LEO, Rasi.VIRGO, Rasi.LIBRA, Rasi.SCORPIO],
        gana="Manushya", nadi="Madhya", yoni="Vrishabha", nature="Dhruva",
        qualities=["Manushya", "Madhya", "Vrishabha", "Dhruva"],
    ),
    NakshatraName.REVATI: NakshatraDetail(
        nakshatra=NakshatraName.REVATI, index=27, lord=Graha.MERCURY, deity="Pushan",
        start_longitude=346.667,
        pada_rasis=[Rasi.SAGITTARIUS, Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.PISCES],
        gana="Deva", nadi="Antya", yoni="Gaja", nature="Mridu",
        qualities=["Deva", "Antya", "Gaja", "Mridu"],
    ),
}
