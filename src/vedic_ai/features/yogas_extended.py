"""Extended yoga detection — lunar, solar, conjunction, wealth, special, Nabhasa.

Sources used:
  BPHS  — Brihat Parasara Hora Shastra (Parasara)
  PD    — Phaladeepika (Mantreswara)
  SA    — Saravali (Kalyanaraman)
  JT    — Jataka Tattva
  BJ    — Brihat Jataka (Varahamihira)
"""
from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Dignity, Graha, Rasi
from vedic_ai.engines.dignity import RASI_LORDS
from vedic_ai.features.base import DUSTHANA_HOUSES, KENDRA_HOUSES, TRIKONA_HOUSES

# ── Planetary sets ────────────────────────────────────────────────────────────
_BENEFICS  = frozenset({Graha.JUPITER, Graha.VENUS, Graha.MERCURY, Graha.MOON})
_MALEFICS  = frozenset({Graha.SUN, Graha.MARS, Graha.SATURN, Graha.RAHU, Graha.KETU})
_SHADOW    = frozenset({Graha.RAHU, Graha.KETU})
_CLASSICAL = [g for g in Graha if g not in _SHADOW]   # Sun–Saturn (7 planets)

# ── Sign quality sets ─────────────────────────────────────────────────────────
_MOVEABLE  = frozenset({Rasi.ARIES, Rasi.CANCER, Rasi.LIBRA, Rasi.CAPRICORN})
_FIXED     = frozenset({Rasi.TAURUS, Rasi.LEO, Rasi.SCORPIO, Rasi.AQUARIUS})
_DUAL      = frozenset({Rasi.GEMINI, Rasi.VIRGO, Rasi.SAGITTARIUS, Rasi.PISCES})
_ODD_SIGNS = frozenset({Rasi.ARIES, Rasi.GEMINI, Rasi.LEO,
                         Rasi.LIBRA, Rasi.SAGITTARIUS, Rasi.AQUARIUS})
_UPACHAYA  = frozenset({3, 6, 10, 11})
_STRONG    = frozenset({Dignity.EXALTED, Dignity.OWN, Dignity.MOOLATRIKONA})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _h(base: int, offset: int) -> int:
    """1-based circular house arithmetic (1–12)."""
    return (base - 1 + offset) % 12 + 1


def _ph(bundle: ChartBundle) -> dict[str, int]:
    """Return {planet_name: house_number} for all Graha."""
    return {g.value: bundle.d1.planets[g.value].house for g in Graha}


def _sign(bundle: ChartBundle, graha: Graha) -> Rasi:
    return bundle.d1.planets[graha.value].rasi.rasi


def _dignity(bundle: ChartBundle, graha: Graha) -> Dignity | None:
    return bundle.d1.planets[graha.value].dignity


# ─────────────────────────────────────────────────────────────────────────────
# 1. LUNAR YOGAS
# ─────────────────────────────────────────────────────────────────────────────

