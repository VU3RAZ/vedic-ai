"""House influence analysis: combined effect of occupants + drishti on each house.

For every house 1-12 this module produces:
  - Which planets occupy it (and their classical effects on that house's topics)
  - Which planets aspect it (graha / rashi / double) and their interpretive effect
  - A net benefic/malefic rating and numeric score
  - Special classical rule annotations (Kuja dosha, Digbala, etc.)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# House significance
# ---------------------------------------------------------------------------

HOUSE_TOPICS: dict[int, tuple[str, str]] = {
    1:  ("Self, body, personality, vitality, appearance",           "Tanu Bhava"),
    2:  ("Wealth, family, speech, food, early education",           "Dhana Bhava"),
    3:  ("Siblings, courage, communication, skills, short journeys","Sahaja Bhava"),
    4:  ("Mother, home, happiness, property, education, vehicles",  "Sukha Bhava"),
    5:  ("Children, intellect, creativity, romance, speculation",   "Putra Bhava"),
    6:  ("Enemies, disease, debts, service, competition",           "Ripu Bhava"),
    7:  ("Spouse, marriage, partnerships, public dealings",         "Kalatra Bhava"),
    8:  ("Longevity, transformation, occult, inheritance, crises",  "Ayu Bhava"),
    9:  ("Dharma, father, luck, higher wisdom, religion, travel",   "Dharma Bhava"),
    10: ("Career, profession, status, authority, public life",      "Karma Bhava"),
    11: ("Gains, elder siblings, social circle, aspirations",       "Labha Bhava"),
    12: ("Losses, expenses, foreign, spirituality, liberation",     "Vyaya Bhava"),
}

# ---------------------------------------------------------------------------
# Natural quality of each planet
# ---------------------------------------------------------------------------

NATURAL_QUALITY: dict[str, str] = {
    "Jupiter": "benefic", "Venus": "benefic", "Moon": "benefic",
    "Mercury": "neutral", "Sun": "neutral",
    "Mars": "malefic", "Saturn": "malefic", "Rahu": "malefic", "Ketu": "malefic",
}

# ---------------------------------------------------------------------------
# Classical planet-in-house effects  (9 planets × 12 houses)
# ---------------------------------------------------------------------------

PLANET_IN_HOUSE: dict[str, dict[int, str]] = {
    "Sun": {
        1:  "Strong individuality and commanding presence; natural authority; radiant self-expression; pride in identity.",
        2:  "Wealth through authority or government; influential and commanding speech; family pride; father connection to family finances.",
        3:  "Courageous, self-driven communication; ambitious initiative; ego-driven interactions with siblings; strong will-power.",
        4:  "Dominating home environment; government property possible; mother's constitution and vitality; pride in homeland.",
        5:  "Brilliant, authoritative intellect; ambitious and leadership-oriented children; confident speculation; strong ego in romance.",
        6:  "Defeats enemies and illness through authority; government service; digestive heat; overcomes litigation with confidence.",
        7:  "Powerful or egoistic spouse; ego conflicts in marriage; partner with status or authority; delays possible due to pride.",
        8:  "Research, investigation, and occult inclinations; longevity through vitality; inheritance from authority; government secrets.",
        9:  "Deeply philosophical and dharmic; prominent father figure; government or religious authority; luck through leadership.",
        10: "Exceptional career success; government, administrative, or political roles; strong public recognition and status.",
        11: "Gains through authority, government, or prominent networks; influential elder siblings; pride in ambitions fulfilled.",
        12: "Spiritual isolation; expenses through ego or authority; foreign government roles; possible vision challenges.",
    },
    "Moon": {
        1:  "Emotional, sensitive, and nurturing personality; changeable moods; attractive appearance; strong intuition and empathy.",
        2:  "Wealth through mother, nourishment, or public service; melodious and persuasive speech; strong family emotional bonds.",
        3:  "Emotionally driven communication; deep bond with siblings; travel for emotional comfort; intuitive mind.",
        4:  "Deep emotional connection to mother and home; strong domestic happiness; comfortable property; excellent for 4th house themes.",
        5:  "Emotionally invested in children; creative emotional intelligence; romantic sensitivity; fluctuating speculative interest.",
        6:  "Emotional health fluctuations; digestive sensitivity; compassionate service; emotional enemies; mental anxieties possible.",
        7:  "Emotionally nurturing and caring spouse; changeable partnership dynamics; marriage brings emotional fulfilment.",
        8:  "Emotional transformations; interest in occult and the unseen; longevity through emotional resilience; subconscious depth.",
        9:  "Deep devotion to religion and mother; spiritual travels; luck through intuition; emotional relationship with father or guru.",
        10: "Career in caring, nourishment, public-facing, or creative roles; emotionally resonant public image; fluctuating status.",
        11: "Gains through women, public, or emotional connections; fluctuating but fulfilling aspirations; nurturing social circle.",
        12: "Spiritual and emotional depth; foreign residence or home; subconscious richness; expenses through family or emotions.",
    },
    "Mars": {
        1:  "Energetic, assertive, and athletic; courageous personality; prone to rashness; Ruchaka yoga if in kendra and own/exalted sign.",
        2:  "Aggressive or decisive speech; expenditure on property or weapons; family tensions; wealth through land or force.",
        3:  "Exceptional courage and will-power; competitive and assertive siblings; dynamic communication; martial or athletic skills.",
        4:  "Property through real estate or land; conflicts at home; energetic or strong-willed mother; possible vehicle accidents.",
        5:  "Passionate, competitive intellect; athletic or courageous children; speculative risks; forceful creative energy.",
        6:  "Overcomes enemies and disease with force; strong immunity; service in military, police, medicine, or engineering.",
        7:  "Kuja Dosha — marital tensions and conflicts; energetic or aggressive spouse; passionate but combative partnerships; Kuja Dosha mitigated if Mars is in own or exalted sign.",
        8:  "Surgeries or accidents possible; fierce transformative energy; interest in occult combat; Mars rules 8th = Scorpio connection.",
        9:  "Crusading dharmic approach; competitive spirituality; father may be military or forceful; zeal for righteous action.",
        10: "Career in military, engineering, surgery, sports, or real estate; strong executive authority; Mars in Digbala here.",
        11: "Gains through property, land, effort, or military; competitive in social circles; goal-oriented and driven aspirations.",
        12: "Kuja Dosha position; expenses through aggression or conflict; foreign military or engineering roles; marital complications.",
    },
    "Mercury": {
        1:  "Intellectual, communicative, and analytical personality; youthful or boyish appearance; adaptable, quick-witted mind.",
        2:  "Eloquent and persuasive speech; wealth through intellect, trade, or writing; skilled in accounts and communication.",
        3:  "Excellent communicator, writer, or journalist; skilled hands; learning through short journeys; close intellectual siblings.",
        4:  "Intellectual home environment; interest in education and real estate; analytical approach to domestic and property matters.",
        5:  "Brilliant analytical intellect; multiple children or intellectual pursuits; skill in speculative trade and games of mind.",
        6:  "Service through intellect and analysis; legal, medical, or health-analytical roles; overcomes enemies with wit and strategy.",
        7:  "Intellectual or youthful spouse; business and trading partnerships; commerce through marriage; negotiation skills.",
        8:  "Research, writing on occult, medicine, or finance; analytical approach to inheritance; intellectual depth in crisis.",
        9:  "Philosophical intellect; travel for education; analytical religious understanding; writing and teaching dharma.",
        10: "Career in writing, communication, commerce, education, IT, or technology; intellectual public status.",
        11: "Gains through intellect, trade, or communication; intellectual and versatile social circle; multiple aspirations fulfilled.",
        12: "Writing and research in seclusion; spiritual intellect; foreign correspondence; analytical approach to liberation.",
    },
    "Jupiter": {
        1:  "Wise, generous, and philosophical personality; Hamsa yoga if in kendra in own or exalted sign; broad and benevolent perspective.",
        2:  "Dhana yoga potential; wealth through wisdom, dharma, or teaching; eloquent philosophical speech; generous with family.",
        3:  "Wise communication and teaching through writing; dharmic courage; philosophical siblings; knowledge as skill.",
        4:  "Happy and prosperous domestic life; wise and spiritual mother; excellent education; property blessings.",
        5:  "Excellent for children; brilliant philosophical intellect; spiritual creativity; high dharma in romance and speculation.",
        6:  "Overcomes obstacles through wisdom and prayer; health protection through dharma; service in education or religion.",
        7:  "Excellent for marriage — wise, dharmic, and prosperous spouse; harmonious and dharmic partnerships; spiritual union.",
        8:  "Spiritual interest in occult and transformation; longevity protected by wisdom; grace through crisis and inheritance.",
        9:  "Guru yoga — deeply spiritual, philosophical, and fortunate; father may be teacher, guru, or benefactor; abundant luck.",
        10: "Dharmic and respected career; education, religion, law, counselling, or finance; highly regarded public figure.",
        11: "Significant gains through wisdom and dharma; influential and spiritual social circle; fulfilled aspirations with integrity.",
        12: "Spiritual liberation and foreign dharmic travel; expenses for religious or charitable purposes; connection to ashram or monastery.",
    },
    "Venus": {
        1:  "Beautiful, charming, and artistic personality; Malavya yoga if in kendra in own or exalted sign; love of beauty and pleasure.",
        2:  "Wealth through beauty, art, or luxury goods; melodious and appealing speech; pleasurable family environment; fine food.",
        3:  "Artistic communication and creative writing; harmonious siblings; aesthetic and diplomatic courage; beauty in expression.",
        4:  "Beautiful and comfortable home; pleasures of domestic life; devoted and artistic mother; luxury vehicles and comforts.",
        5:  "Romantic and creative intellect; talented and artistic children; pleasurable speculative interest; beauty in romance.",
        6:  "Service in beauty, art, or healthcare industry; overcomes enemies through charm and diplomacy; indulgence risks health.",
        7:  "Excellent for marriage — beautiful, artistic, and harmonious spouse; pleasurable and refined partnerships.",
        8:  "Sensual depth and artistic approach to transformation; financial gains through spouse or inheritance; occult arts.",
        9:  "Artistic and aesthetic dharma; beautiful spiritual life; fortunate and charming father; luck through luxury and beauty.",
        10: "Career in arts, entertainment, beauty, diplomacy, fashion, or luxury industries; glamorous public image.",
        11: "Gains through beauty, art, entertainment, or relationships; pleasurable and artistic social circle.",
        12: "Artistic seclusion; foreign pleasures and romance; spiritual beauty; expenses on luxury or sensual indulgence.",
    },
    "Saturn": {
        1:  "Disciplined, reserved, and austere personality; slow start but lasting achievement; Sasa yoga if in kendra own or exalted sign.",
        2:  "Wealth through discipline, hard work, and frugality; serious speech; delayed family growth; methodical accumulation.",
        3:  "Disciplined and methodical communication; hard-working siblings; persevering courage; delayed or serious short journeys.",
        4:  "Domestic responsibilities and restrictions; delayed happiness; mother may have chronic health issues; late property acquisition.",
        5:  "Delayed or fewer children; disciplined and serious intellect; structured romance; past-life (Purvapunya) karma expressed.",
        6:  "Exceptional service and disciplined work ethic; chronic but well-managed health; defeats enemies through perseverance.",
        7:  "Delayed marriage; spouse may be serious, older, or disciplined; structured but long-lasting partnerships once formed.",
        8:  "Longevity through discipline and careful health management; chronic conditions managed; slow but thorough transformation.",
        9:  "Disciplined and karmic dharma; late-blooming father relationship; karma yoga approach to spirituality; practical religion.",
        10: "Exceptional career through discipline and methodical effort; government, organizational, or structural roles; Sasa yoga indicator.",
        11: "Gains through discipline, hard work, and persistence; serious and long-term goals achieved; structured social circle.",
        12: "Spiritual discipline and austerity; foreign long-term residence; service in isolation; moksha through karma yoga.",
    },
    "Rahu": {
        1:  "Unconventional, foreign, or unusual appearance and personality; strong worldly ambition; possible health enigmas; restless.",
        2:  "Wealth through unconventional, foreign, or technological means; unusual speech; non-traditional family; amplified desires.",
        3:  "Unconventional communication and media skills; foreign or unusual siblings; amplified and obsessive courage.",
        4:  "Foreign homeland or unconventional domestic life; unusual mother; restless property dealings; foreign real estate.",
        5:  "Unconventional intellect; foreign or unusual children; speculative gains and risks; obsessive romantic interest.",
        6:  "Amplifies enemies and competition but also amplifies overcoming them; unusual health conditions; obsessive service.",
        7:  "Unconventional or foreign spouse; obsessive attraction; unusual or cross-cultural marriage circumstances.",
        8:  "Intense occult interest and research; sudden transformations; foreign inheritances; mysterious or unusual health events.",
        9:  "Unconventional dharma; foreign religion or guru; amplified ambition in philosophical or spiritual matters.",
        10: "Rapid rise through unconventional, foreign, or technology-driven career; political ambition; disruption in status.",
        11: "Sudden large gains; foreign or unconventional social circle; amplified and insatiable desires and aspirations.",
        12: "Foreign residence; spiritual path through worldly experience; liberation through desire's dissolution; foreign hospitals.",
    },
    "Ketu": {
        1:  "Spiritual, detached, and past-life wisdom; psychic sensitivity; unusual health patterns; withdrawal from worldly identity.",
        2:  "Spiritual or non-materialistic approach to wealth; detachment from family accumulation; past-life financial karma.",
        3:  "Past-life communication skills and knowledge; detached or spiritual siblings; intuitive and non-conventional courage.",
        4:  "Past-life home karma; emotional detachment from mother; spiritual domestic life; inner happiness over external comfort.",
        5:  "Past-life intellectual karma; spiritual or unusual children; intuitive creativity; renunciation or detachment in romance.",
        6:  "Past-life healing abilities; spiritual service; psychic immunity to disease; dissolution or forgiveness of enemies.",
        7:  "Karmic or past-life relationship; spiritual detachment in marriage; partner from past life; possible separation or renunciation.",
        8:  "Deep occult wisdom; past-life transformation skills; moksha indicator; spiritual dissolution and rebirth.",
        9:  "Past-life spiritual attainment; detachment from father or guru; intuitive dharma beyond dogma.",
        10: "Past-life professional skills bearing fruit; research or spiritual career; detachment from status and worldly recognition.",
        11: "Past-life gains manifesting; detachment from aspirations; spiritual social circle; fulfilment without attachment.",
        12: "Moksha karaka in 12th — strong liberation indicator; spiritual dissolution; past-life retreat and ashram connection.",
    },
}

# ---------------------------------------------------------------------------
# Aspect effect templates  (planet aspecting a house)
# ---------------------------------------------------------------------------

PLANET_ASPECT_EFFECT: dict[str, str] = {
    "Sun":     "Illuminates and strengthens {topic}; authority, government, and pride influence {house_name}; visibility and recognition.",
    "Moon":    "Emotional sensitivity and fluctuation in {topic}; maternal nurturing energy on {house_name}; intuitive and changeable influence.",
    "Mars":    "Energy, drive, and aggression impact {topic}; conflicts or decisive action around {house_name}; intensified competitiveness.",
    "Mercury": "Intellectual and communicative influence on {topic}; analytical, trading, and writing energy applied to {house_name}.",
    "Jupiter": "Wisdom, expansion, and protection of {topic}; dharmic and prosperous blessing on {house_name}; broad and benevolent influence.",
    "Venus":   "Beauty, harmony, and pleasure enhance {topic}; artistic and relational grace applied to {house_name}; refinement.",
    "Saturn":  "Discipline, delay, and restriction affect {topic}; karmic lessons and durability brought to {house_name}; long-term structure.",
    "Rahu":    "Obsessive amplification and unconventional influence on {topic}; foreign, unusual, or disruptive energy on {house_name}.",
    "Ketu":    "Spiritual detachment and past-life karma affect {topic}; dissolution, psychic, or liberating energy on {house_name}.",
}

# ---------------------------------------------------------------------------
# Special classical rule annotations  (planet, kind, house) → (name, rating, note)
# ---------------------------------------------------------------------------
# kind: "occupant" or "aspect"

SPECIAL_RULES: dict[tuple[str, str, int], tuple[str, str, str]] = {
    # Kuja Dosha positions
    ("Mars", "occupant", 1):  ("Kuja Dosha", "mixed",   "Mars in Lagna forms Kuja Dosha; marital complications possible unless Mars is in own/exalted sign or mutual exchange applies."),
    ("Mars", "occupant", 4):  ("Kuja Dosha", "mixed",   "Mars in 4th forms Kuja Dosha; domestic conflicts and land disputes possible."),
    ("Mars", "occupant", 7):  ("Kuja Dosha", "concern", "Mars in 7th forms Kuja Dosha; marital tension, passionate but combative partnerships; mitigated if Mars is exalted, own sign, or both partners have Kuja Dosha."),
    ("Mars", "occupant", 8):  ("Kuja Dosha", "concern", "Mars in 8th forms Kuja Dosha; accidents, surgeries, and transformative crises possible; longevity may require care."),
    ("Mars", "occupant", 12): ("Kuja Dosha", "mixed",   "Mars in 12th forms Kuja Dosha; marital complications through isolation or foreign-related issues."),
    # Digbala (directional strength)
    ("Sun",     "occupant", 10): ("Digbala — Sun", "favorable", "Sun gains Digbala (directional strength) in the 10th house — maximum career authority and leadership potential."),
    ("Moon",    "occupant", 4):  ("Digbala — Moon", "favorable","Moon gains Digbala in the 4th house — deeply nourishing domestic life, devoted mother, and emotional contentment."),
    ("Mars",    "occupant", 10): ("Digbala — Mars", "favorable","Mars gains Digbala in the 10th house — exceptional executive drive, physical authority, and career in action-oriented field."),
    ("Mercury", "occupant", 1):  ("Digbala — Mercury", "favorable","Mercury gains Digbala in the Lagna — amplified intellectual presence, communication prowess, and youthful energy."),
    ("Jupiter", "occupant", 1):  ("Digbala — Jupiter", "favorable","Jupiter gains Digbala in the Lagna — wisdom, dharma, and benevolence radiate through the personality; Hamsa yoga potential."),
    ("Venus",   "occupant", 4):  ("Digbala — Venus", "favorable","Venus gains Digbala in the 4th house — beautiful, comfortable home; domestic pleasures and luxury; artistic domestic life."),
    ("Saturn",  "occupant", 7):  ("Digbala — Saturn", "mixed",    "Saturn gains Digbala in the 7th house — discipline and structure in partnerships; delayed but long-lasting marriage."),
    # Benefic aspects on 7th
    ("Jupiter", "aspect", 7):    ("Jupiter's Blessing on 7th", "favorable",  "Jupiter aspecting 7th blesses marriage with wisdom, dharma, and prosperity; indicates a well-educated, spiritual, or benevolent spouse."),
    ("Venus",   "aspect", 7):    ("Venus Aspecting 7th", "favorable",         "Venus aspecting 7th enhances romance, beauty, and harmony in partnerships; refined and artistic marital influence."),
    # Malefic aspects on 7th
    ("Saturn",  "aspect", 7):    ("Saturn Restricting 7th", "concern",        "Saturn aspecting 7th delays marriage and brings seriousness, age difference, or restriction to partnerships; long-lasting once formed."),
    ("Mars",    "aspect", 7):    ("Mars Agitating 7th", "mixed",              "Mars aspecting 7th introduces passion and conflict into partnerships; energetic spouse but possible marital aggression."),
    ("Rahu",    "aspect", 7):    ("Rahu Shadowing 7th", "mixed",              "Rahu aspecting 7th brings unconventional, foreign, or obsessive partnership energy; unusual marriage circumstances."),
    # Saturn career aspects
    ("Saturn",  "aspect", 10):   ("Saturn Structuring Career", "favorable",   "Saturn aspecting 10th brings disciplined, methodical career success; government and organizational roles favoured; Sasa yoga element."),
    ("Jupiter", "aspect", 10):   ("Jupiter Blessing Career", "favorable",     "Jupiter aspecting 10th brings dharmic recognition and career expansion; teaching, law, religion, or advisory roles elevated."),
    # Jupiter's great aspects
    ("Jupiter", "aspect", 1):    ("Jupiter Blessing Lagna", "favorable",      "Jupiter aspecting Lagna endows wisdom, generosity, and dharmic character; protection of health and personality."),
    ("Jupiter", "aspect", 5):    ("Jupiter Blessing 5th", "favorable",        "Jupiter aspecting 5th blesses children, intellect, and spiritual creativity; Purvapunya (past-life merit) activated."),
    ("Jupiter", "aspect", 9):    ("Jupiter Blessing 9th", "favorable",        "Jupiter aspecting 9th deepens dharma, luck, and spiritual fortune; father and guru connections blessed."),
    # Venus in 7th
    ("Venus",   "occupant", 7):  ("Venus in Kendra", "favorable",             "Venus in 7th (its Kendra) gives a beautiful, artistic, and harmonious spouse; excellent for partnerships and marriage quality."),
    # Rahu/Ketu in 7th
    ("Rahu",    "occupant", 7):  ("Rahu in 7th", "mixed",                     "Rahu in 7th creates unconventional or foreign spouse; obsessive attraction; unusual or cross-cultural marriage."),
    ("Ketu",    "occupant", 7):  ("Ketu in 7th", "mixed",                     "Ketu in 7th indicates a past-life karmic partner; spiritual or karmic relationship; possible renunciation or detachment in marriage."),
    # Saturn in 7th
    ("Saturn",  "occupant", 7):  ("Saturn in 7th", "mixed",                   "Saturn in 7th delays marriage and creates a serious, disciplined, or older spouse; structured but enduring bond once formed."),
    # Sun in 7th
    ("Sun",     "occupant", 7):  ("Sun in 7th — Ego in Partnerships", "mixed","Sun in 7th creates a dominant or egoistic spouse; ego conflicts possible but partner has status and authority."),
    # Jupiter aspects 4th
    ("Jupiter", "aspect", 4):    ("Jupiter Blessing Home", "favorable",        "Jupiter aspecting 4th brings wisdom, prosperity, and happiness to domestic life; fortunate property and spiritual mother."),
}

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

_RATING_SCORE: dict[str, float] = {
    "favorable": 1.0, "ok": 0.5, "mixed": 0.0, "concern": -1.0,
}

_DIGNITY_BONUS: dict[str, float] = {
    "exalted": 0.5, "own_sign": 0.4, "own sign": 0.4,
    "friendly": 0.2, "neutral": 0.0,
    "enemy": -0.2, "debilitated": -0.5,
    "neechabhanga": 0.1,
}

_FUNCTIONAL_BONUS: dict[str, float] = {
    "yogakaraka": 0.5, "benefic": 0.3,
    "neutral": 0.0, "malefic": -0.3,
}


def _planet_base_score(planet: str, fn_role: str, dignity: str) -> float:
    nat = NATURAL_QUALITY.get(planet, "neutral")
    nat_score = 0.3 if nat == "benefic" else (-0.3 if nat == "malefic" else 0.0)
    fn_score   = _FUNCTIONAL_BONUS.get(fn_role, 0.0)
    dig_score  = _DIGNITY_BONUS.get((dignity or "").lower(), 0.0)
    return nat_score + fn_score + dig_score


def _net_assessment(items: list[dict]) -> tuple[str, float]:
    if not items:
        return "ok", 0.5
    total = sum(_planet_base_score(it["planet"], it.get("functional_role","neutral"), it.get("dignity","neutral")) for it in items)
    avg = total / len(items)
    if avg >= 0.5:
        return "favorable", round(0.5 + min(avg, 0.5), 2)
    if avg >= 0.1:
        return "ok", round(0.5 + avg * 0.5, 2)
    if avg >= -0.2:
        return "mixed", round(0.5 + avg * 0.5, 2)
    return "concern", round(max(0.0, 0.5 + avg), 2)


# ---------------------------------------------------------------------------
# Main computation
# ---------------------------------------------------------------------------

def compute_house_influence(bundle, features: dict) -> list[dict]:
    """Return a list of 12 house-influence dicts (one per house 1-12).

    Each dict contains:
      house, rasi, bhava_name, significance,
      occupants (list of enriched dicts),
      aspects (list of enriched dicts),
      net_rating, net_score.
    """
    matrix   = features.get("drishti", {}).get("matrix", [])
    planets  = features.get("planets", {})
    fn_map   = features.get("functional_nature", {}).get("planets", {})
    houses_f = features.get("houses", {})

    result: list[dict] = []
    for row in matrix:
        h          = row["house"]
        rasi       = row.get("rasi", "")
        occupants  = row.get("occupants", [])
        graha_asp  = row.get("graha_drishti", [])
        rashi_asp  = row.get("rashi_drishti", [])
        double_asp = row.get("double_aspect", [])
        topic, bhava = HOUSE_TOPICS.get(h, ("", ""))
        short_topic  = topic.split(",")[0].lower()

        # --- occupant analysis ---
        occ_list: list[dict] = []
        for planet in occupants:
            pf      = planets.get(planet, {})
            dignity = pf.get("dignity", "neutral") or "neutral"
            fn_role = fn_map.get(planet, {}).get("role", "neutral")
            effect  = PLANET_IN_HOUSE.get(planet, {}).get(h, f"{planet} influences {bhava}.")
            special = SPECIAL_RULES.get((planet, "occupant", h))
            score   = _planet_base_score(planet, fn_role, dignity)
            if score >= 0.5:    rating = "favorable"
            elif score >= 0.1:  rating = "ok"
            elif score >= -0.2: rating = "mixed"
            else:               rating = "concern"
            occ_list.append({
                "planet":         planet,
                "nature":         NATURAL_QUALITY.get(planet, "neutral"),
                "functional_role": fn_role,
                "dignity":        dignity,
                "effect":         effect,
                "rating":         rating,
                "special_rule":   special[0] if special else None,
                "special_rating": special[1] if special else None,
                "special_note":   special[2] if special else None,
            })

        # --- aspect analysis ---
        all_aspectors = sorted(set(graha_asp) | set(rashi_asp))
        asp_list: list[dict] = []
        for planet in all_aspectors:
            pf      = planets.get(planet, {})
            dignity = pf.get("dignity", "neutral") or "neutral"
            fn_role = fn_map.get(planet, {}).get("role", "neutral")
            asp_type = "double" if planet in double_asp else ("graha" if planet in graha_asp else "rashi")
            template = PLANET_ASPECT_EFFECT.get(planet, "Influences {topic} and {house_name}.")
            effect   = template.format(topic=short_topic, house_name=f"H{h} ({bhava})")
            special  = SPECIAL_RULES.get((planet, "aspect", h))
            score    = _planet_base_score(planet, fn_role, dignity)
            # Double aspect counts with 1.5× weight in net scoring but reported simply here
            if score >= 0.5:    rating = "favorable"
            elif score >= 0.1:  rating = "ok"
            elif score >= -0.2: rating = "mixed"
            else:               rating = "concern"
            asp_list.append({
                "planet":         planet,
                "aspect_type":    asp_type,
                "nature":         NATURAL_QUALITY.get(planet, "neutral"),
                "functional_role": fn_role,
                "dignity":        dignity,
                "effect":         effect,
                "rating":         rating,
                "special_rule":   special[0] if special else None,
                "special_rating": special[1] if special else None,
                "special_note":   special[2] if special else None,
            })

        net_rating, net_score = _net_assessment(occ_list + asp_list)

        result.append({
            "house":        h,
            "rasi":         rasi,
            "bhava_name":   bhava,
            "significance": topic,
            "occupants":    occ_list,
            "aspects":      asp_list,
            "net_rating":   net_rating,
            "net_score":    net_score,
            "is_empty":     len(occupants) == 0 and len(all_aspectors) == 0,
        })

    return result
