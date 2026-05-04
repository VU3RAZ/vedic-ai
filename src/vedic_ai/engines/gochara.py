"""Gochara (transit) analysis engine.

Rules sourced from:
  - BPHS (Brihat Parashara Hora Shastra), Ch. 85–87
  - Phaladeepika Ch. 26 (Mantreswara)
  - Graha and Bhava Balas — B.V. Raman
  - Jaimini Sutras — supplementary Rashi drishti transits
  - Sarvartha Chintamani — classical corroborations

Reference frame: Gochara effects are evaluated from the natal Moon sign (Janma
Rashi) as primary reference and from the Ascendant (Lagna) as secondary.

Key concepts:
  - Vedha (obstruction): certain house positions neutralise the Gochara result
  - Sadhe Sati: Saturn transiting 12th, 1st, 2nd from natal Moon (7.5 years)
  - Ashtama Shani: Saturn transiting 8th from natal Moon (2.5 years)
  - Kantaka Shani: Saturn transiting 4th from natal Moon
  - Guru Chandala: Jupiter+Rahu conjunction in transit
  - Dasha lord transit strength: transit of active dasha lord amplifies results
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from vedic_ai.domain.chart import ChartBundle, TransitSnapshot
from vedic_ai.domain.enums import Graha
from vedic_ai.engines.vimshottari import compute_antardasha_periods, compute_vimshottari_dashas

# ---------------------------------------------------------------------------
# Gochara effect tables  (house counted from Janma Rashi = natal Moon sign)
# ---------------------------------------------------------------------------

# Format: dict[graha_name][house_1_to_12] = (result_key, short_effect, detail)
# result_key: "favorable" | "unfavorable" | "mixed" | "neutral"

_GOCHARA_EFFECTS: dict[str, list[tuple[str, str, str]]] = {
    "Sun": [
        # H1
        ("unfavorable", "Bodily affliction, fever",
         "Sun transiting Janma Rashi (1st from Moon): ill health, separation from family, "
         "fear of king/authority. Physical vitality is low. BPHS 85.3"),
        # H2
        ("unfavorable", "Financial loss, eye trouble",
         "Loss of wealth and prestige, eye/speech problems, quarrels with family. "
         "Avoid speculation. BPHS 85.4"),
        # H3
        ("favorable", "Gains, victory, courage",
         "Success in efforts, gain of wealth, victory over enemies, courage and boldness. "
         "Good for communication and travel. BPHS 85.5"),
        # H4
        ("unfavorable", "Mental distress, travel",
         "Unhappiness at home, forced travel, mental agitation, trouble with mother. "
         "Domestic peace disturbed. BPHS 85.6"),
        # H5
        ("unfavorable", "Children trouble, anxiety",
         "Trouble to children, loss of discrimination, mental anguish, poor judgment. "
         "Not good for speculative activities. BPHS 85.7"),
        # H6
        ("favorable", "Victory, health recovery",
         "Victory over enemies and disease, recovery of health, gains from competition. "
         "Favorable for litigation. BPHS 85.8"),
        # H7
        ("unfavorable", "Travel, conflict",
         "Bodily trouble, loss in partnership, travel away from home, eye problems. "
         "Conflict with spouse. BPHS 85.9"),
        # H8
        ("unfavorable", "Fear, disease, loss",
         "Fear, disease, accidents, obstacles in every sphere. Major inauspicious period. "
         "Avoid risky activities. BPHS 85.10"),
        # H9
        ("unfavorable", "Obstacles to fortune",
         "Father's ill health, obstacles to fortune and religion, lack of divine grace. "
         "Pilgrimage becomes difficult. BPHS 85.11"),
        # H10
        ("favorable", "Career success, fame",
         "Success in profession, honor from superiors, government favor, achievement of goals. "
         "Excellent for career matters. BPHS 85.12"),
        # H11
        ("favorable", "Gains, fulfillment",
         "Gain of wealth, recovery from illness, fulfillment of desires. "
         "Best transit position for Sun. BPHS 85.13"),
        # H12
        ("unfavorable", "Expenses, eye trouble",
         "Unnecessary expenses, eye afflictions, separation from family, defeat. "
         "Avoid important beginnings. BPHS 85.14"),
    ],
    "Moon": [
        # H1 — Moon in own Janma Rashi is generally auspicious per Raman
        ("favorable", "Gains, happiness",
         "Moon transiting Janma Rashi: health and happiness, success in undertakings, "
         "gains from multiple sources. Phaladeepika 26.2"),
        # H2
        ("unfavorable", "Family troubles, expenses",
         "Loss of domestic happiness, expenses increase, family disputes, "
         "speech problems. Avoid family confrontations. Phaladeepika 26.3"),
        # H3
        ("favorable", "Courage, success",
         "Happiness, success in travels, courage, gains from efforts, "
         "good health and vitality. BPHS 86.4"),
        # H4
        ("favorable", "Home happiness, conveyance",
         "Domestic peace, happiness from mother, conveyance, emotional fulfillment. "
         "Good for property matters. BPHS 86.5"),
        # H5
        ("mixed", "Mental activity, children",
         "Mental happiness but possible trouble with children. Creative inspiration active. "
         "Mixed results overall. BPHS 86.6"),
        # H6
        ("unfavorable", "Disease, enmity",
         "Ill health, enmity, mental distress, trouble from enemies and thieves. "
         "Avoid confrontations. BPHS 86.7"),
        # H7
        ("unfavorable", "Partnership trouble",
         "Trouble with spouse/partner, bodily afflictions, loss in trade, "
         "separation or disputes. BPHS 86.8"),
        # H8
        ("unfavorable", "Obstacles, ill health",
         "Fear, disease, obstacles in all spheres, mental depression, accidents. "
         "Highly inauspicious. BPHS 86.9"),
        # H9
        ("favorable", "Fortune, gains",
         "Good luck, fortune, religious activities, gains, happiness from father. "
         "Auspicious for worship. BPHS 86.10"),
        # H10
        ("favorable", "Career success, fame",
         "Fame, success in career, name and reputation, achievements recognized. "
         "Favorable for professional matters. BPHS 86.11"),
        # H11
        ("favorable", "Gains, all desires fulfilled",
         "Gain of wealth, recovery of health, fulfillment of all desires. "
         "Excellent transit for Moon. BPHS 86.12"),
        # H12
        ("unfavorable", "Expenses, troubles",
         "Heavy expenses, foreign travel, mental disturbances, loss of sleep. "
         "Spiritual activities give solace. BPHS 86.13"),
    ],
    "Mars": [
        # H1
        ("unfavorable", "Ill health, accidents",
         "Mars transiting 1st from Moon: physical ailments, fever, conflicts, accidents. "
         "Risk of violence. BPHS 85.15"),
        # H2
        ("unfavorable", "Financial disputes",
         "Financial loss, disputes over money, trouble to family, speech aggression. "
         "Avoid financial risks. BPHS 85.16"),
        # H3
        ("favorable", "Courage, gains, victory",
         "Boldness, success in efforts, gains from travels, victory over enemies. "
         "Excellent position for Mars. BPHS 85.17"),
        # H4
        ("unfavorable", "Domestic strife",
         "Domestic quarrels, trouble to mother, property disputes, mental anguish. "
         "Avoid real estate transactions. BPHS 85.18"),
        # H5
        ("unfavorable", "Children trouble, losses",
         "Trouble to children, poor judgment, losses through speculation, mental distress. "
         "Avoid gambling. BPHS 85.19"),
        # H6
        ("favorable", "Victory, good health",
         "Victory over enemies, recovery from illness, success in competition, "
         "triumph in litigation. BPHS 85.20"),
        # H7
        ("unfavorable", "Partner trouble, travel",
         "Conflicts with spouse, trouble in partnerships, enforced travel, "
         "accidents during journeys. BPHS 85.21"),
        # H8
        ("unfavorable", "Accidents, surgery",
         "Accidents, surgery risk, blood-related ailments, major obstacles. "
         "Highly unfavorable. BPHS 85.22"),
        # H9
        ("unfavorable", "Father's trouble, misfortune",
         "Father's ill health, obstacles to fortune, religious conflicts, "
         "lack of divine grace. BPHS 85.23"),
        # H10
        ("favorable", "Efforts bear fruit",
         "Success in career through persistent effort, recognition, gains from profession. "
         "Good for competitive fields. BPHS 85.24"),
        # H11
        ("favorable", "Gains, strength, success",
         "Financial gains, physical strength, success in all undertakings, "
         "victory in competition. BPHS 85.25"),
        # H12
        ("unfavorable", "Expenses, injuries",
         "Unnecessary expenses, injury risk, losses in foreign places, legal disputes. "
         "BPHS 85.26"),
    ],
    "Mercury": [
        # H1
        ("favorable", "Intelligence, good health",
         "Mercury transiting 1st from Moon: good health, sharp intellect, gains, "
         "happiness. Communication skills enhanced. BPHS 85.27"),
        # H2
        ("favorable", "Financial gains, learning",
         "Increase in wealth through education/trade, eloquence, family happiness. "
         "Good for business negotiations. BPHS 85.28"),
        # H3
        ("unfavorable", "Obstacles, mental stress",
         "Mental stress, obstacles in communication, unfavorable travels, "
         "disputes with siblings. BPHS 85.29"),
        # H4
        ("favorable", "Home happiness, conveyance",
         "Domestic happiness, acquisition of conveyance/property, maternal happiness. "
         "Good for education matters. BPHS 85.30"),
        # H5
        ("favorable", "Intelligence, creative gains",
         "Enhanced intelligence, gains through speculation/creativity, children's progress, "
         "mantra siddhi. BPHS 85.31"),
        # H6
        ("unfavorable", "Disputes, health concerns",
         "Health disputes, conflicts with colleagues, legal complications, "
         "digestive ailments. BPHS 85.32"),
        # H7
        ("favorable", "Travel gains, partnership",
         "Gains through travel, successful partnerships, communication with distant people. "
         "Good for trade. BPHS 85.33"),
        # H8
        ("unfavorable", "Obstacles, loss",
         "Obstacles, loss through dishonesty, chronic illness, mental afflictions. "
         "BPHS 85.34"),
        # H9
        ("favorable", "Wealth, fortune",
         "Good fortune, wealth through dharmic means, religious/philosophical learning, "
         "father's wellbeing. BPHS 85.35"),
        # H10
        ("favorable", "Career success, intelligence",
         "Success in profession through intellect, recognition for skills, "
         "government connections. BPHS 85.36"),
        # H11
        ("favorable", "Gains, happiness",
         "Gains of wealth and happiness, fulfillment of desires, favorable communications. "
         "BPHS 85.37"),
        # H12
        ("unfavorable", "Expenses, obstacles",
         "Expenses increase, obstacles in communication, losses through deceit. "
         "Spiritual learning gives benefit. BPHS 85.38"),
    ],
    "Jupiter": [
        # H1
        ("unfavorable", "Financial loss, family trouble",
         "Jupiter transiting 1st from Moon: financial loss, family trouble, ill health. "
         "Known as 'Janma Guru' — unfavorable. BPHS 85.39"),
        # H2
        ("favorable", "Gains, wealth, happiness",
         "Gain of wealth, family happiness, good food, eloquence. "
         "Acquisition of property. BPHS 85.40"),
        # H3
        ("unfavorable", "Loss, debility, obstacles",
         "Physical debility, loss, obstacles in efforts, trouble to siblings. "
         "BPHS 85.41"),
        # H4
        ("unfavorable", "Home trouble, loss",
         "Trouble at home, loss of comforts, mother's health affected, "
         "property disputes. BPHS 85.42"),
        # H5
        ("favorable", "Children, wisdom, gains",
         "Birth of children, gains, wisdom, happiness, creative fulfillment. "
         "Very auspicious. BPHS 85.43"),
        # H6
        ("unfavorable", "Enemies, health loss",
         "Financial loss, enemies gain strength, health deterioration. "
         "Avoid confrontations. BPHS 85.44"),
        # H7
        ("favorable", "Happiness, marriage gains",
         "Marital happiness, partnership gains, travels, public recognition. "
         "Good for marriage/relationships. BPHS 85.45"),
        # H8
        ("unfavorable", "Obstacles, illness, loss",
         "Major obstacles, serious illness possible, financial setbacks. "
         "Ashtama Guru — highly unfavorable. BPHS 85.46"),
        # H9
        ("favorable", "Fortune, religious gains",
         "Excellent fortune, religious activities, wisdom, gains from father, "
         "spiritual progress. BPHS 85.47"),
        # H10
        ("favorable", "Career success, fame",
         "Career advancement, fame, recognition from government/authority, "
         "professional success. BPHS 85.48"),
        # H11
        ("favorable", "All desires fulfilled",
         "Fulfillment of all desires, immense gains, happiness in every sphere. "
         "BEST transit position for Jupiter. BPHS 85.49"),
        # H12
        ("unfavorable", "Expenses, separation",
         "Heavy expenses, separation from family, loss, foreign travel. "
         "Spiritual liberation possible. BPHS 85.50"),
    ],
    "Venus": [
        # H1
        ("favorable", "Happiness, gains, pleasures",
         "Venus transiting 1st from Moon: happiness, sensual pleasures, gains, "
         "good health. Romantic opportunities. BPHS 85.51"),
        # H2
        ("favorable", "Wealth, domestic happiness",
         "Acquisition of wealth, good food, domestic happiness, romantic pleasures. "
         "Financial gains. BPHS 85.52"),
        # H3
        ("unfavorable", "Loss, travel, obstacles",
         "Loss of comforts, unnecessary travel, obstacles in undertakings. "
         "BPHS 85.53"),
        # H4
        ("favorable", "Conveyance, home happiness",
         "Acquisition of conveyance/jewels, domestic happiness, maternal gains. "
         "Good for property. BPHS 85.54"),
        # H5
        ("favorable", "Progeny, happiness",
         "Gains through children, romantic happiness, creative pleasures. "
         "Good for arts and entertainment. BPHS 85.55"),
        # H6
        ("unfavorable", "Enmity, loss",
         "Enmity from women, health problems of a sensual nature, financial loss. "
         "BPHS 85.56"),
        # H7
        ("favorable", "Partnership, pleasures",
         "Romantic fulfillment, marital happiness, partnership gains, pleasures. "
         "Best position for Venus. BPHS 85.57"),
        # H8
        ("unfavorable", "Obstacles, loss",
         "Loss of comforts, obstacles, health issues, domestic strife. "
         "BPHS 85.58"),
        # H9
        ("favorable", "Worship, fortune, gains",
         "Religious activities, fortune, gains from father, pilgrimage. "
         "BPHS 85.59"),
        # H10
        ("favorable", "Gains, success, pleasure",
         "Gains in profession, success, pleasures from profession. "
         "Career advancement. BPHS 85.60"),
        # H11
        ("favorable", "Happiness, gains, pleasures",
         "Gains of all kinds, happiness, sensual pleasures, fulfillment of desires. "
         "BPHS 85.61"),
        # H12
        ("mixed", "Pleasures, expenses",
         "Sensual pleasures but with expenses. Gains in foreign lands. "
         "Mixed results. BPHS 85.62"),
    ],
    "Saturn": [
        # H1 — Sadhe Sati middle (peak)
        ("unfavorable", "Physical trouble, Sadhe Sati peak",
         "Saturn transiting 1st from Moon (Janma Shani / Sadhe Sati peak): "
         "physical afflictions, career obstacles, mental anguish, loss of property. "
         "Most intense phase of Sadhe Sati. BPHS 85.63"),
        # H2 — Sadhe Sati entering last phase
        ("unfavorable", "Wealth loss, family trouble",
         "Loss of wealth, family disputes, speech troubles, separation from family. "
         "Third phase of Sadhe Sati begins. BPHS 85.64"),
        # H3
        ("favorable", "Gains, success, courage",
         "Financial gains, victory over enemies, courage, success. "
         "Best Saturn transit. BPHS 85.65"),
        # H4
        ("unfavorable", "Domestic troubles, Kantaka",
         "Kantaka Shani: domestic quarrels, loss of property/conveyance, "
         "mother's health affected, mental anguish. BPHS 85.66"),
        # H5
        ("unfavorable", "Children trouble, mental distress",
         "Loss of children's happiness, poor judgment, mental distress, "
         "speculation losses. BPHS 85.67"),
        # H6
        ("favorable", "Victory, career gains",
         "Victory over enemies, recovery of debts, good health, gains. "
         "Favorable for service/competition. BPHS 85.68"),
        # H7
        ("unfavorable", "Partner trouble, travel",
         "Trouble in marriage/partnerships, enforced travel, bodily afflictions. "
         "BPHS 85.69"),
        # H8 — Ashtama Shani
        ("unfavorable", "Major obstacles — Ashtama Shani",
         "Ashtama Shani: very difficult transit. Accidents, chronic disease, "
         "financial loss, disgrace, danger to life. Highly inauspicious. BPHS 85.70"),
        # H9
        ("unfavorable", "Loss of fortune, father's trouble",
         "Obstacles to fortune, father's health at risk, religious obstacles, "
         "lack of divine grace. BPHS 85.71"),
        # H10
        ("unfavorable", "Career obstacles, loss of fame",
         "Obstacles in profession, loss of reputation, conflict with superiors. "
         "Perseverance required. BPHS 85.72"),
        # H11
        ("favorable", "Gains, fulfillment",
         "Financial gains, success, health improvement, fulfillment of desires. "
         "Second best Saturn transit after H3. BPHS 85.73"),
        # H12 — Sadhe Sati first phase begins
        ("unfavorable", "Expenses, Sadhe Sati onset",
         "Sadhe Sati first phase: heavy expenses, foreign travel, disturbed sleep, "
         "hidden troubles beginning. BPHS 85.74"),
    ],
    "Rahu": [
        # H1
        ("unfavorable", "Restlessness, health issues",
         "Rahu transiting 1st from Moon: mental restlessness, health troubles, "
         "deception, new but disruptive beginnings. Sarvartha Chintamani 12.1"),
        # H2
        ("unfavorable", "Financial instability, disputes",
         "Financial irregularities, family disputes, speech problems, "
         "deceit in monetary matters. Sarvartha Chintamani 12.2"),
        # H3
        ("favorable", "Courage, gains, travel",
         "Boldness, gains through travel, success, networking with influential people. "
         "Sarvartha Chintamani 12.3"),
        # H4
        ("unfavorable", "Domestic disruption",
         "Domestic troubles, unexpected relocation, vehicle problems, "
         "trouble with mother. Sarvartha Chintamani 12.4"),
        # H5
        ("unfavorable", "Children trouble, speculation",
         "Trouble with children, speculative losses, mental confusion. "
         "Avoid gambling. Sarvartha Chintamani 12.5"),
        # H6
        ("favorable", "Victory over enemies",
         "Victory over enemies through clever means, success in competition, "
         "good for political/social rivalry. Sarvartha Chintamani 12.6"),
        # H7
        ("unfavorable", "Partnership issues",
         "Deceptive partnerships, marital confusion, foreign travel issues. "
         "Sarvartha Chintamani 12.7"),
        # H8
        ("mixed", "Transformation, occult gains",
         "Major life transformations, occult interests, inheritance possible "
         "but with upheaval. Sarvartha Chintamani 12.8"),
        # H9
        ("mixed", "Unconventional beliefs, travel",
         "Foreign travel, unorthodox spiritual paths, gains through foreign connections. "
         "Sarvartha Chintamani 12.9"),
        # H10
        ("mixed", "Career disruptions, ambitions",
         "Ambitious career moves, unconventional path, sudden changes in profession. "
         "Sarvartha Chintamani 12.10"),
        # H11
        ("favorable", "Gains, networking",
         "Financial gains through networks, fulfillment through unconventional means. "
         "Sarvartha Chintamani 12.11"),
        # H12
        ("mixed", "Foreign, spiritual, liberation",
         "Foreign connections, spiritual liberation, hidden expenses. "
         "Sarvartha Chintamani 12.12"),
    ],
    "Ketu": [
        # H1
        ("unfavorable", "Health, spiritual unrest",
         "Ketu transiting 1st from Moon: physical ailments, spiritual restlessness, "
         "separation tendencies. Sarvartha Chintamani 13.1"),
        # H2
        ("unfavorable", "Financial instability",
         "Financial uncertainty, family separations, speech becomes sparse. "
         "Sarvartha Chintamani 13.2"),
        # H3
        ("favorable", "Success, travel, courage",
         "Success in efforts, favorable travels, courage through inner wisdom. "
         "Sarvartha Chintamani 13.3"),
        # H4
        ("unfavorable", "Domestic changes",
         "Domestic disruptions, change of residence, vehicle problems, "
         "separation from mother. Sarvartha Chintamani 13.4"),
        # H5
        ("unfavorable", "Children trouble, past karma",
         "Trouble through children, past karma surfaces, poor speculation results. "
         "Sarvartha Chintamani 13.5"),
        # H6
        ("favorable", "Victory, health improvement",
         "Victory over enemies and disease, improvement in health matters. "
         "Sarvartha Chintamani 13.6"),
        # H7
        ("unfavorable", "Partnership strife",
         "Partnership and marital difficulties, spiritual awakening through relationships. "
         "Sarvartha Chintamani 13.7"),
        # H8
        ("mixed", "Transformation, moksha",
         "Deep transformations, near-death experiences possible, spiritual liberation. "
         "Sarvartha Chintamani 13.8"),
        # H9
        ("mixed", "Spiritual wisdom, father",
         "Spiritual insights, unconventional beliefs, father's health variable. "
         "Sarvartha Chintamani 13.9"),
        # H10
        ("unfavorable", "Career disruptions",
         "Career interruptions, spiritual path over material success. "
         "Sarvartha Chintamani 13.10"),
        # H11
        ("mixed", "Gains with detachment",
         "Material gains with inner detachment, fulfillment through spiritual means. "
         "Sarvartha Chintamani 13.11"),
        # H12
        ("favorable", "Liberation, spiritual gains",
         "Moksha tendencies, foreign residence, spiritual liberation. "
         "Ketu is at home in the 12th. Sarvartha Chintamani 13.12"),
    ],
}

# ---------------------------------------------------------------------------
# Vedha (obstruction) table
# ---------------------------------------------------------------------------
# Format: {transit_house: vedha_house}  — applies from Janma Rashi perspective
# If a planet other than Sun/Moon occupies the Vedha house, the good transit
# result is neutralized. Exception: Sun and Moon do not cause Vedha to each other.
# Source: BPHS Ch. 87, Phaladeepika Ch. 26

_VEDHA_TABLE: dict[int, int] = {
    1:  8,
    2:  5,
    3:  9,
    4: 10,
    6: 12,
    7:  2,
    10: 4,
    11: 8,
}

# Houses where results are considered FAVORABLE for Vedha checking
_FAVORABLE_HOUSES: set[int] = {1, 3, 6, 10, 11}
# (unfavorable houses have no Vedha since obstruction only matters for good results)

# ---------------------------------------------------------------------------
# Dasha lord Gochara amplifier
# ---------------------------------------------------------------------------

_DASHA_AMPLIFY_FAVORABLE = (
    "Active dasha lord transiting a favorable house amplifies positive results "
    "significantly. The dasha-transit synchrony is a powerful timing indicator."
)
_DASHA_AMPLIFY_UNFAVORABLE = (
    "Active dasha lord transiting an unfavorable house intensifies negative effects. "
    "Caution advised during this period."
)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GrahaTransitResult:
    graha: str
    transit_sign: str
    transit_house_from_moon: int
    transit_house_from_lagna: int
    natal_sign: str
    natal_house: int
    result_key: str         # "favorable" | "unfavorable" | "mixed" | "neutral"
    short_effect: str
    detail: str
    vedha_active: bool
    vedha_planet: Optional[str]
    is_retrograde: bool
    is_dasha_lord: bool
    is_antardasha_lord: bool


@dataclass
class SadheSatiInfo:
    active: bool
    phase: str              # "onset" | "peak" | "exit" | ""
    description: str
    saturn_house_from_moon: int


@dataclass
class SpecialTransitAlert:
    name: str
    severity: str           # "warning" | "alert" | "info"
    description: str


# ---------------------------------------------------------------------------
# Remedy data tables  (classical, cited sources)
# ---------------------------------------------------------------------------
# Primary textual sources used throughout:
#
# BPHS    — Brihat Parashara Hora Shastra (Maharishi Parashara, compiled c. 200–1400 CE)
#           Ch. 88 "Graha Shanti Adhyaya" — planetary pacification through mantra, dana, homa
# MM      — Mantra Mahodadhi (Mahidhara, 16th c. CE) — authoritative source for beeja mantras
# Saravali — Saravali (Kalyana Varma, c. 800 CE) — planet natures & significations
# JP      — Jataka Parijata (Vaidyanatha Dikshita, 15th c. CE) — classical natal astrology
# BS      — Brihat Samhita (Varahamihira, 505–587 CE) — gems & electional astrology
# AP      — Agni Purana, Ch. 246 — Ratnapariksha (examination of gems)
# GP      — Garuda Purana, Ch. 68–70 — gem quality & planetary associations
# SP      — Skanda Purana — various Kavachams & Stotras
# BP      — Brahma Purana — Navagraha Stotras, Kavachams
# MP      — Markandeya Purana, Ch. 81–93 — Devi Mahatmya / Durga Saptashati
# VR      — Valmiki Ramayana — Aditya Hridayam (Yuddha Kanda, Ch. 107)
# RV      — Rigveda — primary Vedic hymns
# YV      — Yajurveda, Taittiriya Samhita
# AV      — Atharvaveda Parishishta — Ganesha Atharvashirsha
# MB      — Mahabharata, Anushasana Parva, Ch. 149 — Vishnu Sahasranama
# LK      — Lal Kitab (Pt. Roop Chand Joshi, 1939–1952 eds.) — practical upaya system
# SC      — Sarvartha Chintamani (Venkatesha Daivagna, c. 1500 CE)
# ---------------------------------------------------------------------------

# Beeja (seed) mantras — Mantra Mahodadhi (Mahidhara, 16th c.), Ch. 3–11
# Recite 108× on the planet's weekday, ideally at the planet's hora
_PLANET_BEEJA_MANTRA: dict[str, str] = {
    "Sun":     "Om Hraam Hreem Hraum Sah Suryaya Namah",
    "Moon":    "Om Shraam Shreem Shraum Sah Chandramase Namah",
    "Mars":    "Om Kraam Kreem Kraum Sah Bhaumaya Namah",
    "Mercury": "Om Braam Breem Braum Sah Budhaya Namah",
    "Jupiter": "Om Graam Greem Graum Sah Gurave Namah",
    "Venus":   "Om Draam Dreem Draum Sah Shukraya Namah",
    "Saturn":  "Om Praam Preem Praum Sah Shanaischaraya Namah",
    "Rahu":    "Om Bhraam Bhreem Bhraum Sah Rahave Namah",
    "Ketu":    "Om Shraam Shreem Shraum Sah Ketave Namah",
}

# Source citation for each beeja mantra
_PLANET_MANTRA_SOURCE: dict[str, str] = {
    "Sun":     "Mantra Mahodadhi Ch.3 (Mahidhara, 16th c.); corroborated in Navagraha Stotra (attr. Vyasa, BP)",
    "Moon":    "Mantra Mahodadhi Ch.4 (Mahidhara); Chandra Namaskara, Skanda Purana",
    "Mars":    "Mantra Mahodadhi Ch.5 (Mahidhara); Mangal Stotra, Skanda Purana Avantya Khanda",
    "Mercury": "Mantra Mahodadhi Ch.6 (Mahidhara); Budh Kavacham, Brahma Purana Ch.28",
    "Jupiter": "Mantra Mahodadhi Ch.7 (Mahidhara); Brihaspati Stotra, Brahma Purana Ch.29",
    "Venus":   "Mantra Mahodadhi Ch.8 (Mahidhara); Shukra Kavacham, Brahma Purana",
    "Saturn":  "Mantra Mahodadhi Ch.9 (Mahidhara); Shani Ashtottara, Skanda Purana; YV Taittiriya Samhita",
    "Rahu":    "Mantra Mahodadhi Ch.10 (Mahidhara); Rahu Kavacham, Brahma Purana Ch.32",
    "Ketu":    "Mantra Mahodadhi Ch.11 (Mahidhara); Ketu Kavacham, Brahma Purana Ch.33",
}

# Vedic root mantra for each planet (Navagraha Suktam / Rigveda / Yajurveda)
_PLANET_VEDIC_MANTRA: dict[str, str] = {
    "Sun":
        "Rigveda 1.50.1: 'Ud u tyam jatavedasam devam vahanti ketavah / "
        "drse vishvaya suryam' — the rising Sun carrying away darkness",
    "Moon":
        "Rigveda 1.91.16 (Soma Sukta): 'Soma rajanno sham no bhava / "
        "dvipade sham catushpade' — O Soma, be auspicious to all",
    "Mars":
        "Yajurveda, Taittiriya Samhita 1.2.1 (Rudra Namakam): "
        "'Namo hiranyabahave senanye disham ca pataye namo' — Mars = Rudra-fire",
    "Mercury":
        "Rigveda 1.22.6 (Saraswati / Vishnu hymn): Budha rules intellect; "
        "recite Rigveda 4.50 (Brihaspati Sukta) for combined Mercury-Jupiter grace",
    "Jupiter":
        "Rigveda 4.50.1 (Brihaspati Sukta): 'A tat te brihaspate "
        "mahimam vardhayamasi' — we extol your greatness, O Brihaspati",
    "Venus":
        "Rigveda Khila 5.87 (Shri Sukta): 'Hiranya varnam harinim / "
        "suvarna rajata srajam' — Lakshmi golden in hue, bearer of garlands",
    "Saturn":
        "Rigveda 10.90 / Yajurveda Taittiriya Brahmana 3.1.2.1: "
        "'Sham no devir abhishtaya apo bhavantu pitaye' — "
        "may the divine waters bring us peace (Saturn = Yama / discipline)",
    "Rahu":
        "Atharvaveda 19.9 (Nakshatra Sukta): Rahu governs Ardra/Swati/Shatabhisha; "
        "recite AV 19.9 on these nakshatra days for Rahu pacification",
    "Ketu":
        "Atharvaveda Parishishta (Ganesha Atharvashirsha): 'Tvam eva pratyaksham "
        "tatvam asi' — Ketu's moksha nature invoked through Ganesha's omniscient form",
}

# Stotra: full name, text, author, and source
_PLANET_STOTRA: dict[str, str] = {
    "Sun":
        "Aditya Hridayam — Valmiki Ramayana, Yuddha Kanda Ch.107 v.1–29 "
        "(sage Agastya taught this to Rama before battle with Ravana). "
        "29 verses; recite at sunrise. Also: Surya Ashtakam (Vyasa).",
    "Moon":
        "Chandra Kavacham — Brahma Purana Ch.30; "
        "Shri Sukta — Rigveda Khila 5.87 (15 verses, one of the oldest Devi hymns); "
        "Chandra Ashtottara Shatanama — 108 names of Moon (SP).",
    "Mars":
        "Hanuman Chalisa — Goswami Tulsidas (1532–1623 CE), 40 chaupais; "
        "Mangal Stotra — Skanda Purana, Avantya Khanda; "
        "Karthikeya Kavacham — SP, Kumara Khanda.",
    "Mercury":
        "Vishnu Sahasranama — Mahabharata, Anushasana Parva Ch.149 (Bhishma to Yudhishthira); "
        "Budh Stotra — Brahma Purana Ch.28; "
        "Budh Ashtottara — 108 names of Mercury.",
    "Jupiter":
        "Brihaspati Kavacham — Brahma Purana Ch.29; "
        "Guru Stotra — Skanda Purana; "
        "Dakshinamurti Stotra — Adi Shankaracharya (8th c. CE) — Jupiter as Guru principle.",
    "Venus":
        "Shri Sukta — Rigveda Khila 5.87 (Lakshmi = Venus); "
        "Shukra Kavacham — Brahma Purana; "
        "Lakshmi Ashtottara Shatanama — Vishnu Purana Book 1 Ch.9.",
    "Saturn":
        "Dasaratha Shani Stotra — traditionally attributed to King Dasaratha "
        "(Ramayana period; opens 'Konastha Pingalo Babhru…'); "
        "Shani Chalisa — Hira Singh Chauhan (17th–18th c. CE), 40 chaupais; "
        "Nilanjana Samabhasam — Brahma Purana Graha Stuti v.1 "
        "('Nilanjana samabhasam raviputram yamagrajam…'); "
        "Hanuman Chalisa (Tulsidas) — recite daily; Hanuman subdues Saturn.",
    "Rahu":
        "Rahu Kavacham — Brahma Purana Ch.32; "
        "Durga Saptashati (Devi Mahatmya) — Markandeya Purana Ch.81–93, 700 verses; "
        "recite during Rahu Kalam on Saturdays.",
    "Ketu":
        "Ganesha Atharvashirsha — Atharva Veda Parishishta (c. 800–1200 CE); "
        "Ketu Kavacham — Brahma Purana Ch.33; "
        "Ketu Stotra — 'Palasa pushpa sankasham…' (BP Graha Stuti).",
}

# Charity items with BPHS Ch.88 verse reference
# BPHS Ch.88 "Graha Shanti Adhyaya" — Parashara specifies dana items per graha
_PLANET_CHARITY: dict[str, str] = {
    "Sun":
        "Wheat (godhuma), red cloth (rakta vastra), copper vessel (tamra patra), "
        "jaggery (guda), red flowers, gold (if possible) — donate Sunday morning "
        "[BPHS 88.5–8: 'Gauradanam taramgaunam suryasya shantaye…']",
    "Moon":
        "White rice (shali), cow's milk, conch shell (shankha), silver (rajata), "
        "white cloth, white flowers, camphor — donate Monday evening "
        "[BPHS 88.9–12: 'Chandrasya shantaye dadyat shvetam vastra rajatam…']",
    "Mars":
        "Red lentils (masoor dal), red cloth, copper (tamra), jaggery, "
        "red sandalwood (raktachandan), coral substitute — donate Tuesday "
        "[BPHS 88.13–16: 'Kuje pida bhave tasya raktavastra pradiyate…']",
    "Mercury":
        "Green moong dal, green cloth (harita vastra), books/pen to students, "
        "emerald substitute (green tourmaline), bronze vessel — Wednesday "
        "[BPHS 88.17–20: 'Buddhasya shantaye hyeta haritam vastra sarsapa…']",
    "Jupiter":
        "Yellow chickpeas (chana dal), turmeric (haridra), yellow cloth, "
        "gold or yellow sapphire substitute, banana (kadali phala), "
        "Brahmin dakshina — Thursday morning "
        "[BPHS 88.21–24: 'Guroh prasade sarvasya pitam vastra suvarnam…']",
    "Venus":
        "White rice, pure ghee (go ghrita), white cloth (shveta vastra), "
        "fragrance (sugandha), white flowers (shveta pushpa), "
        "white horse substitute (silver horse figure) — Friday "
        "[BPHS 88.25–28: 'Shukrasya shantikamena shvetam vastra ghritam…']",
    "Saturn":
        "Black sesame (krishna tila), mustard oil (sarshapa taila), "
        "black cloth (krishna vastra), iron vessel (ayah patra), "
        "dark blanket to a poor labourer — Saturday at dusk "
        "[BPHS 88.29–32: 'Shanaischarasya shantaye krishnanam tila dadyat…']",
    "Rahu":
        "Black sesame, urad dal (masha), dark blue cloth (nila vastra), "
        "coconut (narikela), lead (sisa) — Saturday during Rahu Kalam "
        "[BPHS 88.33–35: 'Rahoh shantim ichanto nila vastra pradiyate…']",
    "Ketu":
        "Multi-coloured cloth (chitravarna vastra), mixed sesame, iron, "
        "spotted blanket (chitrambara) — Tuesday "
        "[BPHS 88.36–38: 'Ketoh shantim dadati citravastra pradiyate…']",
}

# Fasting protocol with textual grounding
_PLANET_FAST_DAY: dict[str, str] = {
    "Sun":
        "Sunday (Ravivar Vrat) — consume only fruits and liquids after sunrise; "
        "avoid salt. 12 Sundays' vrat described in Bhavishya Purana, Uttara Parva Ch.45.",
    "Moon":
        "Monday (Somvar Vrat) — fast until moonrise, break with milk/white foods; "
        "Pradosh Vrat (13th tithi, Shiva fast) also pacifies Moon. "
        "Ref: Shiva Purana, Vidyeshvara Samhita Ch.12.",
    "Mars":
        "Tuesday (Mangalvar Vrat) — fast until sunset; avoid non-vegetarian food; "
        "offer red flowers to Hanuman. 21-Tuesday Hanuman Vrat is classical remedy. "
        "Ref: Skanda Purana, Avantya Khanda.",
    "Mercury":
        "Wednesday (Budhvar Vrat) — fast until evening; consume green foods only; "
        "light a green lamp before Vishnu idol. "
        "Ref: Brahma Purana Ch.28; Muhurta Chintamani on Budha Vara.",
    "Jupiter":
        "Thursday (Guruvar Vrat) — avoid non-vegetarian and salt; eat once, "
        "yellow or saffron foods preferred; 16 Thursdays' vrat is prescribed. "
        "Ref: Skanda Purana; Muhurta Chintamani, Vara Nirnaya.",
    "Venus":
        "Friday (Shukravar Vrat) — consume white foods only (milk, rice, yoghurt); "
        "Shodasha Upachara Lakshmi Puja on 16 Fridays is prescribed. "
        "Ref: Skanda Purana, Maheswara Khanda.",
    "Saturn":
        "Saturday (Shanivar Vrat) — consume black sesame or dark grains once at dusk; "
        "no oil massage on Saturday; 19-Saturday Shani Vrat prescribed in Shani Mahatmya "
        "(Skanda Purana, Brahma Khanda, Ch. 2–8).",
    "Rahu":
        "Saturday during Rahu Kalam — partial fast or sunset fast; "
        "Rahu Kalam varies by weekday; consult panchanga for exact timing. "
        "Ref: Muhurta Chintamani, Rahu Kala Nirnaya.",
    "Ketu":
        "Tuesday (shares Mars energy); Ganesha Chaturthi monthly vrat also pacifies Ketu. "
        "Ref: Brahma Purana, Ketu Shanti Vidhi.",
}

# Deity, puja, and temple references
_PLANET_DEITY: dict[str, str] = {
    "Sun":
        "Lord Surya (Aditya) — 12 Adityas (RV 2.27); also Lord Rama (Sun dynasty). "
        "Perform 12 Surya Namaskaras at sunrise facing east. "
        "Visit Surya temple (Konark, Modhera, Martand) if possible. "
        "Offer arghya (water offering) reciting Surya Ashtanama.",
    "Moon":
        "Lord Shiva — Chandra adorns Shiva's crown (Chandrashekhara); also Devi Parvati. "
        "Shiva puja every Monday; Abhisheka with milk on Pradosh tithi (13th). "
        "Chandra temples: Thingalur (Tamil Nadu), Ujjain Mahakal.",
    "Mars":
        "Lord Hanuman (Tuesdays) — Hanuman is the presiding deity for Mars afflictions; "
        "also Lord Karthikeya / Subramanya (Murugan). "
        "Visit Hanuman temple every Tuesday; offer sindur (red), oil, and garland.",
    "Mercury":
        "Lord Vishnu (Mercury rules Vishnu's intellect aspect); also Lord Ganesha. "
        "Recite Vishnu Sahasranama on Wednesdays. "
        "Light green ghee lamp before Vishnu idol on Wednesdays.",
    "Jupiter":
        "Lord Brihaspati / Guru; also Lord Vishnu (Dattatreya aspect) and Sadashiva. "
        "Perform Guru Vandana (bow to teacher) on Thursdays. "
        "Visit Vishnu / Datta temple; offer yellow flowers and bananas.",
    "Venus":
        "Goddess Lakshmi / Goddess Mahalakshmi; also Goddess Saraswati. "
        "Shodashopachara Lakshmi Puja on Fridays. "
        "Offer white/yellow flowers, fragrance (sandalwood paste), and ghee lamp.",
    "Saturn":
        "Lord Shani (son of Surya and Chhaya); also Lord Hanuman and Lord Shiva. "
        "Visit Shani temple (Shingnapur, Thirunallar) on Saturdays. "
        "Offer sesame oil (tailabhisheka) to Shani idol. "
        "Recite Dasaratha Shani Stotra before Shani image.",
    "Rahu":
        "Goddess Durga / Goddess Kali (Rahu = Tamas, subdued by Shakti). "
        "Recite Durga Saptashati (700 verses) during Rahu Kalam on Saturdays. "
        "Visit Kali / Bhairava temple. Offer blue flowers and coconut.",
    "Ketu":
        "Lord Ganesha (elephant head = Ketu's body-less nature); also Lord Bhairava. "
        "Ganesha Puja on Tuesdays and Chaturthi tithi. "
        "Light camphor (karpura) — Ketu = fire of discrimination. "
        "Perform Pitru Tarpan (ancestor rites) to pacify Ketu's karmic dimension.",
}

# Gemstone — Agni Purana, Garuda Purana, Brihat Samhita (Varahamihira)
_PLANET_GEMSTONE: dict[str, str] = {
    "Sun":
        "Ruby (Manikya / Padmaraga) — Agni Purana Ch.246; Garuda Purana Ch.70. "
        "Only if Sun is a functional benefic (lagna/5th lord etc.) for the native's lagna. "
        "Minimum 3 rattis; set in gold; wear on ring finger, Sunday sunrise.",
    "Moon":
        "Natural Pearl (Mukta / Moti) — Garuda Purana Ch.68; Brihat Samhita Ch.80. "
        "Especially helpful during Moon Mahadasha or when Moon is weak / afflicted. "
        "Set in silver; wear on little finger, Monday morning.",
    "Mars":
        "Red Coral (Praval / Moonga) — Agni Purana Ch.246. "
        "Suitable for Mars-friendly lagnas (Aries, Scorpio, Cancer, Leo). "
        "Set in gold or copper; wear on ring finger, Tuesday sunrise.",
    "Mercury":
        "Emerald (Marakata / Panna) — Garuda Purana Ch.69; Brihat Samhita Ch.80 v.21. "
        "Only when Mercury lords a kendra or trikona for the native's lagna. "
        "Set in gold; wear on little finger, Wednesday morning.",
    "Jupiter":
        "Yellow Sapphire (Pushparaga / Pukhraj) — Agni Purana Ch.246 v.7; GP Ch.70. "
        "Generally considered safe; among the most beneficial gems. "
        "Set in gold; wear on index finger, Thursday morning. "
        "Brihat Samhita Ch.80 v.6 on Pushparaga quality and origin.",
    "Venus":
        "Diamond (Vajra / Heera) or White Sapphire (Safed Pukhraj) — AP Ch.246; GP Ch.70. "
        "Set in silver or platinum; wear on middle finger, Friday morning. "
        "Mani Ratna Chandrika (12th–14th c.) details diamond quality grades.",
    "Saturn":
        "Blue Sapphire (Indranila / Neelam) — GP Ch.68; BS Ch.80 v.16. "
        "EXTREME CAUTION: Blue Sapphire is the fastest-acting gem. "
        "Classical rule: test for 72 hours (Shani Sade Sati or Ashtama Shani = avoid). "
        "Only with explicit expert guidance; set in iron/silver; middle finger, Saturday.",
    "Rahu":
        "Hessonite Garnet (Gomed / Gomeda) — AP Ch.246; GP Ch.69. "
        "Beneficial only when Rahu is a functional benefic (Gemini/Virgo lagna etc.). "
        "Set in silver or panchaloha; wear on middle finger, Saturday (Rahu Kalam).",
    "Ketu":
        "Cat's Eye Chrysoberyl (Vaidurya / Lahsunia) — AP Ch.246; GP Ch.70. "
        "Beneficial during Ketu Mahadasha if Ketu lords a favorable house. "
        "Set in silver; wear on little finger, Tuesday morning.",
}

# Behavioral / lifestyle remedies grounded in Saravali, Jataka Parijata, BPHS significations
_PLANET_BEHAVIORAL: dict[str, str] = {
    "Sun":
        "Honour the father, king, and all authority figures — BPHS Ch.3 on Sun's karakatwas. "
        "Offer water (arghya) to the rising Sun daily (Rig. 1.50). "
        "Avoid ego clashes and dishonesty toward superiors. "
        "Lal Kitab (1952): avoid taking things that belong to others; respect governance.",
    "Moon":
        "Honour the mother and all women — BPHS Ch.3 on Moon's karakatwas. "
        "Maintain emotional stability; avoid excessive worry and mood swings. "
        "Keep the home clean and filled with white/silver objects. "
        "Lal Kitab (1939): place a silver coin or piece in pocket for Moon strength.",
    "Mars":
        "Channel physical energy positively — exercise, sports, martial arts (Saravali Ch.5). "
        "Support siblings and younger relatives. "
        "Avoid heated arguments, especially on Tuesdays. "
        "Lal Kitab (1941): plant a red-flowered plant in the house for Mars.",
    "Mercury":
        "Practice truth in speech and business — Mercury = Satya Vakya (honest word). "
        "Help students, young people, and writers (Mercury karakatwas per BPHS Ch.3). "
        "Feed birds (Mercury = avian communication). "
        "Lal Kitab (1952): keep a piece of bronze in the pocket on Wednesdays.",
    "Jupiter":
        "Respect the Guru, elders, priests, and tradition — JP Ch.15 on Jupiter's nature. "
        "Give charity generously on Thursdays (Guru Dakshina). "
        "Avoid pride, excess, and disrespect toward knowledge. "
        "BPHS Ch.3: Jupiter = Dharma; righteous conduct is the primary remedy.",
    "Venus":
        "Respect women, artists, and creative people (Venus karakatwas, BPHS Ch.3). "
        "Maintain personal cleanliness and aesthetic surroundings. "
        "Keep the home fragrant — flowers, sandalwood incense. "
        "Lal Kitab (1939): donate white items to women for Venus strength.",
    "Saturn":
        "Serve the poor, sick, disabled, and elderly sincerely — Saturn = Karma Yoga (Saravali). "
        "Be patient, disciplined, and honest in all dealings. "
        "Avoid shortcuts, deception, and cruelty. "
        "Feed crows (Shani's vahana) black sesame and rice every Saturday. "
        "BPHS Ch.85: Saturn rewards those who accept their karma with equanimity.",
    "Rahu":
        "Avoid intoxicants, illusions, and deceptive behavior (Rahu = Maya). "
        "Be straightforward in foreign dealings and partnerships. "
        "Help foreigners, outcasts, and the marginalised. "
        "Lal Kitab (1952): avoid taking or eating stale/leftover food during Rahu affliction.",
    "Ketu":
        "Practise meditation, pranayama, and spiritual disciplines — Ketu = Moksha Karaka. "
        "Perform Pitru Tarpan (ancestor water-offering) — Ketu = ancestral karma. "
        "Remain detached from material outcomes. "
        "Help the sick and the spiritually seeking (Ketu significations, BPHS Ch.3).",
}

# Severe special-situation remedies with source citations
_SATURN_SADHESATI_REMEDIES = [
    "Perform Shani Shanti Puja (full ritual with Vedic priest) — prescribed in Shani Mahatmya, "
    "Skanda Purana Brahma Khanda Ch.2–8",
    "Recite 'Nilanjana Samabhasam raviputram yamagrajam…' daily — Brahma Purana Graha Stuti v.1",
    "Recite Dasaratha Shani Stotra ('Konastha Pingalo Babhru…') — traditionally attributed to King "
    "Dasaratha; found in regional Puranas and Shani-related compendiums",
    "Recite Hanuman Chalisa every morning — Goswami Tulsidas (1532–1623 CE); Hanuman is held to "
    "protect devotees from Saturn's afflictions (Shani Mahatmya, SP)",
    "Offer sesame oil (tailabhisheka) to Shani idol/Yantra every Saturday — BPHS Ch.88 v.29",
    "Donate black sesame + mustard oil + iron vessel + black blanket to a poor labourer on "
    "Saturdays — BPHS 88.29–32: 'Shanaischarasya shantaye krishnanam tila dadyat…'",
    "Feed crows (Shani's vahana) black sesame mixed rice each Saturday morning — "
    "Shani Mahatmya (SP) and Lal Kitab (1952 ed.)",
    "Wear a 7-faced (Saptamukhi) Rudraksha — represents Mahalakshmi and Saturn's 7-year nature; "
    "energised by 'Om Hreem Namah' — Rudraksha Jabala Upanishad",
    "Perform genuine selfless service (Seva) to the poor and disabled — "
    "Saturn = Karma Yoga; Bhagavad Gita Ch.3 on Nishkama Karma",
    "Maintain strict honesty: Saturn as Yama's brother rewards dharma and punishes adharma — "
    "Saravali Ch.5 (Kalyana Varma, c. 800 CE)",
]

_SATURN_ASHTAMA_REMEDIES = _SATURN_SADHESATI_REMEDIES + [
    "Perform Maha Mrityunjaya Homa — Yajurveda TS 3.60.12: 'Tryambakam yajamahe…'; "
    "most powerful remedy for life-threatening or health-threatening Saturn periods",
    "Obtain a comprehensive medical check-up; keep health insurance and emergency contacts ready "
    "— Ashtama Shani rules chronic illness (BPHS 85.70)",
    "Avoid elective surgery unless critical; if unavoidable, consult Muhurta Chintamani for an "
    "auspicious time and ensure proper surgical tithi/nakshatra",
    "Settle all pending legal, property, and financial disputes before the transit peaks",
    "Perform Navagraha Homa (fire ritual for all 9 planets) — BPHS Ch.88 general shanti",
    "Avoid risky travel; if unavoidable, offer travel prayer to Hanuman (Hanuman Chalisa v.38–40)",
]

_GURU_CHANDALA_REMEDIES = [
    "Recite Brihaspati Kavacham every Thursday — Brahma Purana Ch.29; Jupiter Kavacham nullifies "
    "Rahu's confusion of the Guru principle",
    "Recite Vishnu Sahasranama (Mahabharata, Anushasana Parva Ch.149) — Vishnu as Guru's ruling "
    "deity overrides Chandala (polluted) influence",
    "Perform Guru Puja — offer yellow cloth, turmeric, yellow flowers, and chickpeas to a learned "
    "Brahmin on Thursdays — BPHS 88.21–24",
    "Avoid seeking guidance from manipulative, deceptive, or unqualified teachers during this period",
    "Recite 'Om Namo Bhagavate Vasudevaya' (12-syllable Vishnu mantra, Bhagavata Purana 6.8) — "
    "directly pacifies the Jupiter–Rahu combination",
    "Donate yellow items (chana dal, turmeric, yellow cloth) to a Brahmin on Thursdays — "
    "BPHS 88.21: 'Guroh prasade sarvasya pitam vastra suvarnam…'",
]

_MARS_SATURN_REMEDIES = [
    "Recite Mars mantra on Tuesdays: 'Om Kraam Kreem Kraum Sah Bhaumaya Namah' (108×) — "
    "Mantra Mahodadhi Ch.5 (Mahidhara)",
    "Recite Saturn mantra on Saturdays: 'Om Praam Preem Praum Sah Shanaischaraya Namah' (108×) — "
    "Mantra Mahodadhi Ch.9",
    "Recite Hanuman Chalisa daily — covers both Mars (valour/courage) and Saturn (discipline) — "
    "Tulsidas (1532–1623 CE); Shani Mahatmya confirms Hanuman subdues Saturn",
    "Avoid risky physical activities, unsecured machinery, and unnecessary travel during exact "
    "conjunction — Mars + Saturn = accident/violence risk (Saravali Ch.5; SC v.4.18)",
    "Offer joint puja: red cloth and red flowers for Mars (Tuesday) + black sesame for Saturn "
    "(Saturday) — BPHS 88.13–16 (Mars); 88.29–32 (Saturn)",
    "Do not enter confrontations; Mars's anger amplified by Saturn's pressure leads to "
    "disproportionate consequences — Jataka Parijata Ch.3 on mutual planetary hostility",
]


@dataclass
class GocharaRemedy:
    planet: str
    situation: str              # e.g., "Saturn H8 — Ashtama Shani"
    priority: str               # "urgent" | "important" | "helpful"
    mantra: str
    mantra_source: str          # classical text citation for this mantra
    vedic_mantra: str           # Rigveda / Yajurveda / Atharvaveda root mantra
    stotra: str
    fast_day: str
    charity: str                # includes BPHS verse reference inline
    deity_puja: str
    gemstone_note: str          # includes Agni/Garuda Purana reference inline
    behavioral: str             # includes Saravali / BPHS / Lal Kitab citations inline
    special_actions: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)


@dataclass
class GocharaReport:
    transit_datetime: datetime
    natal_moon_sign: str
    natal_moon_house: int   # house in natal chart
    natal_lagna_sign: str
    current_mahadasha: str
    current_antardasha: str
    mahadasha_end: str
    antardasha_end: str
    planet_results: list[GrahaTransitResult]
    sadhe_sati: SadheSatiInfo
    special_alerts: list[SpecialTransitAlert]
    observations: list[str]
    favorable_count: int
    unfavorable_count: int
    mixed_count: int
    overall_tone: str       # "favorable" | "unfavorable" | "mixed" | "cautious"
    remedies: list[GocharaRemedy] = field(default_factory=list)

# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _house_from_sign(transit_sign_idx: int, ref_sign_idx: int) -> int:
    """Return 1-based house number of transit_sign counted from ref_sign."""
    return ((transit_sign_idx - ref_sign_idx) % 12) + 1


def _sign_name(sign_idx: int) -> str:
    _SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    ]
    return _SIGNS[sign_idx % 12]


def _sign_index(rasi_value: str) -> int:
    _IDX = {
        "Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3, "Leo": 4, "Virgo": 5,
        "Libra": 6, "Scorpio": 7, "Sagittarius": 8, "Capricorn": 9,
        "Aquarius": 10, "Pisces": 11,
    }
    return _IDX.get(rasi_value, 0)


def _get_active_dasha(natal_bundle: ChartBundle, at_time: datetime) -> tuple[str, str, str, str]:
    """Return (mahadasha_lord, antardasha_lord, maha_end_str, antar_end_str).

    Computes antardasha on-the-fly since bundles only store level-1 periods.
    """
    dashas = natal_bundle.dashas
    at_date = at_time.date() if hasattr(at_time, 'date') else at_time

    for maha in dashas:
        if maha.start_date <= at_date <= maha.end_date:
            maha_lord = maha.graha.value if hasattr(maha.graha, 'value') else str(maha.graha)

            # Check pre-computed sub_periods first; fall back to on-the-fly computation
            antardashas = maha.sub_periods or []
            if not antardashas:
                antardashas = compute_antardasha_periods(maha)

            for antar in antardashas:
                if antar.start_date <= at_date <= antar.end_date:
                    antar_lord = antar.graha.value if hasattr(antar.graha, 'value') else str(antar.graha)
                    return (
                        maha_lord,
                        antar_lord,
                        str(maha.end_date),
                        str(antar.end_date),
                    )
            return maha_lord, "—", str(maha.end_date), "—"
    return "—", "—", "—", "—"


def _check_vedha(
    transit_house: int,
    transit_planets: dict[str, int],   # graha_name -> house_from_moon
    checking_graha: str,
) -> tuple[bool, Optional[str]]:
    """Return (vedha_active, vedha_planet_name) for a transiting graha."""
    if transit_house not in _VEDHA_TABLE:
        return False, None
    vedha_house = _VEDHA_TABLE[transit_house]
    for gname, g_house in transit_planets.items():
        if gname == checking_graha:
            continue
        # Sun and Moon do not cause Vedha to each other (classical rule)
        if {checking_graha, gname} == {"Sun", "Moon"}:
            continue
        if g_house == vedha_house:
            return True, gname
    return False, None


def _sadhe_sati_analysis(saturn_house_from_moon: int) -> SadheSatiInfo:
    """Detect Sadhe Sati phases and Ashtama Shani."""
    if saturn_house_from_moon == 12:
        return SadheSatiInfo(
            active=True,
            phase="onset",
            description=(
                "Sadhe Sati — First Phase (onset): Saturn transiting 12th from natal Moon. "
                "This phase brings hidden anxieties, increased expenses, disturbed sleep, "
                "and subtle health issues. Spiritual practices are highly recommended. "
                "Duration ~2.5 years. BVRaman: 'Period of preparation for trials ahead.'"
            ),
            saturn_house_from_moon=12,
        )
    if saturn_house_from_moon == 1:
        return SadheSatiInfo(
            active=True,
            phase="peak",
            description=(
                "Sadhe Sati — Peak Phase (Janma Shani): Saturn on natal Moon. "
                "The most intense phase: major life restructuring, health challenges, "
                "career obstacles, relationship stress, financial pressure. "
                "The period demands patience, humility, and persistent effort. "
                "BPHS: 'Troubles in all spheres but fruits of past karma are cleared.' "
                "Duration ~2.5 years."
            ),
            saturn_house_from_moon=1,
        )
    if saturn_house_from_moon == 2:
        return SadheSatiInfo(
            active=True,
            phase="exit",
            description=(
                "Sadhe Sati — Third Phase (exit): Saturn transiting 2nd from natal Moon. "
                "Gradual relief from peak phase but still demanding. "
                "Financial constraints, family tensions, speech-related disputes. "
                "Conditions slowly begin to improve toward the end. Duration ~2.5 years."
            ),
            saturn_house_from_moon=2,
        )
    if saturn_house_from_moon == 8:
        return SadheSatiInfo(
            active=True,
            phase="ashtama",
            description=(
                "Ashtama Shani: Saturn transiting 8th from natal Moon — highly inauspicious. "
                "Accidents, chronic illness, financial loss, disgrace, and sudden obstacles. "
                "Complete a will/estate planning. Avoid risky ventures and travel. "
                "Perform Saturn remedies (Shani shanti). Duration ~2.5 years. "
                "BPHS 85.70: 'Brings calamities of all kinds.'"
            ),
            saturn_house_from_moon=8,
        )
    if saturn_house_from_moon == 4:
        return SadheSatiInfo(
            active=True,
            phase="kantaka",
            description=(
                "Kantaka Shani: Saturn transiting 4th from natal Moon. "
                "Domestic troubles, property disputes, vehicle problems, "
                "mother's health concerns, mental anguish. Avoid major property decisions. "
                "BPHS 85.66: 'Loss of home comforts and conveyance.'"
            ),
            saturn_house_from_moon=4,
        )
    return SadheSatiInfo(active=False, phase="", description="", saturn_house_from_moon=saturn_house_from_moon)


def _build_observations(
    results: list[GrahaTransitResult],
    sadhe_sati: SadheSatiInfo,
    maha_lord: str,
    antar_lord: str,
    natal_moon_sign: str,
    natal_lagna_sign: str,
) -> list[str]:
    """Generate rule-based textual observations from the Gochara analysis."""
    obs: list[str] = []

    # Dasha context
    obs.append(
        f"Active period: {maha_lord} Mahadasha / {antar_lord} Antardasha. "
        "Transit effects are filtered through the dasha lord's natal strength."
    )

    # Sadhe Sati / special Saturn alerts
    if sadhe_sati.active:
        obs.append(f"[ALERT] {sadhe_sati.description}")

    # Count favorable / unfavorable
    fav = [r for r in results if r.result_key == "favorable" and not r.vedha_active]
    unf = [r for r in results if r.result_key == "unfavorable"]
    mixed = [r for r in results if r.result_key == "mixed"]

    obs.append(
        f"Transit score: {len(fav)} favorable, {len(unf)} unfavorable, "
        f"{len(mixed)} mixed out of 9 planets."
    )

    # Jupiter position
    jup = next((r for r in results if r.graha == "Jupiter"), None)
    if jup:
        if jup.transit_house_from_moon == 11:
            obs.append(
                "Jupiter transiting 11th from Moon (Labha): MOST AUSPICIOUS Jupiter transit. "
                "Fulfillment of all desires, major gains, health recovery. A golden period."
            )
        elif jup.transit_house_from_moon == 2:
            obs.append(
                "Jupiter transiting 2nd from Moon: Excellent for wealth, family happiness, "
                "and speech. Financial gains expected."
            )
        elif jup.transit_house_from_moon in (5, 7, 9):
            obs.append(
                f"Jupiter transiting {jup.transit_house_from_moon}th from Moon: "
                f"Favorable — {jup.short_effect}."
            )
        elif jup.transit_house_from_moon in (1, 3, 4, 6, 8, 10, 12):
            obs.append(
                f"Jupiter transiting {jup.transit_house_from_moon}th from Moon: "
                f"Unfavorable — {jup.short_effect}. Jupiter relief comes when it moves to 2nd/5th/7th/9th/10th/11th."
            )

    # Saturn special positions
    sat = next((r for r in results if r.graha == "Saturn"), None)
    if sat and not sadhe_sati.active:
        if sat.transit_house_from_moon == 3:
            obs.append(
                "Saturn transiting 3rd from Moon: BEST Saturn position. "
                "Financial gains, victory over enemies, courage. Make bold moves."
            )
        elif sat.transit_house_from_moon == 11:
            obs.append(
                "Saturn transiting 11th from Moon: Very favorable — gains, success, "
                "fulfillment of desires. Second best Saturn position."
            )
        elif sat.transit_house_from_moon == 6:
            obs.append(
                "Saturn transiting 6th from Moon: Favorable for service, victory over enemies, "
                "recovery from debts."
            )

    # Sun special
    sun = next((r for r in results if r.graha == "Sun"), None)
    if sun and sun.transit_house_from_moon == 10:
        obs.append(
            "Sun transiting 10th from Moon: Career peak period. Seek recognition, "
            "approach authority figures, launch career initiatives now."
        )
    if sun and sun.transit_house_from_moon == 11:
        obs.append(
            "Sun transiting 11th from Moon: Financial gains and recovery. Good time for "
            "income-generating activities."
        )

    # Mars special
    mars = next((r for r in results if r.graha == "Mars"), None)
    if mars and mars.transit_house_from_moon == 3:
        obs.append(
            "Mars transiting 3rd from Moon: Excellent period for bold initiatives, "
            "physical activities, competitions, and assertive communication."
        )
    if mars and mars.transit_house_from_moon in (8,):
        obs.append(
            "Mars in 8th from Moon: High risk period for accidents. "
            "Avoid surgery if possible, drive carefully, avoid conflicts."
        )

    # Moon's own transit (from Lagna)
    moon = next((r for r in results if r.graha == "Moon"), None)
    if moon:
        obs.append(
            f"Moon transiting {moon.transit_sign} "
            f"({moon.transit_house_from_moon}th from natal Moon, "
            f"{moon.transit_house_from_lagna}th from Lagna): "
            f"{moon.short_effect}. Moon changes signs every 2.25 days."
        )

    # Dasha lord transit
    for r in results:
        if r.is_dasha_lord:
            tone = "amplifies" if r.result_key == "favorable" else "intensifies challenges in"
            obs.append(
                f"Active Mahadasha lord {r.graha} transiting {r.transit_house_from_moon}th "
                f"from Moon ({r.transit_sign}): {tone} the dasha period effects. {r.short_effect}."
            )
        if r.is_antardasha_lord and antar_lord != maha_lord:
            tone = "supports" if r.result_key == "favorable" else "adds stress to"
            obs.append(
                f"Active Antardasha lord {r.graha} transiting {r.transit_house_from_moon}th "
                f"from Moon: {tone} current sub-period. {r.short_effect}."
            )

    # Vedha alerts
    for r in results:
        if r.vedha_active and r.result_key in ("favorable", "mixed"):
            obs.append(
                f"Vedha (obstruction): {r.graha}'s favorable transit in {r.transit_house_from_moon}th "
                f"from Moon is blocked by {r.vedha_planet} in the Vedha position. "
                f"Results reduced or delayed."
            )

    # Retrograde planets
    retro = [r for r in results if r.is_retrograde and r.graha not in ("Rahu", "Ketu")]
    if retro:
        obs.append(
            "Retrograde planets: " + ", ".join(r.graha for r in retro) + ". "
            "Their transit effects are internalized and may manifest in reversed, delayed, "
            "or introspective ways."
        )

    # Guru Chandala check (Jupiter + Rahu same sign in transit)
    jup_sign = next((r.transit_sign for r in results if r.graha == "Jupiter"), None)
    rahu_sign = next((r.transit_sign for r in results if r.graha == "Rahu"), None)
    if jup_sign and rahu_sign and jup_sign == rahu_sign:
        obs.append(
            f"[ALERT] Guru Chandala Yoga in transit: Jupiter and Rahu both in {jup_sign}. "
            "Wisdom clouded by worldly desires. Be cautious of misleading advisors and "
            "unconventional shortcuts. Spiritual practices help counteract."
        )

    # Rahu-Ketu axis observation
    rahu_r = next((r for r in results if r.graha == "Rahu"), None)
    ketu_r = next((r for r in results if r.graha == "Ketu"), None)
    if rahu_r and ketu_r:
        obs.append(
            f"Rahu-Ketu nodal axis: Rahu in {rahu_r.transit_sign} "
            f"({rahu_r.transit_house_from_moon}th from Moon), "
            f"Ketu in {ketu_r.transit_sign} ({ketu_r.transit_house_from_moon}th from Moon). "
            "Nodes move ~1.5° per month (retrograde). Focus area shifts toward Rahu's house themes."
        )

    # Overall guidance
    if len(fav) >= 5:
        obs.append(
            "Overall transit outlook: GENERALLY FAVORABLE. A majority of planets are well-placed. "
            "Initiate new projects, make important decisions, and leverage opportunities."
        )
    elif len(unf) >= 5:
        obs.append(
            "Overall transit outlook: CHALLENGING. Many planets in difficult positions. "
            "Consolidate existing resources, avoid risky ventures, practice patience. "
            "Spiritual disciplines and charity are recommended."
        )
    elif len(fav) > len(unf):
        obs.append(
            "Overall transit outlook: MODERATELY FAVORABLE. More supportive than challenging. "
            "Proceed with plans but maintain due caution."
        )
    else:
        obs.append(
            "Overall transit outlook: MIXED. Balanced between supportive and challenging energies. "
            "Discriminate carefully between opportunities and risks."
        )

    return obs


def _build_special_alerts(
    results: list[GrahaTransitResult],
    sadhe_sati: SadheSatiInfo,
    natal_bundle: ChartBundle,
    transit_snapshot: TransitSnapshot,
) -> list[SpecialTransitAlert]:
    alerts: list[SpecialTransitAlert] = []

    if sadhe_sati.active:
        severity = "alert" if sadhe_sati.phase in ("peak", "ashtama") else "warning"
        alerts.append(SpecialTransitAlert(
            name=f"Sadhe Sati — {sadhe_sati.phase.title()}" if sadhe_sati.phase != "ashtama"
                 else "Ashtama Shani" if sadhe_sati.phase == "ashtama"
                 else "Kantaka Shani",
            severity=severity,
            description=sadhe_sati.description,
        ))

    # Guru Chandala
    jup_sign = next((r.transit_sign for r in results if r.graha == "Jupiter"), None)
    rahu_sign = next((r.transit_sign for r in results if r.graha == "Rahu"), None)
    if jup_sign and rahu_sign and jup_sign == rahu_sign:
        alerts.append(SpecialTransitAlert(
            name="Guru Chandala Yoga",
            severity="warning",
            description=f"Jupiter conjunct Rahu in {jup_sign} in transit. Wisdom clouded.",
        ))

    # Mars + Saturn together
    mars_sign = next((r.transit_sign for r in results if r.graha == "Mars"), None)
    sat_sign  = next((r.transit_sign for r in results if r.graha == "Saturn"), None)
    if mars_sign and sat_sign and mars_sign == sat_sign:
        alerts.append(SpecialTransitAlert(
            name="Mars–Saturn Transit Conjunction",
            severity="warning",
            description=(
                f"Mars and Saturn both transiting {mars_sign}. Explosive friction energy. "
                "Accidents, surgeries, conflicts are more likely. Extra caution advised."
            ),
        ))

    # Jupiter in 11th — Golden period alert
    jup_h = next((r.transit_house_from_moon for r in results if r.graha == "Jupiter"), None)
    if jup_h == 11:
        alerts.append(SpecialTransitAlert(
            name="Jupiter in 11th — Golden Period",
            severity="info",
            description=(
                "Jupiter transiting 11th from Moon: The most auspicious Jupiter transit. "
                "Maximize gains, launch important projects, expand networks."
            ),
        ))

    return alerts


def _build_remedies(
    planet_results: list,
    sadhe_sati: "SadheSatiInfo",
    special_alerts: list,
    maha_lord: str,
    antar_lord: str,
) -> list[GocharaRemedy]:
    """Build prioritized list of remedies for unfavorable/mixed Gochara positions.

    Priority logic:
      - urgent: Sadhe Sati peak, Ashtama Shani, active dasha lord in severe transit
      - important: unfavorable planet (not vedha-cancelled), dasha lord mixed
      - helpful: mixed planets, mildly unfavorable
    """
    remedies: list[GocharaRemedy] = []
    seen: set[str] = set()   # avoid duplicate planet remedies

    def _make_remedy(
        planet: str, situation: str, priority: str,
        special: list[str] | None = None,
        refs: list[str] | None = None,
    ) -> GocharaRemedy:
        return GocharaRemedy(
            planet=planet,
            situation=situation,
            priority=priority,
            mantra=_PLANET_BEEJA_MANTRA.get(planet, ""),
            mantra_source=_PLANET_MANTRA_SOURCE.get(planet, ""),
            vedic_mantra=_PLANET_VEDIC_MANTRA.get(planet, ""),
            stotra=_PLANET_STOTRA.get(planet, ""),
            fast_day=_PLANET_FAST_DAY.get(planet, ""),
            charity=_PLANET_CHARITY.get(planet, ""),
            deity_puja=_PLANET_DEITY.get(planet, ""),
            gemstone_note=_PLANET_GEMSTONE.get(planet, ""),
            behavioral=_PLANET_BEHAVIORAL.get(planet, ""),
            special_actions=special or [],
            source_refs=refs or ["BPHS Ch.88 (Graha Shanti)", "Lal Kitab (Arun Samhita)"],
        )

    # ── Step 1: Special situation remedies first (highest priority) ──────────

    # Sadhe Sati / Ashtama Shani
    if sadhe_sati.active and sadhe_sati.phase == "peak":
        remedies.append(_make_remedy(
            "Saturn",
            "Sadhe Sati — Peak Phase (Janma Shani): Saturn on natal Moon",
            "urgent",
            special=_SATURN_SADHESATI_REMEDIES,
            refs=["BPHS Ch.88", "Shani Mahatmya", "Lal Kitab", "B.V. Raman: Planetary Influences"],
        ))
        seen.add("Saturn")
    elif sadhe_sati.active and sadhe_sati.phase == "ashtama":
        remedies.append(_make_remedy(
            "Saturn",
            "Ashtama Shani: Saturn in 8th from natal Moon",
            "urgent",
            special=_SATURN_ASHTAMA_REMEDIES,
            refs=["BPHS Ch.85.70", "Shani Mahatmya", "B.V. Raman"],
        ))
        seen.add("Saturn")
    elif sadhe_sati.active and sadhe_sati.phase in ("onset", "exit"):
        remedies.append(_make_remedy(
            "Saturn",
            f"Sadhe Sati — {sadhe_sati.phase.title()} Phase",
            "important",
            special=_SATURN_SADHESATI_REMEDIES[:6],
            refs=["BPHS Ch.88", "Shani Mahatmya", "Lal Kitab"],
        ))
        seen.add("Saturn")
    elif sadhe_sati.active and sadhe_sati.phase == "kantaka":
        remedies.append(_make_remedy(
            "Saturn",
            "Kantaka Shani: Saturn in 4th from natal Moon",
            "important",
            special=_SATURN_SADHESATI_REMEDIES[:5],
            refs=["BPHS Ch.85.66", "Shani Mahatmya"],
        ))
        seen.add("Saturn")

    # Guru Chandala in transit
    alert_names = {a.name for a in special_alerts}
    if "Guru Chandala Yoga" in alert_names:
        if "Jupiter" not in seen:
            remedies.append(_make_remedy(
                "Jupiter",
                "Guru Chandala Yoga in transit: Jupiter + Rahu conjunct",
                "important",
                special=_GURU_CHANDALA_REMEDIES,
                refs=["Sarvartha Chintamani", "Muhurta Chintamani"],
            ))
            seen.add("Jupiter")

    # Mars–Saturn conjunction
    if "Mars–Saturn Transit Conjunction" in alert_names:
        if "Mars" not in seen:
            remedies.append(_make_remedy(
                "Mars",
                "Mars–Saturn Transit Conjunction: explosive friction energy",
                "important",
                special=_MARS_SATURN_REMEDIES,
                refs=["BPHS Ch.85", "Sarvartha Chintamani"],
            ))
            seen.add("Mars")

    # ── Step 2: Active dasha lord unfavorable transit ────────────────────────
    for r in planet_results:
        if r.graha in seen:
            continue
        if r.is_dasha_lord and r.result_key in ("unfavorable", "mixed"):
            priority = "urgent" if r.result_key == "unfavorable" else "important"
            situation = (
                f"Active Mahadasha lord {r.graha} transiting {r.transit_house_from_moon}th "
                f"from Moon ({r.transit_sign}) — {r.short_effect}"
            )
            remedies.append(_make_remedy(r.graha, situation, priority))
            seen.add(r.graha)

    # ── Step 3: Active antardasha lord unfavorable transit ───────────────────
    for r in planet_results:
        if r.graha in seen:
            continue
        if r.is_antardasha_lord and r.result_key in ("unfavorable", "mixed"):
            situation = (
                f"Active Antardasha lord {r.graha} transiting {r.transit_house_from_moon}th "
                f"from Moon ({r.transit_sign}) — {r.short_effect}"
            )
            remedies.append(_make_remedy(r.graha, situation, "important"))
            seen.add(r.graha)

    # ── Step 4: Other unfavorable planets (not Vedha-cancelled) ─────────────
    # Priority order: Saturn > Mars > Rahu > Jupiter > Sun > Moon > Mercury > Venus > Ketu
    _SEVERITY_ORDER = ["Saturn", "Mars", "Rahu", "Jupiter", "Sun", "Moon", "Mercury", "Venus", "Ketu"]
    for gname in _SEVERITY_ORDER:
        if gname in seen:
            continue
        r = next((x for x in planet_results if x.graha == gname), None)
        if not r:
            continue
        if r.result_key == "unfavorable" and not r.vedha_active:
            situation = (
                f"{r.graha} transiting {r.transit_house_from_moon}th from Moon "
                f"({r.transit_sign}) — {r.short_effect}"
            )
            remedies.append(_make_remedy(r.graha, situation, "helpful"))
            seen.add(r.graha)

    # ── Step 5: Mixed planets (helpful only) ────────────────────────────────
    for gname in _SEVERITY_ORDER:
        if gname in seen:
            continue
        r = next((x for x in planet_results if x.graha == gname), None)
        if not r:
            continue
        if r.result_key == "mixed":
            situation = (
                f"{r.graha} transiting {r.transit_house_from_moon}th from Moon "
                f"({r.transit_sign}) — {r.short_effect} (mixed)"
            )
            remedies.append(_make_remedy(r.graha, situation, "helpful"))
            seen.add(r.graha)

    # ── Step 6: General remedy if overall tone is unfavorable ───────────────
    unfav_count = sum(1 for r in planet_results if r.result_key == "unfavorable" and not r.vedha_active)
    if unfav_count >= 4 and "general" not in seen:
        general = GocharaRemedy(
            planet="All",
            situation="Multiple planets unfavorably placed — overall Gochara challenging",
            priority="important",
            mantra="Navagraha Mantra: 'Om Navagrahaya Namah' — followed by each planet's mantra",
            mantra_source="Navagraha Stotra (attr. Vyasa, Brahma Purana); each planet's beeja from Mantra Mahodadhi Ch.3–11 (Mahidhara, 16th c.)",
            vedic_mantra="Rigveda 1.89.8 (Vishwedeva Sukta): 'Bhadram karnebhih shrinuyama devah…' — may we hear auspicious things with our ears (invokes all devas incl. all 9 grahas)",
            stotra="Navagraha Stotra (recite all 9 planetary stotras in sequence)",
            fast_day="Observe 9-day Navagraha fast beginning on a Sunday",
            charity=(
                "Perform Navagraha Shanti puja — donate items for all 9 planets. "
                "Alternatively, donate a rainbow-colored thread (nine-colored) to a temple."
            ),
            deity_puja=(
                "Perform Navagraha Puja at a Navagraha temple (all 9 deity shrines). "
                "Offer individual items to each graha shrine."
            ),
            gemstone_note="Consult an expert astrologer before wearing any gemstone during a challenging transit period.",
            behavioral=(
                "Practice Ahimsa (non-violence), Satya (truthfulness), and Dana (charity). "
                "Perform daily sunrise and sunset Sandhyavandanam or Sun salutation. "
                "Avoid major new ventures during the most challenging transit windows."
            ),
            special_actions=[
                "Perform a full Navagraha Homa (fire ritual) — resolves multiple planetary afflictions",
                "Visit a Navagraha temple and make offerings to all 9 graha shrines",
                "Recite the Maha Mrityunjaya Mantra 108 times daily for overall protection",
                "Light a sesame oil lamp daily at Navagraha shrine or home altar",
                "Donate food to 9 poor people on 9 consecutive days",
            ],
            source_refs=["BPHS Ch.88", "Navagraha Stotra", "Muhurta Chintamani"],
        )
        remedies.append(general)

    return remedies


def compute_gochara(
    natal_bundle: ChartBundle,
    transit_snapshot: TransitSnapshot,
) -> GocharaReport:
    """Compute full Gochara analysis from natal chart and transit snapshot.

    Returns a GocharaReport with per-planet results, Vedha analysis,
    Sadhe Sati detection, special alerts, and rule-based observations.
    """
    d1 = natal_bundle.d1
    asc_lon = d1.ascendant_longitude
    lagna_sign_idx = int(asc_lon / 30.0)

    # Natal Moon sign
    natal_moon = d1.planets.get("Moon")
    if natal_moon is None:
        raise ValueError("Natal Moon placement not found in ChartBundle")
    natal_moon_sign_idx = int(natal_moon.longitude / 30.0) if natal_moon.longitude is not None \
        else _sign_index(natal_moon.rasi.rasi.value)
    natal_moon_sign = _sign_name(natal_moon_sign_idx)
    natal_moon_house = natal_moon.house or 1

    natal_lagna_sign = _sign_name(lagna_sign_idx)

    # Active dasha
    at_time = transit_snapshot.at_time
    maha_lord, antar_lord, maha_end, antar_end = _get_active_dasha(natal_bundle, at_time)

    # Compute transit house from Moon for each planet (for Vedha check)
    transit_house_from_moon_map: dict[str, int] = {}
    for graha in Graha:
        gname = graha.value
        tp = transit_snapshot.planets.get(gname)
        if tp is None:
            continue
        t_lon = tp.longitude
        t_sign_idx = int(t_lon / 30.0)
        transit_house_from_moon_map[gname] = _house_from_sign(t_sign_idx, natal_moon_sign_idx)

    # Build per-planet results
    planet_results: list[GrahaTransitResult] = []
    _ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

    for gname in _ORDER:
        tp = transit_snapshot.planets.get(gname)
        if tp is None:
            continue

        t_lon = tp.longitude
        t_sign_idx = int(t_lon / 30.0)
        t_sign = _sign_name(t_sign_idx)
        h_from_moon  = _house_from_sign(t_sign_idx, natal_moon_sign_idx)
        h_from_lagna = _house_from_sign(t_sign_idx, lagna_sign_idx)

        natal_p = d1.planets.get(gname)
        natal_sign = _sign_name(int(natal_p.longitude / 30.0)) if natal_p else "—"
        natal_house = natal_p.house if natal_p else 0

        rules = _GOCHARA_EFFECTS.get(gname, [])
        if rules and 1 <= h_from_moon <= 12:
            result_key, short_effect, detail = rules[h_from_moon - 1]
        else:
            result_key, short_effect, detail = "neutral", "Neutral", ""

        vedha_active, vedha_planet = _check_vedha(
            h_from_moon,
            transit_house_from_moon_map,
            gname,
        )

        is_retrograde = bool(tp.is_retrograde)
        is_dasha_lord = (gname == maha_lord)
        is_antar_lord = (gname == antar_lord)

        planet_results.append(GrahaTransitResult(
            graha=gname,
            transit_sign=t_sign,
            transit_house_from_moon=h_from_moon,
            transit_house_from_lagna=h_from_lagna,
            natal_sign=natal_sign,
            natal_house=natal_house,
            result_key=result_key,
            short_effect=short_effect,
            detail=detail,
            vedha_active=vedha_active,
            vedha_planet=vedha_planet,
            is_retrograde=is_retrograde,
            is_dasha_lord=is_dasha_lord,
            is_antardasha_lord=is_antar_lord,
        ))

    # Sadhe Sati analysis
    sat_house_from_moon = transit_house_from_moon_map.get("Saturn", 0)
    sadhe_sati = _sadhe_sati_analysis(sat_house_from_moon)

    # Special alerts
    special_alerts = _build_special_alerts(planet_results, sadhe_sati, natal_bundle, transit_snapshot)

    # Remedies
    remedies = _build_remedies(planet_results, sadhe_sati, special_alerts, maha_lord, antar_lord)

    # Observations
    observations = _build_observations(
        planet_results, sadhe_sati, maha_lord, antar_lord,
        natal_moon_sign, natal_lagna_sign,
    )

    # Counts
    fav   = sum(1 for r in planet_results if r.result_key == "favorable" and not r.vedha_active)
    unf   = sum(1 for r in planet_results if r.result_key == "unfavorable")
    mixed = sum(1 for r in planet_results if r.result_key == "mixed")

    if fav >= 5:
        overall_tone = "favorable"
    elif unf >= 5:
        overall_tone = "unfavorable"
    elif sadhe_sati.active and sadhe_sati.phase in ("peak", "ashtama"):
        overall_tone = "cautious"
    elif fav > unf:
        overall_tone = "mixed"
    else:
        overall_tone = "mixed"

    return GocharaReport(
        transit_datetime=at_time,
        natal_moon_sign=natal_moon_sign,
        natal_moon_house=natal_moon_house,
        natal_lagna_sign=natal_lagna_sign,
        current_mahadasha=maha_lord,
        current_antardasha=antar_lord,
        mahadasha_end=maha_end,
        antardasha_end=antar_end,
        planet_results=planet_results,
        sadhe_sati=sadhe_sati,
        special_alerts=special_alerts,
        observations=observations,
        favorable_count=fav,
        unfavorable_count=unf,
        mixed_count=mixed,
        overall_tone=overall_tone,
        remedies=remedies,
    )