def detect_lunar_yogas(bundle: ChartBundle) -> list[dict]:
    """Sunapha, Anapha, Durudhara, Adhi, Shakata, Chandra-Mangala."""
    yogas: list[dict] = []
    ph = _ph(bundle)
    moon_h = ph[Graha.MOON.value]
    exclude = {Graha.SUN.value, Graha.MOON.value} | {g.value for g in _SHADOW}

    # Sunapha — planet(s) in 2nd from Moon (BPHS 36.24)
    h2m  = _h(moon_h, 1)
    sp   = [n for n in ph if n not in exclude and ph[n] == h2m]
    if sp:
        yogas.append({
            "name": "Sunapha Yoga", "type": "sunapha",
            "detail": f"{', '.join(sp)} in H{h2m} (2nd from Moon) — self-earned wealth, fame, independent prosperity",
            "source": "BPHS 36.24",
        })

    # Anapha — planet(s) in 12th from Moon (BPHS 36.25)
    h12m = _h(moon_h, 11)
    ap   = [n for n in ph if n not in exclude and ph[n] == h12m]
    if ap:
        yogas.append({
            "name": "Anapha Yoga", "type": "anapha",
            "detail": f"{', '.join(ap)} in H{h12m} (12th from Moon) — charitable, free from disease, graceful",
            "source": "BPHS 36.25",
        })

    # Durudhara — planets in both 2nd AND 12th from Moon (BPHS 36.26)
    if sp and ap:
        yogas.append({
            "name": "Durudhara Yoga", "type": "durudhara",
            "detail": f"Planets in H{h2m} ({', '.join(sp)}) and H{h12m} ({', '.join(ap)}) — wealthy, generous, luxurious",
            "source": "BPHS 36.26",
        })

    # Adhi Yoga — Jupiter/Venus/Mercury in 6th, 7th, or 8th from Moon (BPHS 36.28)
    adhi: list[str] = []
    for g in (Graha.MERCURY, Graha.JUPITER, Graha.VENUS):
        off = (ph[g.value] - moon_h) % 12
        if off in (5, 6, 7):
            adhi.append(g.value)
    if adhi:
        maha = (len(adhi) == 3)
        yogas.append({
            "name": ("Maha " if maha else "") + "Adhi Yoga",
            "type": "maha_adhi" if maha else "adhi",
            "detail": f"{', '.join(adhi)} in 6th/7th/8th from Moon — ministerial status, eminence, authority",
            "source": "BPHS 36.28",
        })

    # Shakata Yoga — Jupiter in 6/8/12 from Moon (affliction, BPHS 36.37)
    jup_off = (ph[Graha.JUPITER.value] - moon_h) % 12
    if jup_off in (5, 7, 11):
        label = {5: "6th", 7: "8th", 11: "12th"}[jup_off]
        yogas.append({
            "name": "Shakata Yoga", "type": "shakata",
            "detail": f"Jupiter in {label} house from Moon (H{ph[Graha.JUPITER.value]}) — fluctuating fortune, wheel of fate",
            "source": "BPHS 36.37",
        })

    # Chandra-Mangala — Moon and Mars in same house (PD 6.32)
    if ph[Graha.MOON.value] == ph[Graha.MARS.value]:
        yogas.append({
            "name": "Chandra-Mangala Yoga", "type": "chandra_mangala",
            "detail": f"Moon and Mars conjunct in H{ph[Graha.MOON.value]} — wealth via trade/business, bold and enterprising",
            "source": "Phaladeepika 6.32",
        })

    return yogas


# ─────────────────────────────────────────────────────────────────────────────
# 2. SOLAR YOGAS
# ─────────────────────────────────────────────────────────────────────────────

def detect_solar_yogas(bundle: ChartBundle) -> list[dict]:
    """Vesi, Vasi, Ubhayachari."""
    yogas: list[dict] = []
    ph = _ph(bundle)
    sun_h = ph[Graha.SUN.value]
    exclude = {Graha.SUN.value, Graha.MOON.value} | {g.value for g in _SHADOW}

    h2s  = _h(sun_h, 1)
    h12s = _h(sun_h, 11)
    vesi = [n for n in ph if n not in exclude and ph[n] == h2s]
    vasi = [n for n in ph if n not in exclude and ph[n] == h12s]

    if vesi:
        yogas.append({
            "name": "Vesi Yoga", "type": "vesi",
            "detail": f"{', '.join(vesi)} in H{h2s} (2nd from Sun) — courageous, wealthy, truthful, hard-working",
            "source": "BPHS 36.17",
        })
    if vasi:
        yogas.append({
            "name": "Vasi Yoga", "type": "vasi",
            "detail": f"{', '.join(vasi)} in H{h12s} (12th from Sun) — fortunate, charitable, robust constitution",
            "source": "BPHS 36.18",
        })
    if vesi and vasi:
        yogas.append({
            "name": "Ubhayachari Yoga", "type": "ubhayachari",
            "detail": "Planets on both sides of Sun — royal attributes, eloquent speech, balanced and dignified life",
            "source": "BPHS 36.19",
        })

    return yogas


# ─────────────────────────────────────────────────────────────────────────────
# 3. CONJUNCTION & PLANETARY YOGAS
# ─────────────────────────────────────────────────────────────────────────────

