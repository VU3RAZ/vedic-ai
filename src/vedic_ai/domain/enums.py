"""All domain enumerations for the Vedic AI framework.

Import from here rather than individual modules so every module shares
a single canonical definition for each enum.
"""

from enum import Enum


class Graha(str, Enum):
    SUN = "Sun"
    MOON = "Moon"
    MARS = "Mars"
    MERCURY = "Mercury"
    JUPITER = "Jupiter"
    VENUS = "Venus"
    SATURN = "Saturn"
    RAHU = "Rahu"
    KETU = "Ketu"


class Rasi(str, Enum):
    ARIES = "Aries"
    TAURUS = "Taurus"
    GEMINI = "Gemini"
    CANCER = "Cancer"
    LEO = "Leo"
    VIRGO = "Virgo"
    LIBRA = "Libra"
    SCORPIO = "Scorpio"
    SAGITTARIUS = "Sagittarius"
    CAPRICORN = "Capricorn"
    AQUARIUS = "Aquarius"
    PISCES = "Pisces"


class NakshatraName(str, Enum):
    ASHWINI = "Ashwini"
    BHARANI = "Bharani"
    KRITTIKA = "Krittika"
    ROHINI = "Rohini"
    MRIGASHIRSHA = "Mrigashirsha"
    ARDRA = "Ardra"
    PUNARVASU = "Punarvasu"
    PUSHYA = "Pushya"
    ASHLESHA = "Ashlesha"
    MAGHA = "Magha"
    PURVA_PHALGUNI = "Purva Phalguni"
    UTTARA_PHALGUNI = "Uttara Phalguni"
    HASTA = "Hasta"
    CHITRA = "Chitra"
    SWATI = "Swati"
    VISHAKHA = "Vishakha"
    ANURADHA = "Anuradha"
    JYESHTHA = "Jyeshtha"
    MULA = "Mula"
    PURVA_ASHADHA = "Purva Ashadha"
    UTTARA_ASHADHA = "Uttara Ashadha"
    SHRAVANA = "Shravana"
    DHANISHTHA = "Dhanishtha"
    SHATABHISHA = "Shatabhisha"
    PURVA_BHADRAPADA = "Purva Bhadrapada"
    UTTARA_BHADRAPADA = "Uttara Bhadrapada"
    REVATI = "Revati"


class Dignity(str, Enum):
    EXALTED = "exalted"
    MOOLATRIKONA = "moolatrikona"
    OWN = "own"
    FRIEND = "friend"
    NEUTRAL = "neutral"
    ENEMY = "enemy"
    DEBILITATED = "debilitated"


class NodeType(str, Enum):
    MEAN = "mean"
    TRUE = "true"


class Ayanamsa(str, Enum):
    LAHIRI = "lahiri"
    KRISHNAMURTI = "krishnamurti"
    RAMAN = "raman"


class HouseSystem(str, Enum):
    WHOLE_SIGN = "whole_sign"
    PLACIDUS = "placidus"