def detect_conjunction_yogas(
    bundle: ChartBundle,
    lordships: dict[int, dict],
    aspected_by: dict[int, list[str]],
) -> list[dict]:
    """Budhaditya, Guru-Chandala, Guru-Mangala, Shrapit, Dharma-Karmadhipati,
    Subha/Papa Kartari for lagna."""
    yogas: list[dict] = []
    ph = _ph(bundle)

    # Budhaditya Yoga — Sun + Mercury in same house (PD 6)
    if ph[Graha.SUN.value] == ph[Graha.MERCURY.value]:
        yogas.append({
            "name": "Budhaditya Yoga", "type": "budhaditya",
            "detail": f"Sun and Mercury conjunct in H{ph[Graha.SUN.value]} — sharp intellect, scholarly, administrative excellence",
            "source": "Phaladeepika 6",
        })

    # Guru-Mangala Yoga — Jupiter + Mars in mutual kendra (Classical)
    jup_h = ph[Graha.JUPITER.value]
    mar_h = ph[Graha.MARS.value]
    off   = (jup_h - mar_h) % 12
    if off in (0, 3, 6, 9):
        assoc = "conjunct" if off == 0 else f"mutual kendra (H{mar_h}↔H{jup_h})"
        yogas.append({
            "name": "Guru-Mangala Yoga", "type": "guru_mangala",
            "detail": f"Jupiter and Mars {assoc} — courage, generosity, leadership, protective strength",
            "source": "Classical",
        })

    # Guru-Chandala Yoga — Jupiter + Rahu conjunct (affliction)
    if ph[Graha.JUPITER.value] == ph[Graha.RAHU.value]:
        yogas.append({
            "name": "Guru-Chandala Yoga", "type": "guru_chandala",
            "detail": f"Jupiter and Rahu conjunct in H{ph[Graha.JUPITER.value]} — unconventional worldview, wisdom mixed with impurity",
            "source": "Classical",
        })

    # Shrapit Yoga — Saturn + Rahu conjunct (karmic debt)
    if ph[Graha.SATURN.value] == ph[Graha.RAHU.value]:
        yogas.append({
            "name": "Shrapit Yoga", "type": "shrapit",
            "detail": f"Saturn and Rahu conjunct in H{ph[Graha.SATURN.value]} — past-life debt, obstacles that refine the soul",
            "source": "Classical",
        })

    # Dharma-Karmadhipati Yoga — 9th and 10th lords conjunct or mutual 7th (BPHS 36.12)
    h9_lord = lordships[9]["lord"]
    h10_lord = lordships[10]["lord"]
    if h9_lord != h10_lord:
        try:
            h9l_h  = bundle.d1.planets[h9_lord].house
            h10l_h = bundle.d1.planets[h10_lord].house
            conjunct  = (h9l_h == h10l_h)
            mutual7   = (h9l_h - h10l_h) % 12 == 6 or (h10l_h - h9l_h) % 12 == 6
            if conjunct or mutual7:
                yogas.append({
                    "name": "Dharma-Karmadhipati Yoga", "type": "dharma_karma",
                    "detail": (f"{h9_lord} (9L H{h9l_h}) and {h10_lord} (10L H{h10l_h}) "
                               f"{'conjunct' if conjunct else 'mutual 7th'} — career aligned with dharma, righteous authority"),
                    "source": "BPHS 36.12",
                })
        except KeyError:
            pass

    # Subha Kartari Yoga for Lagna — lagna hemmed between benefics (H12 and H2)
    h12_occ = [g for g in Graha if ph[g.value] == 12]
    h2_occ  = [g for g in Graha if ph[g.value] == 2]
    if h12_occ and h2_occ:
        if all(g in _BENEFICS for g in h12_occ) and all(g in _BENEFICS for g in h2_occ):
            yogas.append({
                "name": "Subha Kartari Yoga (Lagna)", "type": "subha_kartari",
                "detail": (f"Lagna hemmed by benefics — H12: {[g.value for g in h12_occ]}, "
                           f"H2: {[g.value for g in h2_occ]} — protected, prosperous, pleasant life"),
                "source": "BPHS",
            })
        elif all(g in _MALEFICS for g in h12_occ) and all(g in _MALEFICS for g in h2_occ):
            yogas.append({
                "name": "Papa Kartari Yoga (Lagna)", "type": "papa_kartari",
                "detail": (f"Lagna hemmed by malefics — H12: {[g.value for g in h12_occ]}, "
                           f"H2: {[g.value for g in h2_occ]} — health and self-esteem challenged"),
                "source": "BPHS",
            })

    return yogas


# ─────────────────────────────────────────────────────────────────────────────
# 4. WEALTH YOGAS
# ─────────────────────────────────────────────────────────────────────────────

def detect_wealth_yogas(
    bundle: ChartBundle,
    lordships: dict[int, dict],
) -> list[dict]:
    """Lakshmi, Saraswati, Vasumati, Kalanidhi, Chandra-Mangala (wealth aspect)."""
    yogas: list[dict] = []
    ph = _ph(bundle)

    # Lakshmi Yoga — 9th lord exalted/own in kendra/trikona, lagna lord strong (BPHS 36.41)
    h9_lord  = lordships[9]["lord"]
    h1_lord  = lordships[1]["lord"]
    try:
        h9l = bundle.d1.planets[h9_lord]
        h1l = bundle.d1.planets[h1_lord]
        if (h9l.house in KENDRA_HOUSES | TRIKONA_HOUSES
                and h9l.dignity in _STRONG
                and h1l.dignity in _STRONG):
            yogas.append({
                "name": "Lakshmi Yoga", "type": "lakshmi",
                "detail": (f"9th lord {h9_lord} ({h9l.dignity.value}) in H{h9l.house}; "
                           f"lagna lord {h1_lord} ({h1l.dignity.value}) — Lakshmi's grace, exceptional wealth"),
                "source": "BPHS 36.41",
            })
    except (KeyError, AttributeError):
        pass

    # Saraswati Yoga — Jupiter/Venus/Mercury all in kendra/trikona/2nd (BPHS 36.39)
    saras = KENDRA_HOUSES | TRIKONA_HOUSES | {2}
    if all(ph[g.value] in saras for g in (Graha.JUPITER, Graha.VENUS, Graha.MERCURY)):
        yogas.append({
            "name": "Saraswati Yoga", "type": "saraswati",
            "detail": (f"Jupiter H{ph[Graha.JUPITER.value]}, Venus H{ph[Graha.VENUS.value]}, "
                       f"Mercury H{ph[Graha.MERCURY.value]} — all in kendra/trikona/2nd — eloquence, artistic mastery, scholarship"),
            "source": "BPHS 36.39",
        })

    # Vasumati Yoga — natural benefics in upachaya from lagna or Moon (BPHS 36.61)
    moon_h    = ph[Graha.MOON.value]
    m_upacha  = frozenset({_h(moon_h, 2), _h(moon_h, 5), _h(moon_h, 9), _h(moon_h, 10)})
    bens3     = (Graha.JUPITER, Graha.VENUS, Graha.MERCURY)
    from_l    = all(ph[g.value] in _UPACHAYA for g in bens3)
    from_m    = all(ph[g.value] in m_upacha  for g in bens3)
    if from_l or from_m:
        ref = "lagna" if from_l else "Moon"
        yogas.append({
            "name": "Vasumati Yoga", "type": "vasumati",
            "detail": f"Jupiter, Venus, Mercury in upachaya houses from {ref} — wealth accumulation, pragmatic success",
            "source": "BPHS 36.61",
        })

    # Kalanidhi Yoga — Jupiter in 2nd or 5th in Mercury/Venus sign (PD 6.37)
    jup_sign = _sign(bundle, Graha.JUPITER)
    jup_h    = ph[Graha.JUPITER.value]
    if jup_h in (2, 5) and jup_sign in {Rasi.GEMINI, Rasi.VIRGO, Rasi.TAURUS, Rasi.LIBRA}:
        yogas.append({
            "name": "Kalanidhi Yoga", "type": "kalanidhi",
            "detail": f"Jupiter in {jup_sign.value} H{jup_h} (Mercury/Venus sign, 2nd/5th) — artistic talent, government honours, wealthy",
            "source": "Phaladeepika 6.37",
        })

    # Dhana Yoga extended — lords of 1+5, 1+9, 2+11, 5+9 conjunct or mutual 7th
    _DHANA_PAIRS = [(1, 5), (1, 9), (2, 11), (5, 9), (2, 9), (1, 11)]
    for h_a, h_b in _DHANA_PAIRS:
        lord_a = lordships[h_a]["lord"]
        lord_b = lordships[h_b]["lord"]
        if lord_a == lord_b:
            continue
        try:
            ha = bundle.d1.planets[lord_a].house
            hb = bundle.d1.planets[lord_b].house
            conjunct = (ha == hb)
            mutual7  = (ha - hb) % 12 == 6 or (hb - ha) % 12 == 6
            if conjunct or mutual7:
                yogas.append({
                    "name": f"Dhana Yoga (H{h_a}+H{h_b})", "type": "dhana_ext",
                    "detail": (f"{lord_a} (H{h_a} lord, H{ha}) and {lord_b} (H{h_b} lord, H{hb}) "
                               f"{'conjunct' if conjunct else 'mutual 7th'} — wealth enhancement"),
                    "source": "BPHS 36.7",
                })
        except KeyError:
            pass

    return yogas


# ─────────────────────────────────────────────────────────────────────────────
# 5. SPECIAL / COMBINATION YOGAS
# ─────────────────────────────────────────────────────────────────────────────

def detect_special_yogas(
    bundle: ChartBundle,
    lordships: dict[int, dict],
    aspected_by: dict[int, list[str]],
) -> list[dict]:
    """Amala, Kahala, Sankha, Parijata, Chamara, Mahabhagya, Parvata,
    Kuja Dosha, Graha Malika, Nipuna."""
    yogas: list[dict] = []
    ph = _ph(bundle)

    # Amala Yoga — 10th from lagna or Moon has ONLY natural benefics (PD 6.22)
    moon_h = ph[Graha.MOON.value]
    for ref_h, ref_label in [(10, "lagna"), (_h(moon_h, 9), f"Moon (H{_h(moon_h,9)})")]:
        occ = [g for g in Graha if ph[g.value] == ref_h]
        if occ and all(g in _BENEFICS for g in occ):
            yogas.append({
                "name": "Amala Yoga", "type": "amala",
                "detail": (f"H{ref_h} (10th from {ref_label}) has only benefics "
                           f"{[g.value for g in occ]} — spotless reputation, ethical career"),
                "source": "Phaladeepika 6.22",
            })
            break

    # Kahala Yoga — 4th and 9th lords in mutual kendra, lagna lord strong (BPHS 36.68)
    h4_lord = lordships[4]["lord"]
    h9_lord = lordships[9]["lord"]
    h1_lord = lordships[1]["lord"]
    try:
        h4l_h  = bundle.d1.planets[h4_lord].house
        h9l_h  = bundle.d1.planets[h9_lord].house
        h1l_d  = bundle.d1.planets[h1_lord].dignity
        if (h4l_h - h9l_h) % 12 in (0, 3, 6, 9) and h1l_d in _STRONG:
            yogas.append({
                "name": "Kahala Yoga", "type": "kahala",
                "detail": (f"{h4_lord} (4L H{h4l_h}) and {h9_lord} (9L H{h9l_h}) mutual kendra; "
                           f"lagna lord {h1_lord} {h1l_d.value} — courageous, authoritative commander"),
                "source": "BPHS 36.68",
            })
    except (KeyError, AttributeError):
        pass

    # Sankha Yoga — 5th and 6th lords in mutual kendra (BPHS 36.69)
    h5_lord = lordships[5]["lord"]
    h6_lord = lordships[6]["lord"]
    try:
        h5l_h = bundle.d1.planets[h5_lord].house
        h6l_h = bundle.d1.planets[h6_lord].house
        if (h5l_h - h6l_h) % 12 in (0, 3, 6, 9):
            yogas.append({
                "name": "Sankha Yoga", "type": "sankha",
                "detail": (f"{h5_lord} (5L H{h5l_h}) and {h6_lord} (6L H{h6l_h}) mutual kendra "
                           "— learned, humane, long-lived, compassionate"),
                "source": "BPHS 36.69",
            })
    except KeyError:
        pass

    # Parijata Yoga — dispositor of lagna lord in kendra/trikona or own/exalted (BPHS 36.40)
    try:
        h1l      = bundle.d1.planets[h1_lord]
        ll_sign  = h1l.rasi.rasi
        disp_g   = RASI_LORDS[ll_sign]
        disp     = bundle.d1.planets[disp_g.value]
        if disp.house in KENDRA_HOUSES | TRIKONA_HOUSES or disp.dignity in _STRONG:
            pos = ("kendra" if disp.house in KENDRA_HOUSES
                   else "trikona" if disp.house in TRIKONA_HOUSES
                   else disp.dignity.value if disp.dignity else "placed")
            yogas.append({
                "name": "Parijata Yoga", "type": "parijata",
                "detail": (f"Dispositor of lagna lord ({disp_g.value}, lord of {ll_sign.value}) "
                           f"in H{disp.house} ({pos}) — deeply respectable, royal favour in later life"),
                "source": "BPHS 36.40",
            })
    except (KeyError, AttributeError):
        pass

    # Chamara Yoga — lagna lord exalted in kendra, aspected by Jupiter (BPHS 36.56)
    try:
        h1l = bundle.d1.planets[h1_lord]
        if (h1l.dignity == Dignity.EXALTED
                and h1l.house in KENDRA_HOUSES
                and Graha.JUPITER.value in aspected_by.get(1, [])):
            yogas.append({
                "name": "Chamara Yoga", "type": "chamara",
                "detail": (f"Lagna lord {h1_lord} exalted in H{h1l.house} (kendra), "
                           "aspected by Jupiter — scholar, orator, king-like authority"),
                "source": "BPHS 36.56",
            })
    except (KeyError, AttributeError):
        pass

    # Mahabhagya Yoga — alignment of Sun, Moon, and lagna (BPHS 36.2)
    sun_sign   = _sign(bundle, Graha.SUN)
    moon_sign  = _sign(bundle, Graha.MOON)
    lagna_sign = bundle.d1.houses[1].rasi
    sun_odd    = sun_sign   in _ODD_SIGNS
    moon_odd   = moon_sign  in _ODD_SIGNS
    lagna_odd  = lagna_sign in _ODD_SIGNS
    day_birth  = ph[Graha.SUN.value] in range(7, 13)  # Sun above horizon

    if sun_odd and moon_odd and lagna_odd and day_birth:
        yogas.append({
            "name": "Mahabhagya Yoga (male)", "type": "mahabhagya_m",
            "detail": (f"Day birth; Sun {sun_sign.value}, Moon {moon_sign.value}, "
                       f"Lagna {lagna_sign.value} — all odd signs — exceptional fortune, leadership"),
            "source": "BPHS 36.2",
        })
    elif not sun_odd and not moon_odd and not lagna_odd and not day_birth:
        yogas.append({
            "name": "Mahabhagya Yoga (female)", "type": "mahabhagya_f",
            "detail": (f"Night birth; Sun {sun_sign.value}, Moon {moon_sign.value}, "
                       f"Lagna {lagna_sign.value} — all even signs — exceptional fortune, beauty, celebrated"),
            "source": "BPHS 36.2",
        })

    # Parvata Yoga — benefics in kendra; H6 and H8 empty or benefics only (BPHS 36.65)
    h6_occ = [g for g in Graha if ph[g.value] == 6]
    h8_occ = [g for g in Graha if ph[g.value] == 8]
    h6_ok  = not h6_occ or all(g in _BENEFICS for g in h6_occ)
    h8_ok  = not h8_occ or all(g in _BENEFICS for g in h8_occ)
    ben_kendra = any(ph[g.value] in KENDRA_HOUSES for g in _BENEFICS)
    if h6_ok and h8_ok and ben_kendra:
        yogas.append({
            "name": "Parvata Yoga", "type": "parvata",
            "detail": "Benefics in kendra; H6 and H8 free of malefics — prosperity, renown, charitable",
            "source": "BPHS 36.65",
        })

    # Nipuna Yoga — Sun + Mercury + another planet in same house (advanced Budhaditya)
    sun_h = ph[Graha.SUN.value]
    mer_h = ph[Graha.MERCURY.value]
    if sun_h == mer_h:
        others_here = [g.value for g in Graha
                       if g not in (Graha.SUN, Graha.MERCURY) and ph[g.value] == sun_h]
        if others_here:
            yogas.append({
                "name": "Nipuna Yoga", "type": "nipuna",
                "detail": (f"Sun, Mercury and {', '.join(others_here)} together in H{sun_h} "
                           "— exceptional expertise, mastery in chosen field"),
                "source": "SA 14.3",
            })

    # Kuja Dosha (Manglik) — Mars in 1/2/4/7/8/12 (Classical)
    mars_h = ph[Graha.MARS.value]
    if mars_h in (1, 2, 4, 7, 8, 12):
        yogas.append({
            "name": "Kuja Dosha (Manglik)", "type": "kuja_dosha",
            "detail": f"Mars in H{mars_h} — strong will, potential delays/challenges in partnerships",
            "source": "Classical",
        })

    # Graha Malika Yoga — planets in 7+ consecutive houses (BPHS 35.25)
    occ_set = set(ph.values())
    best_len, best_start = 0, 1
    for start in range(1, 13):
        run = 0
        for offset in range(12):
            if _h(start, offset) in occ_set:
                run += 1
            else:
                break
        if run > best_len:
            best_len, best_start = run, start
    if best_len >= 7:
        yogas.append({
            "name": "Graha Malika Yoga", "type": "graha_malika",
            "detail": (f"Planets garland {best_len} consecutive houses from H{best_start} "
                       "— broad success, ambitious, multi-domain achievement"),
            "source": "BPHS 35.25",
        })

    return yogas


# ─────────────────────────────────────────────────────────────────────────────
# 6. NABHASA (FIGURE) YOGAS — BPHS Chapter 35
# ─────────────────────────────────────────────────────────────────────────────

def detect_nabhasa_yogas(bundle: ChartBundle) -> list[dict]:
    """Aakrit (form) and Sankhya (number) yogas based on sign distribution
    of the 7 classical planets (Sun–Saturn, excluding Rahu/Ketu)."""
    yogas: list[dict] = []
    ph = _ph(bundle)

    signs_7   = [bundle.d1.planets[g.value].rasi.rasi for g in _CLASSICAL]
    sign_set  = set(signs_7)
    houses_7  = [ph[g.value] for g in _CLASSICAL]

    # ── Aakrit (quality) yogas ──────────────────────────────────────────────
    if all(s in _MOVEABLE for s in signs_7):
        yogas.append({
            "name": "Rajju Yoga", "type": "rajju",
            "detail": "All 7 planets in moveable signs — restless, fond of travel, ever-changing circumstances",
            "source": "BPHS 35.3",
        })
    elif all(s in _FIXED for s in signs_7):
        yogas.append({
            "name": "Musala Yoga", "type": "musala",
            "detail": "All 7 planets in fixed signs — steadfast, wealthy, honoured, set in purpose",
            "source": "BPHS 35.4",
        })
    elif all(s in _DUAL for s in signs_7):
        yogas.append({
            "name": "Nala Yoga", "type": "nala",
            "detail": "All 7 planets in dual signs — versatile, learned, many accomplishments",
            "source": "BPHS 35.5",
        })

    # ── Ashraya (house position) yogas ──────────────────────────────────────
    if all(h in KENDRA_HOUSES for h in houses_7):
        yogas.append({
            "name": "Mala Yoga", "type": "mala",
            "detail": "All 7 planets in angular houses (kendra) — powerful, prosperous, kingly",
            "source": "BPHS 35.8",
        })
    elif all(h in DUSTHANA_HOUSES for h in houses_7):
        yogas.append({
            "name": "Sarpa Yoga", "type": "sarpa",
            "detail": "All 7 planets in dusthana houses (6/8/12) — hardship, cruelty, misfortune (affliction)",
            "source": "BPHS 35.9",
        })

    # ── Sankhya (count) yogas ────────────────────────────────────────────────
    n = len(sign_set)
    SANKHYA: dict[int, tuple[str, str, str]] = {
        1: ("Gola Yoga",  "gola",  "all planets in 1 sign — singular genius, extraordinary in one domain"),
        2: ("Yuga Yoga",  "yuga",  "all planets in 2 signs — strong duality, contrasting life themes"),
        3: ("Shula Yoga", "shula", "all planets in 3 signs — three-pronged nature; obstacles overcome by will"),
        4: ("Kedar Yoga", "kedar", "all planets in 4 signs — prosperity from land, stable agricultural wealth"),
        5: ("Pasha Yoga", "pasha", "all planets in 5 signs — binding ties, large social networks, business"),
        6: ("Dama Yoga",  "dama",  "all planets in 6 signs — many resources and connections, broad life scope"),
        7: ("Veena Yoga", "veena", "all planets in 7 signs — harmonious, musical/artistic ability, happiness"),
    }
    if n in SANKHYA:
        name, ytype, detail = SANKHYA[n]
        yogas.append({
            "name": name, "type": ytype,
            "detail": detail,
            "source": "BPHS 35.13",
        })

    return yogas


# ─────────────────────────────────────────────────────────────────────────────
# 7. KARTARI YOGA PER HOUSE (Step 2.4 extended to all 12 houses)
# ─────────────────────────────────────────────────────────────────────────────

_KARTARI_MALEFICS = frozenset({Graha.SUN, Graha.MARS, Graha.SATURN, Graha.RAHU, Graha.KETU})
_KARTARI_BENEFICS = frozenset({Graha.JUPITER, Graha.VENUS, Graha.MERCURY, Graha.MOON})

_HOUSE_SIGNIF = {
    1: "self/body/vitality", 2: "wealth/speech/family", 3: "courage/siblings",
    4: "home/mother/peace", 5: "intellect/children/dharma", 6: "health/enemies/debt",
    7: "marriage/partnerships", 8: "longevity/transformation", 9: "fortune/father/dharma",
    10: "career/status/authority", 11: "gains/income/aspirations", 12: "losses/liberation",
}


def detect_kartari_yogas(bundle: ChartBundle) -> list[dict]:
    """Detect Subha Kartari and Papa Kartari for all 12 houses.

    A house is hemmed when both its flanking houses (H-1 and H+1) are
    occupied.  Pure malefic flankers → Papa Kartari; pure benefic → Subha.
    """
    yogas: list[dict] = []
    ph = _ph(bundle)

    house_occupants: dict[int, list[Graha]] = {h: [] for h in range(1, 13)}
    for g in Graha:
        house_occupants[ph[g.value]].append(g)

    for house in range(1, 13):
        prev_h = _h(house, -1)
        next_h = _h(house, 1)

        prev_occ = house_occupants[prev_h]
        next_occ = house_occupants[next_h]

        if not prev_occ or not next_occ:
            continue

        prev_mal = [g for g in prev_occ if g in _KARTARI_MALEFICS]
        prev_ben = [g for g in prev_occ if g in _KARTARI_BENEFICS]
        next_mal = [g for g in next_occ if g in _KARTARI_MALEFICS]
        next_ben = [g for g in next_occ if g in _KARTARI_BENEFICS]

        signif = _HOUSE_SIGNIF.get(house, "")

        if prev_mal and next_mal and not prev_ben and not next_ben:
            yogas.append({
                "house": house,
                "name": f"Papa Kartari Yoga (H{house})",
                "type": "papa_kartari",
                "h_before": prev_h,
                "h_after": next_h,
                "malefics_before": [g.value for g in prev_mal],
                "malefics_after":  [g.value for g in next_mal],
                "detail": (
                    f"H{house} ({signif}) hemmed between malefics — "
                    f"H{prev_h}: {', '.join(g.value for g in prev_mal)}; "
                    f"H{next_h}: {', '.join(g.value for g in next_mal)}. "
                    "Significations weakened or obstructed."
                ),
                "source": "BPHS",
            })
        elif prev_ben and next_ben and not prev_mal and not next_mal:
            yogas.append({
                "house": house,
                "name": f"Subha Kartari Yoga (H{house})",
                "type": "subha_kartari",
                "h_before": prev_h,
                "h_after": next_h,
                "benefics_before": [g.value for g in prev_ben],
                "benefics_after":  [g.value for g in next_ben],
                "detail": (
                    f"H{house} ({signif}) hemmed between benefics — "
                    f"H{prev_h}: {', '.join(g.value for g in prev_ben)}; "
                    f"H{next_h}: {', '.join(g.value for g in next_ben)}. "
                    "Significations strengthened and protected."
                ),
                "source": "BPHS",
            })

    return yogas
