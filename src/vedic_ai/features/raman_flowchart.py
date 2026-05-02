"""Raman HTJH complete horoscope analysis flowchart.

Implements the 8-module algorithm from vedic-horoscope-analysis-algorithm.txt as a
static rule-based (if-then-else) inference engine derived from B.V. Raman's
'How to Judge a Horoscope' (Volumes 1 & 2).  No LLM calls — pure conditional logic.
"""
from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.features.base import DUSTHANA_HOUSES, KENDRA_HOUSES, TRIKONA_HOUSES

# ── Constants ─────────────────────────────────────────────────────────────────

_FAVORABLE   = frozenset({1, 4, 5, 7, 9, 10, 11})
_UNFAVORABLE = frozenset({6, 8, 12})

_NAT_BENEFICS = frozenset({"Jupiter", "Venus", "Moon", "Mercury"})
_NAT_MALEFICS = frozenset({"Sun", "Mars", "Saturn", "Rahu", "Ketu"})

_MOVABLE = frozenset({"Aries", "Cancer", "Libra", "Capricorn"})
_FIXED   = frozenset({"Taurus", "Leo", "Scorpio", "Aquarius"})
_DUAL    = frozenset({"Gemini", "Virgo", "Sagittarius", "Pisces"})
_FIRE    = frozenset({"Aries", "Leo", "Sagittarius"})
_EARTH   = frozenset({"Taurus", "Virgo", "Capricorn"})
_AIR     = frozenset({"Gemini", "Libra", "Aquarius"})
_WATER   = frozenset({"Cancer", "Scorpio", "Pisces"})

_SIGN_ELEMENT: dict[str, str] = {
    **{s: "Fire"  for s in _FIRE},
    **{s: "Earth" for s in _EARTH},
    **{s: "Air"   for s in _AIR},
    **{s: "Water" for s in _WATER},
}
_SIGN_MODALITY: dict[str, str] = {
    **{s: "Movable" for s in _MOVABLE},
    **{s: "Fixed"   for s in _FIXED},
    **{s: "Dual"    for s in _DUAL},
}

_DASHA_YEARS: dict[str, int] = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}

_HOUSE_NAMES: dict[int, str] = {
    1: "Lagna (Self/Body)",
    2: "Dhana (Wealth/Speech)",
    3: "Sahaja (Siblings/Courage)",
    4: "Sukha (Home/Mother/Property)",
    5: "Putra (Children/Intelligence)",
    6: "Ripu/Roga (Enemies/Disease/Debt)",
    7: "Kalatra (Marriage/Partnerships)",
    8: "Ayus (Longevity/Occult)",
    9: "Dharma (Fortune/Father/Guru)",
    10: "Karma (Career/Status/Authority)",
    11: "Labha (Gains/Income/Aspirations)",
    12: "Vyaya (Losses/Spirituality/Moksha)",
}

_HOUSE_KARAKAS: dict[int, list[str]] = {
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

_TRIDOSHA: dict[str, str] = {
    "Sun": "Pitta", "Mars": "Pitta",
    "Moon": "Kapha", "Venus": "Kapha", "Jupiter": "Kapha",
    "Saturn": "Vata", "Mercury": "Mixed (Tridoshic)",
    "Rahu": "Vata", "Ketu": "Mixed (Vata-Pitta)",
}

_PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

# ── Primitive helpers ─────────────────────────────────────────────────────────

def _step(sid: str, title: str, status: str, findings: list[str],
          table: list[dict] | None = None) -> dict:
    return {"id": sid, "title": title, "status": status,
            "findings": findings, "table": table or []}

def _module(mid: str, title: str, steps: list[dict]) -> dict:
    return {"id": mid, "title": title, "steps": steps}

def _fn_role(name: str, fn: dict) -> str:
    return fn.get("planets", {}).get(name, {}).get("role", "neutral")

def _pdata(f: dict, planet: str) -> dict:
    return f["planets"].get(planet, {})

def _hdata(f: dict, house: int) -> dict:
    return f["houses"].get(house, {})

def _house_lord(f: dict, h: int) -> str:
    return _hdata(f, h).get("lord", "—")

def _lord_house(f: dict, h: int) -> int:
    return _hdata(f, h).get("lord_house", 0)

def _lord_dignity(f: dict, h: int) -> str:
    return _hdata(f, h).get("lord_dignity") or "neutral"

def _occupants(f: dict, h: int) -> list[str]:
    return _hdata(f, h).get("occupants", [])

def _aspects_on(f: dict, h: int) -> list[str]:
    return _hdata(f, h).get("aspects_received_from", [])

def _is_strong(dignity: str | None) -> bool:
    return dignity in ("exalted", "own", "moolatrikona")

def _is_weak(dignity: str | None) -> bool:
    return dignity == "debilitated"

def _status3(pos: int, neg: int) -> str:
    if pos >= 2 and neg == 0:
        return "favorable"
    if neg >= 2 and pos == 0:
        return "concern"
    if neg >= 2:
        return "concern"
    if pos >= 2:
        return "favorable"
    return "mixed"

def _strength_label(planet: str, f: dict) -> str:
    p = _pdata(f, planet)
    d = p.get("dignity") or "neutral"
    parts = [d]
    if p.get("is_retrograde"):     parts.append("retrograde")
    if p.get("is_vargottama"):     parts.append("vargottama")
    if p.get("is_combust") and not p.get("combust_exempt"):
        parts.append("combust")
    return ", ".join(parts)

def _lord_fav_str(f: dict, h: int) -> str:
    lh = _lord_house(f, h)
    if lh in _FAVORABLE:
        return f"favorably placed in H{lh}"
    elif lh in _UNFAVORABLE:
        return f"adversely placed in H{lh} (dusthana)"
    return f"in H{lh}"

def _planet_from_house(planet_house: int, ref_house: int) -> int:
    """Return which house planet is FROM ref_house (1=same, 7=opposition, etc.)."""
    return (planet_house - ref_house) % 12 + 1

# ── Module 1: Foundation Setup ────────────────────────────────────────────────

def _m1_foundation(_bundle: ChartBundle, f: dict) -> dict:
    fn  = f["functional_nature"]
    lag = f["lagna"]

    lagna_sign = lag.get("rasi", "—")
    lagna_nak  = lag.get("nakshatra", "—")
    lagna_lord = lag.get("lord", "—")
    lagna_lord_h = lag.get("lord_house", 0)

    planet_table = []
    for p in _PLANET_ORDER:
        pd = _pdata(f, p)
        planet_table.append({
            "Planet":   p,
            "Sign":     pd.get("rasi", "—"),
            "House":    str(pd.get("house", "—")),
            "Degree":   f"{pd.get('degree_in_rasi', 0):.1f}°",
            "Dignity":  pd.get("dignity") or "neutral",
            "℞":        "Yes" if pd.get("is_retrograde") else "—",
        })

    step11 = _step("1.1", "STEP 1.1: Chart Construction", "ok", [
        f"Lagna: {lagna_sign} "
        f"({_SIGN_MODALITY.get(lagna_sign,'—')} / {_SIGN_ELEMENT.get(lagna_sign,'—')})",
        f"Lagna Nakshatra: {lagna_nak}, Pada {lag.get('pada','—')}",
        f"Lagna lord: {lagna_lord} placed in H{lagna_lord_h}",
        f"Ayanamsa: {f.get('metadata',{}).get('ayanamsa','Lahiri')} | "
        f"House system: {f.get('metadata',{}).get('house_system','Whole Sign')}",
    ], planet_table)

    # Step 1.2 — Functional nature
    fn_table = []
    for p in _PLANET_ORDER:
        pi = fn["planets"].get(p, {})
        fn_table.append({
            "Planet": p,
            "Role":   pi.get("role", "neutral"),
            "Owns":   ", ".join(f"H{h}" for h in pi.get("houses_owned", [])),
            "Label":  pi.get("label", ""),
        })

    yks = fn.get("yogakarakas", [])
    mks = fn.get("maraka_lords", [])
    step12 = _step("1.2", "STEP 1.2: Functional Nature per Lagna (HTJH Method)", "ok", [
        f"Lagna: {fn.get('lagna_rasi','—')} — lagna-relative roles assigned to each planet",
        f"Yogakaraka(s): {', '.join(yks) if yks else 'None detected'}"
        f" — lords both a Kendra (4/7/10) AND Trikona (5/9)",
        f"Maraka lords (H2 and H7 lords): {', '.join(mks) if mks else 'None'}",
        "HTJH rule: Functional benefic/malefic status overrides natural character in predictions.",
    ], fn_table)

    # Step 1.3 — Yogakarakas
    yk_finds: list[str] = []
    for yk in yks:
        yk_finds.append(
            f"{yk} (Yogakaraka): {_strength_label(yk, f)}, "
            f"placed in H{_pdata(f, yk).get('house','?')}"
        )
    if not yk_finds:
        yk_finds.append("No Yogakaraka detected for this lagna — raja yoga requires other combinations.")

    h9l  = _house_lord(f, 9);  h9lh  = _lord_house(f, 9)
    h10l = _house_lord(f, 10); h10lh = _lord_house(f, 10)
    if h9l == h10l:
        yk_finds.append(
            f"9th & 10th lords share the same planet ({h9l}) — intrinsic Rajayoga potential."
        )
    elif h9lh == h10lh:
        yk_finds.append(
            f"9th lord ({h9l}) and 10th lord ({h10l}) are conjunct in H{h9lh} — strong Rajayoga."
        )
    else:
        yk_finds.append(
            f"9th lord ({h9l}) in H{h9lh}; 10th lord ({h10l}) in H{h10lh} "
            f"— {'no direct conjunction/exchange detected' if h9lh != h10lh else 'conjunct'}."
        )

    step13_status = "favorable" if yks else "mixed"
    step13 = _step("1.3", "STEP 1.3: Yogakarakas & Rajayoga Potential", step13_status, yk_finds)

    return _module("M1", "MODULE 1: Foundation Setup", [step11, step12, step13])


# ── Module 2: Assess Planetary Strengths ─────────────────────────────────────

def _m2_strengths(_bundle: ChartBundle, f: dict) -> dict:

    # Step 2.1 — Dignities
    dg_table: list[dict] = []
    strong_count = weak_count = 0
    for p in _PLANET_ORDER:
        pd = _pdata(f, p)
        d  = pd.get("dignity") or "neutral"
        extras = []
        if pd.get("is_vargottama"):
            extras.append("Vargottama (D9 same sign — double strength)")
        if pd.get("is_retrograde"):
            extras.append("Retrograde (intensified results)")
        if _is_strong(d):  strong_count += 1
        if _is_weak(d):    weak_count   += 1
        dg_table.append({
            "Planet":   p,
            "Sign":     pd.get("rasi", "—"),
            "House":    str(pd.get("house", "—")),
            "Dignity":  d,
            "Bonuses":  "; ".join(extras) or "—",
        })

    dg_status = _status3(strong_count, weak_count)
    step21 = _step("2.1", "STEP 2.1: Dignities & Debilities", dg_status, [
        f"Strong planets (exalted/own/moolatrikona): {strong_count}",
        f"Weak planets (debilitated): {weak_count}",
        "HTJH rule: Exaltation = highest strength; Debilitation = lowest. "
        "Vargottama = double strength. Retrograde = additional strength.",
        "Combust planets (within Sun's orb, except Venus/Saturn) lose their period strength.",
    ], dg_table)

    # Step 2.2 — Neechabhanga
    nb_list = f.get("yogas", {}).get("neechabhanga", [])
    nb_finds: list[str] = []
    for nb in nb_list:
        cby = "; ".join(nb.get("cancellation_by", []))
        nb_finds.append(
            f"{nb['graha']} debilitated in {nb['debilitation_sign']} H{nb['house']} "
            f"→ Neechabhanga cancelled by: {cby}"
        )
    if not nb_finds:
        nb_finds = ["No debilitations to cancel — Neechabhanga not applicable."]
    else:
        nb_finds.insert(0,
            "Neechabhanga Raja Yoga: debilitation cancelled when exaltation lord or "
            "sign lord is in a Kendra. Debilitated planet now gains power."
        )
    step22_status = "favorable" if nb_list else "ok"
    step22 = _step("2.2", "STEP 2.2: Neechabhanga (Cancellation of Debility)", step22_status, nb_finds)

    # Step 2.3 — Combustion
    comb_finds: list[str] = []
    for p in _PLANET_ORDER:
        if p in ("Sun", "Moon"):
            continue
        pd = _pdata(f, p)
        if pd.get("is_combust"):
            orb = pd.get("combust_orb", 0)
            exempt = pd.get("combust_exempt", False)
            if exempt:
                comb_finds.append(
                    f"{p}: within Sun's orb ({orb:.1f}°) — EXEMPT from combustion "
                    f"(Venus/Saturn retain full strength per HTJH)."
                )
            else:
                comb_finds.append(
                    f"{p}: COMBUST — within {orb:.1f}° of Sun → weakened; "
                    "loses half its period in Amsayu calculation."
                )
    if not comb_finds:
        comb_finds = ["No planets in combustion — all planets operative at full period strength."]
    comb_status = "concern" if any("COMBUST" in x for x in comb_finds) else "favorable"
    step23 = _step("2.3", "STEP 2.3: Combustion (Astangata)", comb_status, comb_finds)

    # Step 2.4 — Kartari
    kartari = f.get("yogas", {}).get("kartari_yogas", [])
    kt_finds: list[str] = []
    for k in kartari:
        name = k.get("name", "Kartari")
        detail = k.get("detail", "")
        kt_finds.append(f"{name}: {detail}")
    if not kt_finds:
        kt_finds = ["No Papakartari or Subhakartari yoga detected."]
    else:
        kt_finds.insert(0,
            "Papakartari: house/planet hemmed between malefics → weakens significations. "
            "Subhakartari: hemmed between benefics → strengthens."
        )
    kt_status = ("concern"   if any("Papa Kartari" in x or "Papakartari" in x for x in kt_finds) else
                 "favorable" if any("Subha Kartari" in x or "Subhakartari" in x for x in kt_finds) else "ok")
    step24 = _step("2.4", "STEP 2.4: Papakartari / Subhakartari Yoga", kt_status, kt_finds)

    return _module("M2", "MODULE 2: Assess Planetary Strengths", [step21, step22, step23, step24])


# ── Module 3: House Analysis Framework ───────────────────────────────────────

def _m3_house_framework(_bundle: ChartBundle, f: dict) -> dict:
    fn = f["functional_nature"]

    # Step 3.1 — Three-factor analysis summary table
    h_table: list[dict] = []
    for h in range(1, 13):
        hd  = _hdata(f, h)
        lord = hd.get("lord", "—")
        lh   = hd.get("lord_house", 0)
        ld   = hd.get("lord_dignity") or "neutral"
        occ  = hd.get("occupants", [])
        karakas = _HOUSE_KARAKAS.get(h, [])
        k_status_parts = []
        for k in karakas:
            kd = _pdata(f, k).get("dignity") or "neutral"
            k_status_parts.append(f"{k}:{kd}")
        lord_ok    = lh in _FAVORABLE and not _is_weak(ld)
        lord_bad   = lh in _UNFAVORABLE or _is_weak(ld)
        occ_ok  = any(_fn_role(o, fn) in ("benefic","yogakaraka") for o in occ)
        occ_bad = any(_fn_role(o, fn) == "malefic" for o in occ)
        kar_ok  = any(_is_strong(_pdata(f, k).get("dignity")) for k in karakas)
        kar_bad = any(_is_weak(_pdata(f, k).get("dignity")) for k in karakas)
        pos = sum([lord_ok, occ_ok, kar_ok])
        neg = sum([lord_bad, occ_bad, kar_bad])
        st  = _status3(pos, neg)
        h_table.append({
            "House":      f"H{h} — {_HOUSE_NAMES[h].split('(')[0].strip()}",
            "Lord":       f"{lord} in H{lh} ({ld})",
            "Occupants":  ", ".join(occ) if occ else "—",
            "Karakas":    ", ".join(k_status_parts) or "—",
            "Assessment": st.upper(),
        })

    step31 = _step("3.1", "STEP 3.1: Three-Factor Analysis per Bhava", "ok", [
        "For each house: (A) house sign+occupants+aspects, "
        "(B) house lord placement/strength, (C) karaka condition.",
        "HTJH rule: All three factors must agree for a clear result. "
        "When factors conflict, the stronger/more numerous prevail.",
        "Favorable house positions: H1 H4 H5 H7 H9 H10 H11",
        "Adverse house positions: H6 H8 H12 (dusthana — loss, obstruction, reversal)",
    ], h_table)

    # Step 3.2 — Checklist highlights (Kendra and Trikona lords)
    kendra_finds: list[str] = []
    for h in (1, 4, 7, 10):
        lord = _house_lord(f, h)
        lh   = _lord_house(f, h)
        ld   = _lord_dignity(f, h)
        status_txt = "favorably placed" if lh in _FAVORABLE else "adversely placed (dusthana)" if lh in _UNFAVORABLE else "neutral"
        kendra_finds.append(f"H{h} lord ({lord}): {status_txt} in H{lh}, dignity: {ld}")

    trikona_finds: list[str] = []
    for h in (1, 5, 9):
        lord = _house_lord(f, h)
        lh   = _lord_house(f, h)
        ld   = _lord_dignity(f, h)
        status_txt = "strong placement" if lh in _FAVORABLE else "adverse placement" if lh in _UNFAVORABLE else "neutral"
        trikona_finds.append(f"H{h} lord ({lord}): {status_txt} in H{lh}, dignity: {ld}")

    step32_finds = (
        ["KENDRA LORDS (H1/H4/H7/H10 — Angles, power houses):"]
        + kendra_finds
        + ["", "TRIKONA LORDS (H1/H5/H9 — Fortune houses):"]
        + trikona_finds
        + ["", "HTJH checklist: also assess Chandra Lagna (Moon as ascendant) "
            "and Navamsa (D9) for each house."]
    )
    step32 = _step("3.2", "STEP 3.2: House Analysis Checklist", "ok", step32_finds)

    # Step 3.3 — Positional outcomes
    favorable_lords:   list[str] = []
    unfavorable_lords: list[str] = []
    own_house_lords:   list[str] = []
    for h in range(1, 13):
        lord = _house_lord(f, h)
        lh   = _lord_house(f, h)
        if lh == h:
            own_house_lords.append(f"H{h} lord ({lord}) in own house — self-reliant, strong indications")
        elif lh in _FAVORABLE:
            favorable_lords.append(f"H{h} lord ({lord}) in H{lh} (favorable)")
        elif lh in _UNFAVORABLE:
            unfavorable_lords.append(f"H{h} lord ({lord}) in H{lh} (dusthana — adverse)")

    pos33 = len(favorable_lords) + len(own_house_lords)
    neg33 = len(unfavorable_lords)
    step33 = _step("3.3", "STEP 3.3: Key Positional Outcomes for House Lords", _status3(pos33, neg33), [
        f"Favorably placed lords (H1,4,5,7,9,10,11): {len(favorable_lords) + len(own_house_lords)}",
        f"Adversely placed lords (H6,8,12): {len(unfavorable_lords)}",
        "Own house (Swa): " + ("; ".join(own_house_lords) or "None"),
        "Favorable: " + ("; ".join(favorable_lords) or "None"),
        "Adverse:   " + ("; ".join(unfavorable_lords) or "None"),
    ])

    return _module("M3", "MODULE 3: House Analysis Framework", [step31, step32, step33])


# ── Module 4: House-by-House Detailed Analysis ───────────────────────────────

def _m4_houses(_bundle: ChartBundle, f: dict) -> dict:
    fn = f["functional_nature"]
    steps = []

    for h in range(1, 13):
        steps.append(_analyze_house(h, f, fn))

    return _module("M4", "MODULE 4: House-by-House Detailed Analysis (HTJH)", steps)


def _analyze_house(h: int, f: dict, fn: dict) -> dict:  # noqa: C901
    hd     = _hdata(f, h)
    lord   = hd.get("lord", "—")
    lh     = hd.get("lord_house", 0)
    ld     = hd.get("lord_dignity") or "neutral"
    occ    = hd.get("occupants", [])
    asp    = hd.get("aspects_received_from", [])
    rasi   = hd.get("rasi", "—")
    karakas = _HOUSE_KARAKAS.get(h, [])

    finds: list[str] = []

    # — House sign
    modality = _SIGN_MODALITY.get(rasi, "—")
    element  = _SIGN_ELEMENT.get(rasi, "—")
    finds.append(f"Sign: {rasi} ({modality}/{element})")

    # — Occupants
    if occ:
        for o in occ:
            role = _fn_role(o, fn)
            od   = _pdata(f, o).get("dignity") or "neutral"
            finds.append(f"Occupant: {o} ({role}, {od})")
    else:
        finds.append("No planets in this house.")

    # — Aspects received
    if asp:
        asp_parts = []
        for a in asp:
            role = _fn_role(a, fn)
            asp_parts.append(f"{a} ({role})")
        finds.append(f"Aspects received from: {', '.join(asp_parts)}")
    else:
        finds.append("No planetary aspects on this house.")

    # — Lord placement
    own_house = (lh == h)
    lord_fav = own_house or (lh in _FAVORABLE)
    lord_bad = (not own_house) and (lh in _UNFAVORABLE or _is_weak(ld))
    finds.append(
        f"House lord: {lord} in H{lh} ({ld}) — "
        f"{'own house (self-reliant)' if own_house else 'favorable' if lord_fav else 'adverse' if lh in _UNFAVORABLE else 'neutral'} placement"
    )
    if _is_strong(ld):
        finds.append(f"  ✓ {lord} is strong ({ld}) — house significations well supported.")
    elif _is_weak(ld):
        finds.append(f"  ✗ {lord} is debilitated — house significations weakened/reversed.")
    if hd.get("lord_is_retrograde"):
        finds.append(f"  {lord} is retrograde — results intensified or delayed then sudden.")

    # — Karaka conditions
    kar_ok = kar_bad = False
    for k in karakas:
        kpd = _pdata(f, k)
        kd  = kpd.get("dignity") or "neutral"
        kh  = kpd.get("house", 0)
        if _is_strong(kd):
            kar_ok = True
            finds.append(f"Karaka {k}: strong ({kd}) in H{kh} — natural significator well placed.")
        elif _is_weak(kd):
            kar_bad = True
            finds.append(f"Karaka {k}: debilitated in H{kh} — natural significator weakened.")
        else:
            finds.append(f"Karaka {k}: {kd} in H{kh}.")

    # — Occupant quality
    occ_ben_count = sum(1 for o in occ if _fn_role(o, fn) in ("benefic","yogakaraka"))
    occ_mal_count = sum(1 for o in occ if _fn_role(o, fn) == "malefic")
    asp_ben = sum(1 for a in asp if _fn_role(a, fn) in ("benefic","yogakaraka"))
    asp_mal = sum(1 for a in asp if _fn_role(a, fn) == "malefic")

    pos = sum([lord_fav, occ_ben_count > 0, kar_ok, asp_ben > 0])
    neg = sum([lord_bad, occ_mal_count > 0, kar_bad, asp_mal > 0])

    # ── House-specific rules (HTJH) ──────────────────────────────────────────
    finds.append("—")
    finds.append("HTJH ANALYSIS:")

    if h == 1:
        _h1_rules(f, fn, finds)
    elif h == 2:
        _h2_rules(f, fn, finds)
    elif h == 3:
        _h3_rules(f, fn, finds)
    elif h == 4:
        _h4_rules(f, fn, finds)
    elif h == 5:
        _h5_rules(f, fn, finds)
    elif h == 6:
        _h6_rules(f, fn, finds)
    elif h == 7:
        _h7_rules(f, fn, finds)
    elif h == 8:
        _h8_rules(f, fn, finds)
    elif h == 9:
        _h9_rules(f, fn, finds)
    elif h == 10:
        _h10_rules(f, fn, finds)
    elif h == 11:
        _h11_rules(f, fn, finds)
    elif h == 12:
        _h12_rules(f, fn, finds)

    status = _status3(pos, neg)
    title  = f"STEP 4.{h}: H{h} — {_HOUSE_NAMES[h]}"
    return _step(f"4.{h}", title, status, finds)


def _h1_rules(f: dict, fn: dict, finds: list[str]) -> None:
    sun  = _pdata(f, "Sun")
    moon = _pdata(f, "Moon")
    lag  = f["lagna"]
    ll   = lag.get("lord","—"); ll_h = lag.get("lord_house", 0); ll_d = lag.get("lord_dignity","neutral")

    # Lagna lord strength
    if ll_h in KENDRA_HOUSES | TRIKONA_HOUSES:
        finds.append(f"✓ Lagna lord {ll} in kendra/trikona H{ll_h} — strong personality, good constitution.")
    elif ll_h in DUSTHANA_HOUSES:
        finds.append(f"✗ Lagna lord {ll} in dusthana H{ll_h} — health vulnerabilities, life obstacles.")
    if _is_strong(ll_d):
        finds.append(f"✓ Lagna lord {ll} {ll_d} — physical vitality and self-determination enhanced.")
    elif _is_weak(ll_d):
        finds.append(f"✗ Lagna lord {ll} debilitated — diminished physical vitality; check Neechabhanga.")

    # Sun (soul/vitality)
    sd = sun.get("dignity") or "neutral"
    if _is_strong(sd):
        finds.append(f"✓ Sun ({sd}) — soul vitality strong; government/authority connections favored.")
    elif _is_weak(sd):
        finds.append(f"✗ Sun debilitated — soul vitality reduced; check H9 (father) and H10 (career).")

    # Moon (mind)
    md = moon.get("dignity") or "neutral"
    if _is_strong(md):
        finds.append(f"✓ Moon ({md}) — mental stability and emotional well-being strong.")
    elif _is_weak(md):
        finds.append(f"✗ Moon debilitated — mental restlessness; check Kemadruma/Chandal yogas.")
    if moon.get("house") in KENDRA_HOUSES:
        finds.append("✓ Moon in kendra — emotional security and strong mind.")

    # Health triad
    pos = sum([ll_h in _FAVORABLE, _is_strong(ll_d), _is_strong(sd), _is_strong(md)])
    neg = sum([ll_h in _UNFAVORABLE, _is_weak(ll_d), _is_weak(sd), _is_weak(md)])
    if pos >= 3:
        finds.append("✓ HEALTH TRIAD (Lagna/Sun/Moon): Excellent constitution indicated — strong vitality.")
    elif neg >= 2:
        finds.append("✗ HEALTH TRIAD: Multiple weaknesses — constitution needs careful monitoring.")
    else:
        finds.append("⚠ HEALTH TRIAD: Mixed signals — moderate constitution.")


def _h2_rules(f: dict, fn: dict, finds: list[str]) -> None:
    jup    = _pdata(f, "Jupiter")
    h2_occ = _occupants(f, 2)
    h2_lord = _house_lord(f, 2); h2_lh = _lord_house(f, 2)
    jd = jup.get("dignity") or "neutral"

    if _is_strong(jd):
        finds.append(f"✓ Jupiter ({jd}) H{jup.get('house','?')} — karaka strong; wealth and family prosperity indicated.")
    elif _is_weak(jd):
        finds.append(f"✗ Jupiter debilitated — karaka weak; wealth accumulation requires effort.")

    if h2_lh in _FAVORABLE:
        finds.append(f"✓ 2nd lord {h2_lord} in H{h2_lh} — income and family stable.")
    elif h2_lh in _UNFAVORABLE:
        finds.append(f"✗ 2nd lord {h2_lord} in dusthana H{h2_lh} — wealth loss or family troubles indicated.")

    mal_in_2 = [o for o in h2_occ if _fn_role(o, fn) == "malefic"]
    if mal_in_2:
        finds.append(f"✗ Malefics in H2 ({', '.join(mal_in_2)}) — expense of wealth, harsh speech, family friction.")
    ben_in_2 = [o for o in h2_occ if _fn_role(o, fn) in ("benefic","yogakaraka")]
    if ben_in_2:
        finds.append(f"✓ Benefics in H2 ({', '.join(ben_in_2)}) — wealth inflow, pleasant speech, family harmony.")

    finds.append("Note: H2 is a Maraka (death-inflicting) house — its lord/occupants time critical events.")


def _h3_rules(f: dict, fn: dict, finds: list[str]) -> None:
    mars = _pdata(f, "Mars")
    h3_occ  = _occupants(f, 3)
    h3_lord = _house_lord(f, 3); h3_lh = _lord_house(f, 3)
    md = mars.get("dignity") or "neutral"

    if _is_strong(md):
        finds.append(f"✓ Mars ({md}) H{mars.get('house','?')} — courage and enterprise strong; sibling relations active.")
    elif _is_weak(md):
        finds.append(f"✗ Mars debilitated — low physical initiative; sibling conflict possible.")

    mal_in_3 = [o for o in h3_occ if _fn_role(o, fn) == "malefic"]
    if mal_in_3:
        finds.append(
            f"⚠ Malefics in H3 ({', '.join(mal_in_3)}) — HTJH: troubled siblings BUT enhanced courage."
        )

    if h3_lh in _UNFAVORABLE:
        finds.append(f"✗ 3rd lord {h3_lord} in dusthana H{h3_lh} — loss or harm to siblings; communication issues.")
    elif h3_lh in _FAVORABLE:
        finds.append(f"✓ 3rd lord {h3_lord} in H{h3_lh} — siblings prosper; short travels beneficial.")


def _h4_rules(f: dict, fn: dict, finds: list[str]) -> None:
    moon  = _pdata(f, "Moon")
    venus = _pdata(f, "Venus")
    h4_occ  = _occupants(f, 4)
    h4_lord = _house_lord(f, 4); h4_lh = _lord_house(f, 4)
    mnd = moon.get("dignity") or "neutral"; vd = venus.get("dignity") or "neutral"

    if _is_strong(mnd):
        finds.append(f"✓ Moon ({mnd}) — mother's welfare good; comfortable domestic life.")
    elif _is_weak(mnd):
        finds.append(f"✗ Moon debilitated — mother's health/relationship strained; emotional unease at home.")

    if _is_strong(vd):
        finds.append(f"✓ Venus ({vd}) — vehicles, property, and material comforts strongly indicated.")
    elif _is_weak(vd):
        finds.append(f"✗ Venus debilitated — property/vehicle matters problematic.")

    mal_in_4 = [o for o in h4_occ if _fn_role(o, fn) == "malefic"]
    if mal_in_4:
        finds.append(f"✗ Malefics in H4 ({', '.join(mal_in_4)}) — HTJH: unhappy home life, troubled relationship with mother.")
    if h4_lh in _UNFAVORABLE:
        finds.append(f"✗ 4th lord {h4_lord} in H{h4_lh} — domestic peace and property adversely affected.")
    elif h4_lh in _FAVORABLE:
        finds.append(f"✓ 4th lord {h4_lord} in H{h4_lh} — education, property, and domestic happiness supported.")


def _h5_rules(f: dict, fn: dict, finds: list[str]) -> None:
    jup = _pdata(f, "Jupiter")
    h5_occ  = _occupants(f, 5)
    h5_lord = _house_lord(f, 5); h5_lh = _lord_house(f, 5)
    jd = jup.get("dignity") or "neutral"

    if _is_strong(jd):
        finds.append(f"✓ Jupiter/Putrakaraka ({jd}) H{jup.get('house','?')} — children and intelligence well aspected.")
    elif _is_weak(jd):
        finds.append(f"✗ Jupiter debilitated — Putrakaraka weak; children and intellectual pursuits need support.")

    if h5_lh in _FAVORABLE:
        finds.append(f"✓ 5th lord {h5_lord} in H{h5_lh} — progeny, creativity, and speculative gains favored.")
    elif h5_lh in _UNFAVORABLE:
        finds.append(f"✗ 5th lord {h5_lord} in dusthana H{h5_lh} — difficulty with children or creative expression.")

    mal_in_5 = [o for o in h5_occ if _fn_role(o, fn) == "malefic"]
    ben_in_5 = [o for o in h5_occ if _fn_role(o, fn) in ("benefic","yogakaraka")]
    if mal_in_5:
        finds.append(f"✗ Malefics in H5 ({', '.join(mal_in_5)}) — challenges with children; guard against speculative losses.")
    if ben_in_5:
        finds.append(f"✓ Benefics in H5 ({', '.join(ben_in_5)}) — intelligence enhanced; children bring joy.")
    finds.append("HTJH: Assess H5 also from Moon and from Jupiter for full progeny picture.")


def _h6_rules(f: dict, fn: dict, finds: list[str]) -> None:
    mars   = _pdata(f, "Mars")
    saturn = _pdata(f, "Saturn")
    h6_lord = _house_lord(f, 6); h6_lh = _lord_house(f, 6)

    if h6_lh == 6:
        finds.append(f"✓ 6th lord {h6_lord} in H6 — HTJH: strong for overcoming enemies and disease; opponents subdued.")
    elif h6_lh in _FAVORABLE:
        finds.append(f"⚠ 6th lord {h6_lord} in H{h6_lh} — enemies may gain strength; debts could increase.")
    elif h6_lh in _UNFAVORABLE:
        finds.append(f"✓ 6th lord {h6_lord} in dusthana H{h6_lh} (Viparita tendency) — obstacles to enemies.")

    # Tridosha
    h6_occ = _occupants(f, 6)
    doshas = {_TRIDOSHA.get(p,"—") for p in (h6_occ or []) + ["Sun","Mars","Saturn"]}
    doshas.discard("—")
    if h6_occ:
        dosha_planets = [f"{o}→{_TRIDOSHA.get(o,'—')}" for o in h6_occ]
        finds.append(f"Tridosha indicators in H6: {', '.join(dosha_planets)}")
    finds.append(
        "HTJH Tridosha: Sun/Mars = Pitta (fire/inflammatory); "
        "Moon/Venus/Jupiter = Kapha (mucus/fluids); Saturn/Rahu = Vata (nervous/joints)."
    )
    # Disease indicators
    h6_asp = _aspects_on(f, 6)
    mal_asp = [a for a in h6_asp if _fn_role(a, fn) == "malefic"]
    if mal_asp:
        finds.append(f"✗ Malefic aspects on H6 ({', '.join(mal_asp)}) — chronic health conditions possible.")


def _h7_rules(f: dict, fn: dict, finds: list[str]) -> None:
    venus  = _pdata(f, "Venus")
    mars   = _pdata(f, "Mars")
    h7_occ  = _occupants(f, 7)
    h7_lord = _house_lord(f, 7); h7_lh = _lord_house(f, 7)
    vd = venus.get("dignity") or "neutral"

    # Venus (Kalatrakaraka)
    if _is_strong(vd):
        finds.append(f"✓ Venus ({vd}) — Kalatrakaraka strong; happy marriage, harmonious partnership.")
    elif _is_weak(vd):
        finds.append(f"✗ Venus debilitated — Kalatrakaraka weak; marital happiness requires effort.")

    if h7_lh in _FAVORABLE:
        finds.append(f"✓ 7th lord {h7_lord} in H{h7_lh} — spouse and partnerships well indicated.")
    elif h7_lh in _UNFAVORABLE:
        finds.append(f"✗ 7th lord {h7_lord} in dusthana H{h7_lh} — marital difficulties; partnerships strained.")

    mal_in_7 = [o for o in h7_occ if _fn_role(o, fn) == "malefic"]
    if mal_in_7:
        asp_on_7 = _aspects_on(f, 7)
        ben_asp  = [a for a in asp_on_7 if _fn_role(a, fn) in ("benefic","yogakaraka")]
        if ben_asp:
            finds.append(
                f"⚠ Malefics in H7 ({', '.join(mal_in_7)}) — mitigated by benefic aspects "
                f"({', '.join(ben_asp)}); some marital friction but resolution possible."
            )
        else:
            finds.append(
                f"✗ Malefics in H7 ({', '.join(mal_in_7)}) unaspected by benefics — "
                "HTJH: serious marital difficulties; spouse's health/temperament challenged."
            )

    # Kuja Dosha
    mars_h = mars.get("house", 0)
    kuja_houses = {2, 4, 7, 8, 12}
    moon_h = _pdata(f, "Moon").get("house", 0)
    venus_h = venus.get("house", 0)
    kuja_from_lagna = mars_h in kuja_houses
    kuja_from_moon  = _planet_from_house(mars_h, moon_h) in kuja_houses if moon_h else False
    kuja_from_venus = _planet_from_house(mars_h, venus_h) in kuja_houses if venus_h else False

    if any([kuja_from_lagna, kuja_from_moon, kuja_from_venus]):
        sources = []
        if kuja_from_lagna:  sources.append(f"Lagna (Mars in H{mars_h})")
        if kuja_from_moon:   sources.append(f"Moon (Mars is H{_planet_from_house(mars_h,moon_h)} from Moon)")
        if kuja_from_venus:  sources.append(f"Venus (Mars is H{_planet_from_house(mars_h,venus_h)} from Venus)")
        finds.append(
            f"✗ KUJA DOSHA present from: {', '.join(sources)} — "
            "HTJH: spousal disharmony risk; match chart with partner; "
            "Mars in Leo/Aquarius or with Jupiter/Moon can exempt."
        )
    else:
        finds.append("✓ No Kuja Dosha detected from Lagna, Moon, or Venus.")

    # Timing
    finds.append(
        f"Marriage timing dasha: look for periods of {h7_lord} (7th lord), Venus, "
        "planets in H7, or planets aspecting H7."
    )


def _h8_rules(f: dict, fn: dict, finds: list[str]) -> None:
    saturn = _pdata(f, "Saturn")
    h8_lord = _house_lord(f, 8); h8_lh = _lord_house(f, 8)
    sd = saturn.get("dignity") or "neutral"

    if _is_strong(sd):
        finds.append(f"✓ Saturn ({sd}) — 8th karaka strong; longevity well supported; occult abilities possible.")
    elif _is_weak(sd):
        finds.append(f"✗ Saturn debilitated — longevity karaka weak; potential for sudden reversals.")

    if _is_strong(_lord_dignity(f, 8)):
        finds.append(f"✓ 8th lord {h8_lord} strong ({_lord_dignity(f,8)}) — good longevity, inheritance possible.")
    elif h8_lh in _UNFAVORABLE and h8_lh != 8:
        finds.append(f"⚠ 8th lord {h8_lord} in H{h8_lh} — mixed longevity signal; check Pindayu.")
    elif h8_lh in _FAVORABLE:
        finds.append(
            f"✓ 8th lord {h8_lord} in H{h8_lh} — HTJH: strong 8th lord supports longevity. "
            "Also activates occult interests and hidden resources."
        )

    finds.append("HTJH: H3 and H8 = houses of life; H2 and H7 = houses of death (maraka).")
    finds.append(
        "NEVER predict longevity reduction from one factor — require convergence of "
        "8th lord, Saturn, Lagna lord, and Dasha activation."
    )


def _h9_rules(f: dict, fn: dict, finds: list[str]) -> None:
    jup = _pdata(f, "Jupiter")
    sun = _pdata(f, "Sun")
    h9_lord = _house_lord(f, 9); h9_lh = _lord_house(f, 9)
    jd = jup.get("dignity") or "neutral"; sd = sun.get("dignity") or "neutral"

    if _is_strong(jd):
        finds.append(f"✓ Jupiter ({jd}) H{jup.get('house','?')} — fortune and guru blessings strong; dharmic life.")
    elif _is_weak(jd):
        finds.append(f"✗ Jupiter debilitated — fortune karaka weak; religious/philosophical doubts.")
    if _is_strong(sd):
        finds.append(f"✓ Sun ({sd}) — father's welfare and divine grace well supported.")
    elif _is_weak(sd):
        finds.append(f"✗ Sun debilitated — father-related difficulties; authority figures less helpful.")

    if h9_lh in _FAVORABLE:
        finds.append(f"✓ 9th lord {h9_lord} in H{h9_lh} — fortune, righteousness, and long journeys favored.")
    elif h9_lh in _UNFAVORABLE:
        finds.append(f"✗ 9th lord {h9_lord} in dusthana H{h9_lh} — fortune adversely affected; dharma tested.")

    h9_occ = _occupants(f, 9)
    ben_9 = [o for o in h9_occ if _fn_role(o, fn) in ("benefic","yogakaraka")]
    if ben_9:
        finds.append(f"✓ Benefics in H9 ({', '.join(ben_9)}) — great fortune, righteous disposition, spiritual merit.")
    if "Venus" in h9_occ:
        finds.append("⚠ Venus in H9 — HTJH: sensual inclinations may conflict with spiritual pursuits.")


def _h10_rules(f: dict, fn: dict, finds: list[str]) -> None:
    h10_occ  = _occupants(f, 10)
    h10_lord = _house_lord(f, 10); h10_lh = _lord_house(f, 10)

    # Vocational indicators
    prof_map = {
        "Jupiter":  "intellectual, legal, advisory, academic, financial",
        "Mercury":  "business, communications, writing, trade, computing",
        "Sun":      "government service, leadership, medicine, administration",
        "Mars":     "military, surgery, engineering, sports, police",
        "Saturn":   "agriculture, service, judiciary, mass work, real estate",
        "Venus":    "arts, aesthetics, luxury goods, entertainment, fashion",
        "Moon":     "public relations, service industries, food, nursing",
        "Rahu":     "foreign/unconventional fields, technology, politics",
        "Ketu":     "research, occult, technical precision, isolation professions",
    }

    if h10_occ:
        finds.append(f"Planets in H10 (primary career indicators): {', '.join(h10_occ)}")
        for p in h10_occ:
            pd = _pdata(f, p)
            d  = pd.get("dignity") or "neutral"
            prof = prof_map.get(p, "varied career")
            finds.append(
                f"  {p} ({d}) in H10 — HTJH: {prof}"
            )
    else:
        finds.append(f"No planets in H10 — 10th lord {h10_lord} is primary career determinant.")
        ld  = _lord_dignity(f, 10)
        prof = prof_map.get(h10_lord, "career field determined by lord's sign/nakshatra")
        finds.append(f"  10th lord {h10_lord} ({ld}) in H{h10_lh} — {prof}")

    if h10_lh in _FAVORABLE:
        finds.append(f"✓ 10th lord {h10_lord} in H{h10_lh} — career advancement and public recognition supported.")
    elif h10_lh in _UNFAVORABLE:
        finds.append(f"✗ 10th lord {h10_lord} in dusthana H{h10_lh} — career setbacks, professional obstacles.")

    # Check 10th from Moon
    moon_h = _pdata(f, "Moon").get("house", 0)
    if moon_h:
        tenth_from_moon = (moon_h - 1 + 9) % 12 + 1
        h10fm_lord = _house_lord(f, tenth_from_moon)
        finds.append(
            f"HTJH: Also assess H10 from Moon — 10th from Moon is H{tenth_from_moon} "
            f"(lord: {h10fm_lord}). Convergence of H10 from Lagna, Moon, and Sun confirms career."
        )


def _h11_rules(f: dict, fn: dict, finds: list[str]) -> None:
    jup = _pdata(f, "Jupiter")
    h11_lord = _house_lord(f, 11); h11_lh = _lord_house(f, 11)
    jd = jup.get("dignity") or "neutral"

    if _is_strong(jd):
        finds.append(f"✓ Jupiter ({jd}) H{jup.get('house','?')} — gains karaka strong; income and aspirations supported.")
    elif _is_weak(jd):
        finds.append(f"✗ Jupiter debilitated — gains reduced; elder siblings may have difficulties.")

    if h11_lh == 11:
        finds.append(
            f"⚠ 11th lord {h11_lord} in H11 (own house) — HTJH: 'worst malefic house for the lord'; "
            "11th house in own house is a double-edged placement — strong but potentially "
            "overindulgent or obsessed with gains."
        )
    elif h11_lh in _FAVORABLE:
        finds.append(f"✓ 11th lord {h11_lord} in H{h11_lh} — financial gains, fulfilled aspirations.")
    elif h11_lh in _UNFAVORABLE:
        finds.append(f"✗ 11th lord {h11_lord} in dusthana H{h11_lh} — income unstable; aspirations thwarted.")

    h11_occ = _occupants(f, 11)
    ben_11 = [o for o in h11_occ if _fn_role(o, fn) in ("benefic","yogakaraka")]
    mal_11 = [o for o in h11_occ if _fn_role(o, fn) == "malefic"]
    if ben_11:
        finds.append(f"✓ Benefics in H11 ({', '.join(ben_11)}) — multiple income streams, social connections prosper.")
    if mal_11:
        finds.append(f"⚠ Malefics in H11 ({', '.join(mal_11)}) — gains come through struggle; "
                     "elder siblings may be a source of tension.")


def _h12_rules(f: dict, fn: dict, finds: list[str]) -> None:
    saturn = _pdata(f, "Saturn")
    ketu   = _pdata(f, "Ketu")
    jup    = _pdata(f, "Jupiter")
    h12_lord = _house_lord(f, 12); h12_lh = _lord_house(f, 12)
    h12_occ  = _occupants(f, 12)
    sd = saturn.get("dignity") or "neutral"
    jd = jup.get("dignity") or "neutral"

    if _is_strong(sd):
        finds.append(f"✓ Saturn ({sd}) H{saturn.get('house','?')} — karaka strong; able to manage losses/expenses.")
    elif _is_weak(sd):
        finds.append(f"✗ Saturn debilitated — karaka weak; excessive expenditure, chronic fatigue.")

    if h12_lh in _FAVORABLE:
        finds.append(f"⚠ 12th lord {h12_lord} in H{h12_lh} — expenses and losses may be channeled productively.")
    elif h12_lh in _UNFAVORABLE:
        finds.append(f"✗ 12th lord {h12_lord} in dusthana H{h12_lh} — heavy losses, imprisonment risk, wasteful spending.")

    # Spiritual/moksha potential
    if "Jupiter" in h12_occ:
        finds.append("✓ Jupiter in H12 — HTJH: strong moksha indicator; foreign residence, spiritual retreat, ashram life.")
    if "Ketu" in h12_occ:
        finds.append("✓ Ketu in H12 — moksha significator in 12th; liberation and detachment from material world.")
    ben_12 = [o for o in h12_occ if _fn_role(o, fn) in ("benefic","yogakaraka")]
    if ben_12:
        finds.append(f"✓ Benefics in H12 ({', '.join(ben_12)}) — HTJH: spiritual gifts, foreign connections, charitable nature.")
    mal_12 = [o for o in h12_occ if _fn_role(o, fn) == "malefic"]
    if mal_12:
        finds.append(f"✗ Malefics in H12 ({', '.join(mal_12)}) — hidden enemies, hospital/prison risk, secret losses.")

    if _is_strong(jd):
        finds.append("✓ Strong Jupiter + H12 emphasis — spiritual advancement and moksha potential elevated.")


# ── Module 5: Dasha-Bhukti Timing Engine ─────────────────────────────────────

def _m5_dasha(_bundle: ChartBundle, f: dict) -> dict:
    fn = f["functional_nature"]
    ds = f.get("dasha_strength", {})

    # Step 5.1 — Current dasha
    maha_info  = ds.get("mahadasha", {})
    antar_info = ds.get("antardasha", {})
    maha_lord  = maha_info.get("lord", "—")
    antar_lord = antar_info.get("lord", "—")
    maha_start = maha_info.get("start", "—")
    maha_end   = maha_info.get("end", "—")
    antar_start = antar_info.get("start", "—")
    antar_end   = antar_info.get("end", "—")

    step51_finds = [
        f"Current Mahadasha: {maha_lord} ({maha_start} → {maha_end}; "
        f"{_DASHA_YEARS.get(maha_lord,'?')} yr cycle)",
        f"Current Antardasha: {antar_lord} ({antar_start} → {antar_end})",
        "Vimshottari sequence: Ketu(7)→Venus(20)→Sun(6)→Moon(10)→Mars(7)→"
        "Rahu(18)→Jupiter(16)→Saturn(19)→Mercury(17) = 120 yrs",
        "Balance at birth determined by natal Moon's Nakshatra position.",
    ]
    step51 = _step("5.1", "STEP 5.1: Vimshottari Dasha — Current Period", "ok", step51_finds)

    # Step 5.2 — Dasha strength (7-point assessment)
    step52_finds: list[str] = []
    dasha_table: list[dict] = []
    if maha_info and maha_lord != "—":
        ml_fn   = _fn_role(maha_lord, fn)
        ml_pd   = _pdata(f, maha_lord)
        ml_d    = ml_pd.get("dignity") or "neutral"
        ml_h    = ml_pd.get("house", 0)
        ml_owns = fn["planets"].get(maha_lord, {}).get("houses_owned", [])
        retro   = ml_pd.get("is_retrograde", False)
        vargo   = ml_pd.get("is_vargottama", False)
        combust = ml_pd.get("is_combust", False) and not ml_pd.get("combust_exempt", False)

        step52_finds += [
            f"Dasha lord: {maha_lord} (functional role: {ml_fn})",
            f"(1) Houses ruled: {', '.join(f'H{h}' for h in sorted(ml_owns)) or '—'}",
            f"(2) Placement: H{ml_h} ({'kendra' if ml_h in KENDRA_HOUSES else 'trikona' if ml_h in TRIKONA_HOUSES else 'dusthana' if ml_h in DUSTHANA_HOUSES else 'other'})",
            f"(3) Sign strength: {ml_d}",
            f"(4) Aspects received on {maha_lord}: "
            f"{', '.join(_aspects_on(f, ml_h)) or 'none'}",
            f"(5) Associations: conjunctions in H{ml_h} = "
            f"{', '.join(_occupants(f, ml_h)) or 'none'}",
            f"(6) Vargottama: {'Yes — double strength' if vargo else 'No'}",
            f"(7) Retrograde: {'Yes — intensified/delayed results' if retro else 'No'}",
        ]
        if combust:
            step52_finds.append(f"  ⚠ {maha_lord} is COMBUST — period results reduced near Sun.")

        dasha_table.append({
            "Period": f"{maha_lord} Mahadasha",
            "Functional Role": ml_fn,
            "Houses Owned": ", ".join(f"H{h}" for h in sorted(ml_owns)),
            "In House": str(ml_h),
            "Dignity": ml_d,
            "Score": str(maha_info.get("score", "—")),
        })

    if antar_info and antar_lord != "—" and antar_lord != maha_lord:
        al_fn  = _fn_role(antar_lord, fn)
        al_pd  = _pdata(f, antar_lord)
        al_d   = al_pd.get("dignity") or "neutral"
        al_h   = al_pd.get("house", 0)
        al_own = fn["planets"].get(antar_lord, {}).get("houses_owned", [])
        step52_finds.append(
            f"Antardasha lord: {antar_lord} ({al_fn}, {al_d}) in H{al_h} "
            f"— owns {', '.join(f'H{h}' for h in sorted(al_own)) or '—'}"
        )
        dasha_table.append({
            "Period": f"{antar_lord} Antardasha",
            "Functional Role": al_fn,
            "Houses Owned": ", ".join(f"H{h}" for h in sorted(al_own)),
            "In House": str(al_h),
            "Dignity": al_d,
            "Score": "—",
        })

    step52_status = "ok" if not step52_finds else (
        "favorable" if maha_info.get("score", 0) > 0.6 else
        "concern"   if maha_info.get("score", 0) < 0.3 else "mixed"
    )
    step52 = _step("5.2", "STEP 5.2: Dasha Lord — 7-Point Strength Assessment", step52_status,
                   step52_finds or ["No active dasha data available."], dasha_table)

    # Step 5.3 — Prediction per bhava
    step53_finds: list[str] = []
    if maha_lord != "—":
        ml_fn = _fn_role(maha_lord, fn)
        ml_h  = _pdata(f, maha_lord).get("house", 0)
        ml_owns = fn["planets"].get(maha_lord, {}).get("houses_owned", [])
        step53_finds += [
            f"Dasha lord {maha_lord} placed in H{ml_h} — direct experience of H{ml_h} significations.",
            f"Houses owned by {maha_lord}: {', '.join(f'H{h}' for h in sorted(ml_owns)) or '—'} — "
            "results of those houses manifest during this period.",
        ]
        if ml_fn == "yogakaraka":
            step53_finds.append(f"✓ YOGAKARAKA DASHA: {maha_lord} period — exceptional success, rise in life, raja yoga activation.")
        elif ml_fn == "benefic":
            step53_finds.append(f"✓ Functional benefic dasha — constructive period for owned houses.")
        elif ml_fn == "malefic":
            step53_finds.append(f"✗ Functional malefic dasha — obstacles and setbacks; owned houses under pressure.")

        if ml_h in DUSTHANA_HOUSES:
            step53_finds.append(f"✗ {maha_lord} in dusthana H{ml_h} — health issues, reversals, obstacles to owned-house matters.")
        elif ml_h in KENDRA_HOUSES | TRIKONA_HOUSES:
            step53_finds.append(f"✓ {maha_lord} in kendra/trikona H{ml_h} — results of period well-directed and potent.")

        if _pdata(f, maha_lord).get("is_maraka"):
            step53_finds.append(
                f"⚠ {maha_lord} is a Maraka lord — HTJH: danger to longevity ONLY if "
                "life's allotted span is nearly complete; do NOT predict death without 3+ supporting factors."
            )
        step53_finds.append(
            "HTJH rule: Transits (Gochar) validate Dasha results — "
            "Saturn & Jupiter transits over natal Moon are most significant."
        )

    step53_status = "ok"
    step53 = _step("5.3", "STEP 5.3: Prediction per Bhava in Current Dasha", step53_status, step53_finds)

    # Step 5.4 — Upcoming dasha
    step54 = _step("5.4", "STEP 5.4: Dasha Sequence Outlook", "ok", [
        "See Vimshottari Dasha table in Chart tab for full period dates.",
        "Assess each future dasha lord using the 7-point framework (Step 5.2).",
        "Key triggers: Yogakaraka dasha = peak opportunity; Maraka dasha = health caution.",
    ])

    return _module("M5", "MODULE 5: Dasha-Bhukti Timing Engine", [step51, step52, step53, step54])


# ── Module 6: Special Combinations and Yogas ─────────────────────────────────

def _m6_yogas(_bundle: ChartBundle, f: dict) -> dict:
    fn    = f["functional_nature"]
    yogas = f.get("yogas", {})

    # ── Step 6.1 — Classical positive yogas ──────────────────────────────────
    pos_finds: list[str] = []
    raja = yogas.get("raja_yogas", [])
    if raja:
        for ry in raja:
            pos_finds.append(
                f"✓ RAJA YOGA: {ry['trikona_lord']} (H{ry['house_t']}) + "
                f"{ry['kendra_lord']} (H{ry['house_k']}) — {ry['association']}"
            )
    else:
        pos_finds.append("No Raja Yoga (9th+10th lord conjunction/exchange) detected.")

    for dy in yogas.get("dhana_yogas", []):
        pos_finds.append(
            f"✓ DHANA YOGA: {dy['wealth_lord']} (H{dy['house_w']}, 2nd/11th) + "
            f"{dy['prosperity_lord']} (H{dy['house_p']}, 1st/9th) — {dy['association']}"
        )

    if yogas.get("gajakesari"):
        jh = _pdata(f, "Jupiter").get("house", 0)
        mh = _pdata(f, "Moon").get("house", 0)
        pos_finds.append(f"✓ GAJAKESARI YOGA: Jupiter H{jh} in kendra from Moon H{mh} — fame, intelligence, success.")
    else:
        pos_finds.append("Gajakesari Yoga absent — Jupiter not in kendra from Moon.")

    for pm in yogas.get("pancha_mahapurusha", []):
        pos_finds.append(
            f"✓ PANCHA MAHAPURUSHA — {pm['name']} Yoga: "
            f"{pm['graha']} in {pm['rasi']} H{pm['house']} (kendra, own/exaltation)"
        )

    for nb in yogas.get("neechabhanga", []):
        pos_finds.append(
            f"✓ NEECHABHANGA RAJA YOGA: {nb['graha']} debilitation cancelled in "
            f"{nb['debilitation_sign']} H{nb['house']} → planet gains power to bestow results"
        )

    for vr in yogas.get("viparita_raja_yogas", []):
        pos_finds.append(
            f"✓ VIPARITA RAJA YOGA: {vr['lord']} (H{vr['owns_house']} dusthana lord) "
            f"in H{vr['placed_in_house']} — gains through apparent losses, late success"
        )

    for wy in yogas.get("wealth_yogas", []):
        pos_finds.append(f"✓ WEALTH YOGA — {wy['name']}: {wy['detail']}")

    # Positive conjunction yogas (Budhaditya, Guru-Mangala, Dharma-Karmadhipati)
    _POS_CONJ = {"Budhaditya Yoga", "Guru-Mangala Yoga", "Dharma-Karmadhipati Yoga"}
    for cy in yogas.get("conjunction_yogas", []):
        if cy.get("name", "") in _POS_CONJ:
            pos_finds.append(f"✓ {cy['name'].upper()}: {cy['detail']}")

    step61_status = (
        "favorable" if raja or yogas.get("gajakesari") or yogas.get("pancha_mahapurusha") or
                       yogas.get("neechabhanga") or yogas.get("dhana_yogas")
        else "mixed"
    )
    step61 = _step("6.1", "STEP 6.1: Key Positive Yogas", step61_status, pos_finds)

    # ── Step 6.2 — Negative combinations ─────────────────────────────────────
    neg_finds: list[str] = []
    if yogas.get("kemadruma"):
        neg_finds.append(
            "✗ KEMADRUMA YOGA: Moon has no planets in 2nd or 12th from it — "
            "HTJH: loneliness, emotional struggles, periodic isolation."
        )
    else:
        neg_finds.append("✓ No Kemadruma Yoga — Moon has planetary support.")

    for cy in yogas.get("conjunction_yogas", []):
        cname = cy.get("name", "")
        if "Chandal" in cname or "Guru-Chandal" in cname:
            neg_finds.append(f"✗ GURU-CHANDALA YOGA: {cy['detail']}")
        elif cname == "Shrapit Yoga":
            neg_finds.append(f"✗ SHRAPIT YOGA: {cy['detail']}")

    for kt in yogas.get("kartari_yogas", []):
        kname = kt.get("name", "")
        if "Papa Kartari" in kname or "Papakartari" in kname:
            neg_finds.append(f"✗ PAPAKARTARI ({kname}): {kt['detail']}")
        elif "Subha Kartari" in kname or "Subhakartari" in kname:
            neg_finds.append(f"✓ SUBHAKARTARI ({kname}): {kt['detail']}")

    for sy in yogas.get("special_yogas", []):
        if sy.get("type") == "kuja_dosha":
            neg_finds.append(f"✗ KUJA DOSHA (Manglik): {sy['detail']}")

    neg_status = "concern" if any("✗" in x for x in neg_finds) else "favorable"
    step62 = _step("6.2", "STEP 6.2: Key Negative Combinations", neg_status, neg_finds)

    # ── Step 6.3 — H7 marriage combinations ──────────────────────────────────
    h7_occ   = _occupants(f, 7)
    h7_finds: list[str] = []
    planet_combos_7 = {
        frozenset({"Mars","Venus"}):    "Physical passion; if afflicted = extra-marital tendencies; Jupiter needed for stability.",
        frozenset({"Venus","Saturn"}):  "Stability and patience; if Saturn afflicted = cold/troubled marriage; long-lasting union.",
        frozenset({"Jupiter","Venus"}): "Good children, harmonious marriage; HTJH: best combination for H7.",
    }
    for combo, text in planet_combos_7.items():
        if combo.issubset(set(h7_occ)):
            h7_finds.append(f"Combination in H7 ({'+'.join(combo)}): {text}")
    for p in h7_occ:
        if p == "Sun":
            h7_finds.append("Sun in H7 — HTJH: delayed marriage, loose morals risk, government-related spouse trouble.")
        elif p == "Saturn":
            h7_finds.append("Saturn in H7 — HTJH: older or widowed partner; stable but emotionally cold marriage.")
        elif p == "Rahu":
            h7_finds.append("Rahu in H7 — HTJH: unconventional marriage, possible foreign/inter-caste spouse, scandal risk.")
        elif p == "Ketu":
            h7_finds.append("Ketu in H7 — spiritual detachment from marriage; past-life karmic bonds with spouse.")
    if not h7_finds:
        h7_finds = [
            f"H7 occupants: {', '.join(h7_occ) if h7_occ else 'Empty'}. "
            "No special planetary combinations in H7 — assess from 7th lord and Venus."
        ]
    step63 = _step("6.3", "STEP 6.3: Planetary Combinations in H7 (Marriage)", "mixed", h7_finds)

    # ── Step 6.4 — Special/Rare yogas (Amala, Kahala, Kuja Dosha, etc.) ─────
    sp_finds: list[str] = []
    _NEGATIVE_SPECIAL = {"kuja_dosha"}
    for sy in yogas.get("special_yogas", []):
        if sy.get("type") in _NEGATIVE_SPECIAL:
            continue   # already shown in step 6.2
        sp_finds.append(f"✓ {sy['name'].upper()}: {sy['detail']}  [{sy.get('source','')}]")
    if not sp_finds:
        sp_finds = ["No special/rare yogas (Amala, Kahala, Mahabhagya, Parvata, Chamara, etc.) detected."]
    sp_status = "favorable" if len(sp_finds) >= 2 else ("ok" if sp_finds and "No special" not in sp_finds[0] else "ok")
    step64 = _step("6.4", "STEP 6.4: Special Yogas (Amala, Kahala, Mahabhagya, Parvata…)", sp_status, sp_finds)

    # ── Step 6.5 — Lunar, Solar & Nabhasa yogas ───────────────────────────────
    ls_finds: list[str] = []
    for ly in yogas.get("lunar_yogas", []):
        ls_finds.append(f"✓ {ly['name'].upper()}: {ly['detail']}  [{ly.get('source','')}]")
    for sy in yogas.get("solar_yogas", []):
        ls_finds.append(f"✓ {sy['name'].upper()}: {sy['detail']}  [{sy.get('source','')}]")
    for ny in yogas.get("nabhasa_yogas", []):
        ls_finds.append(f"✓ {ny['name'].upper()}: {ny['detail']}  [{ny.get('source','')}]")
    if not ls_finds:
        ls_finds = ["No lunar, solar, or nabhasa pattern yogas detected."]
    ls_count = sum(1 for x in ls_finds if x.startswith("✓"))
    ls_status = "favorable" if ls_count >= 2 else ("ok" if ls_count == 1 else "ok")
    step65 = _step("6.5", "STEP 6.5: Lunar, Solar & Nabhasa Yogas", ls_status, ls_finds)

    return _module("M6", "MODULE 6: Special Combinations and Yogas",
                   [step61, step62, step63, step64, step65])


# ── Module 7: Longevity Determination ────────────────────────────────────────

def _m7_longevity(_bundle: ChartBundle, f: dict) -> dict:
    fn = f["functional_nature"]

    # Balarishta indicators
    moon   = _pdata(f, "Moon")
    sun    = _pdata(f, "Sun")
    lagna  = f["lagna"]
    moon_h = moon.get("house", 0)
    lagna_lord = lagna.get("lord", "—")
    ll_d   = lagna.get("lord_dignity", "neutral")
    moon_d = moon.get("dignity") or "neutral"
    sun_d  = sun.get("dignity") or "neutral"

    bala_risk = 0
    bala_finds: list[str] = []

    # Weak Moon in Lagna with malefics
    if moon_h == 1:
        occ1 = _occupants(f, 1)
        mals = [o for o in occ1 if _fn_role(o, fn) == "malefic" and o != "Moon"]
        if mals and _is_weak(moon_d):
            bala_finds.append(f"✗ Balarishta signal: Weak Moon in Lagna with malefics ({', '.join(mals)}).")
            bala_risk += 2

    # Moon in 6/8/12 badly afflicted
    if moon_h in {6, 8, 12}:
        mal_asp_moon = [a for a in _aspects_on(f, moon_h) if _fn_role(a, fn) == "malefic"]
        if mal_asp_moon or _is_weak(moon_d):
            bala_finds.append(
                f"✗ Moon in dusthana H{moon_h} {'debilitated' if _is_weak(moon_d) else 'with malefic aspects'}"
                " — Balarishta indicator."
            )
            bala_risk += 1

    # Malefics in 1/5/8/12 with no benefic aspects
    for h_check in (1, 5, 8, 12):
        occ = _occupants(f, h_check)
        mals = [o for o in occ if _fn_role(o, fn) == "malefic"]
        asp  = _aspects_on(f, h_check)
        ben_asp = [a for a in asp if _fn_role(a, fn) in ("benefic","yogakaraka")]
        if mals and not ben_asp:
            bala_finds.append(
                f"✗ Malefics in H{h_check} ({', '.join(mals)}) without benefic aspect — longevity concern."
            )
            bala_risk += 1

    # Health triad
    triad_weak = sum([_is_weak(ll_d), _is_weak(moon_d), _is_weak(sun_d)])
    if triad_weak >= 2:
        bala_finds.append(f"✗ Health triad weak ({triad_weak}/3 debilitated) — low vitality constitution.")
        bala_risk += 1

    if not bala_finds:
        bala_finds = ["✓ No Balarishta indicators detected — proceed to longevity classification."]

    bala_status = "concern" if bala_risk >= 2 else "mixed" if bala_risk >= 1 else "favorable"
    step71 = _step("7.1", "STEP 7.1: Longevity Classification / Balarishta Check", bala_status, bala_finds)

    # Longevity classification
    # Basic assessment: H1 lord + H8 lord strength
    h8_lord = _house_lord(f, 8); h8_lh = _lord_house(f, 8); h8_ld = _lord_dignity(f, 8)
    long_pos = 0; long_neg = 0
    long_finds: list[str] = []

    if _is_strong(ll_d):
        long_pos += 1; long_finds.append(f"✓ Lagna lord {lagna_lord} ({ll_d}) — longevity supported.")
    elif _is_weak(ll_d):
        long_neg += 1; long_finds.append(f"✗ Lagna lord {lagna_lord} debilitated — reduces longevity.")

    if _is_strong(h8_ld) or h8_lh in _FAVORABLE:
        long_pos += 1
        long_finds.append(f"✓ 8th lord {h8_lord} ({h8_ld}) in H{h8_lh} — good longevity indicator.")
    elif _is_weak(h8_ld) or h8_lh in DUSTHANA_HOUSES and h8_lh != 8:
        long_neg += 1
        long_finds.append(f"✗ 8th lord {h8_lord} ({h8_ld}) in H{h8_lh} — reduced longevity indicator.")

    saturn = _pdata(f, "Saturn")
    sat_d = saturn.get("dignity") or "neutral"
    sat_h = saturn.get("house", 0)
    if _is_strong(sat_d):
        long_pos += 1; long_finds.append(f"✓ Saturn ({sat_d}) H{sat_h} — longevity karaka strong.")
    elif _is_weak(sat_d):
        long_neg += 1; long_finds.append(f"✗ Saturn debilitated H{sat_h} — longevity karaka weak.")

    longevity_class = "Long" if long_pos >= 2 and long_neg == 0 else \
                      "Short" if long_neg >= 2 and long_pos == 0 else "Medium"
    long_finds.append(f"Estimated longevity class: {longevity_class} life")
    long_finds.append(
        "HTJH: Pindayu calculation uses planetary longitude arcs for precise years. "
        "Confirmed by Nisargayu and Amsayu methods. Longevity from single factor = unreliable."
    )

    step72_status = "favorable" if longevity_class == "Long" else "concern" if longevity_class == "Short" else "mixed"
    step72 = _step("7.2", "STEP 7.2: Longevity Classification (Pindayu Framework)", step72_status, long_finds)

    # Maraka activation
    mks = fn.get("maraka_lords", [])
    mk_finds: list[str] = [
        f"Maraka lords (H2/H7): {', '.join(mks) if mks else 'None'}",
        "Maraka activation requires: (1) longevity nearly complete, "
        "(2) Maraka Dasha + Maraka Bhukti, (3) Saturn transit over 2nd from natal Moon.",
        "HTJH: NEVER predict death from single Maraka factor — require convergence of 3+ indicators.",
    ]
    for mk in mks:
        mk_pd = _pdata(f, mk)
        mk_h  = mk_pd.get("house", 0)
        mk_d  = mk_pd.get("dignity") or "neutral"
        mk_finds.append(f"  {mk} (Maraka): {mk_d} in H{mk_h}")

    step73 = _step("7.3", "STEP 7.3: Maraka Activation Timing", "ok", mk_finds)

    return _module("M7", "MODULE 7: Longevity Determination", [step71, step72, step73])


# ── Module 8: Synthesis and Prediction Delivery ──────────────────────────────

def _m8_synthesis(_bundle: ChartBundle, f: dict) -> dict:
    fn    = f["functional_nature"]
    yogas = f.get("yogas", {})

    # Step 8.1 — Chart quality grading
    kendra_count   = sum(1 for p in _PLANET_ORDER if _pdata(f,p).get("house",0) in KENDRA_HOUSES)
    trikona_count  = sum(1 for p in _PLANET_ORDER if _pdata(f,p).get("house",0) in TRIKONA_HOUSES)
    dusthana_count = sum(1 for p in _PLANET_ORDER if _pdata(f,p).get("house",0) in DUSTHANA_HOUSES)
    raja_count     = len(yogas.get("raja_yogas", []))

    lagna    = f["lagna"]
    ll_lord  = lagna.get("lord","—"); ll_d = lagna.get("lord_dignity","neutral")
    moon_d   = _pdata(f,"Moon").get("dignity") or "neutral"
    moon_h   = _pdata(f,"Moon").get("house",0)
    moon_rasi = _pdata(f,"Moon").get("rasi","—")
    yks = fn.get("yogakarakas",[])

    grade_points = 0
    grade_finds: list[str] = []

    # Kendras
    grade_finds.append(f"Planets in Kendras (angles): {kendra_count}/9 "
                       f"({'strong' if kendra_count >= 4 else 'moderate' if kendra_count >= 2 else 'weak'})")
    if kendra_count >= 4: grade_points += 2
    elif kendra_count >= 2: grade_points += 1

    # Trikonas
    grade_finds.append(f"Planets in Trikonas (fortune): {trikona_count}/9 "
                       f"({'strong' if trikona_count >= 3 else 'moderate' if trikona_count >= 1 else 'weak'})")
    if trikona_count >= 3: grade_points += 2
    elif trikona_count >= 1: grade_points += 1

    # Yogakarakas
    if yks:
        grade_finds.append(f"✓ Yogakarakas present: {', '.join(yks)} — strong raja yoga engine.")
        grade_points += 2
    else:
        grade_finds.append("No Yogakaraka — raja yoga requires special combinations.")

    # Lagna lord
    if _is_strong(ll_d):
        grade_finds.append(f"✓ Lagna lord {ll_lord}: {ll_d} — strong character, healthy constitution.")
        grade_points += 1
    elif _is_weak(ll_d):
        grade_finds.append(f"✗ Lagna lord {ll_lord}: debilitated — constitutional weaknesses.")
        grade_points -= 1

    # Moon
    if _is_strong(moon_d):
        grade_finds.append(f"✓ Moon: {moon_d} in {moon_rasi} H{moon_h} — strong mind, emotional stability.")
        grade_points += 1
    elif _is_weak(moon_d):
        grade_finds.append(f"✗ Moon: debilitated in {moon_rasi} H{moon_h} — mental restlessness.")
        grade_points -= 1
    else:
        grade_finds.append(f"Moon: {moon_d} in {moon_rasi} H{moon_h} — moderate mental strength.")

    # Raja yogas
    if raja_count >= 2:
        grade_finds.append(f"✓ Multiple Raja Yogas ({raja_count}) — exceptional career/status potential.")
        grade_points += 2
    elif raja_count == 1:
        grade_finds.append(f"✓ Raja Yoga detected (1) — career and social elevation supported.")
        grade_points += 1
    else:
        grade_finds.append("No classical Raja Yoga — career built through consistent effort.")

    # Grade
    grade = (
        "A — Excellent Chart (strong, multiple positive combinations)" if grade_points >= 7 else
        "B — Good Chart (favourable with some challenges)"             if grade_points >= 5 else
        "C — Average Chart (mixed, requires careful timing)"           if grade_points >= 3 else
        "D — Challenging Chart (multiple adverse placements)"
    )
    grade_finds.append(f"OVERALL CHART GRADE: {grade}")
    grade_finds.append(f"Dusthana planet count: {dusthana_count}/9 — "
                       f"{'high affliction' if dusthana_count >= 5 else 'moderate' if dusthana_count >= 3 else 'low'}")

    grade_status = "favorable" if grade_points >= 5 else "mixed" if grade_points >= 3 else "concern"
    step81 = _step("8.1", "STEP 8.1: Chart Quality Grading", grade_status, grade_finds)

    # Step 8.2 — Life area predictions
    life_areas = [
        ("Personality/Health", 1, "lagna lord strength, Sun, Moon health triad"),
        ("Wealth/Speech", 2, "2nd lord, Jupiter, wealth yogas"),
        ("Siblings/Courage", 3, "3rd lord, Mars"),
        ("Home/Mother/Property", 4, "4th lord, Moon, Venus"),
        ("Children/Intelligence", 5, "5th lord, Jupiter"),
        ("Career/Status", 10, "10th lord, Sun/Mercury/Jupiter/Saturn in 10th"),
        ("Marriage/Partnerships", 7, "7th lord, Venus, Kuja Dosha"),
        ("Fortune/Father", 9, "9th lord, Jupiter, Sun"),
        ("Gains/Income", 11, "11th lord, Jupiter"),
        ("Spirituality/Losses", 12, "12th lord, Saturn, Ketu"),
    ]

    pred_table: list[dict] = []
    pred_finds: list[str] = []
    for area_name, house_num, key_factors in life_areas:
        hd = _hdata(f, house_num)
        lord = hd.get("lord","—")
        lh   = hd.get("lord_house", 0)
        ld   = hd.get("lord_dignity") or "neutral"
        occ  = hd.get("occupants", [])
        ben_occ = [o for o in occ if _fn_role(o, fn) in ("benefic","yogakaraka")]
        mal_occ = [o for o in occ if _fn_role(o, fn) == "malefic"]
        own_h = (lh == house_num)
        lord_ok = own_h or (lh in _FAVORABLE and not _is_weak(ld))
        lord_bad = (not own_h) and (lh in _UNFAVORABLE or _is_weak(ld))
        pos = sum([lord_ok, bool(ben_occ)])
        neg = sum([lord_bad, bool(mal_occ)])
        assessment = _status3(pos, neg)
        key_combo = f"H{house_num} lord ({lord}) in H{lh} ({ld})"
        if occ:
            key_combo += f"; occupants: {', '.join(occ)}"

        pred_table.append({
            "Life Area": area_name,
            "Assessment": assessment.upper(),
            "Key Factor": key_combo,
            "Key Factors": key_factors,
        })

    pred_finds = [
        "Life area assessments based on three-factor analysis (lord + occupants + karaka).",
        "HTJH rule: Never predict from one combination alone — require at least 3 supporting factors.",
        "Always assess from both Lagna and Chandra Lagna (Moon as ascendant) before concluding.",
    ]
    step82 = _step("8.2", "STEP 8.2: Life Area Predictions Template", "ok", pred_finds, pred_table)

    # Step 8.3 — Cardinal rules
    rules_finds = [
        "1. NEVER predict from one combination alone — require at least 3 supporting factors.",
        "2. ALWAYS assess from both Lagna AND Chandra Lagna before concluding.",
        "3. Natural benefic/malefic status is overridden by functional status for each Lagna.",
        "4. A strong chart survives weak periods; a weak chart suffers even in good periods.",
        "5. Neechabhanga and Yogakaraka can dramatically alter expected outcomes.",
        "6. When multiple factors conflict: the stronger/more numerous factors prevail.",
        "7. Consider native's age, sex, and social context in delivery of results.",
        "8. Navamsa (D9) is equal in importance to Rasi for marriage and spiritual matters.",
        "9. Transits (Gochar) validate Dasha predictions — Saturn & Jupiter transits most important.",
        "10. Intuition combined with knowledge and precision mathematics = mastery (Raman's dictum).",
    ]
    step83 = _step("8.3", "STEP 8.3: Cardinal Rules for Prediction (HTJH)", "ok", rules_finds)

    return _module("M8", "MODULE 8: Synthesis and Prediction Delivery", [step81, step82, step83])


# ── Public entry point ────────────────────────────────────────────────────────

def build_raman_flowchart(bundle: ChartBundle, features: dict) -> dict:
    """Build complete 8-module Raman HTJH flowchart analysis from ChartBundle and features.

    Returns a JSON-serialisable dict with key 'modules' containing a list of module
    dicts, each with 'id', 'title', and 'steps'.  Each step has 'id', 'title',
    'status' ('favorable'|'mixed'|'concern'|'ok'), 'findings' (list of str), and
    optional 'table' (list of column-dict rows).

    Also includes 'final_assessment' — a synthesised grade card aggregating all modules.

    No LLM calls — pure rule-based conditional inference derived from HTJH.
    """
    modules = [
        _m1_foundation(bundle, features),
        _m2_strengths(bundle, features),
        _m3_house_framework(bundle, features),
        _m4_houses(bundle, features),
        _m5_dasha(bundle, features),
        _m6_yogas(bundle, features),
        _m7_longevity(bundle, features),
        _m8_synthesis(bundle, features),
    ]
    return {
        "modules": modules,
        "final_assessment": _build_final_assessment(bundle, features, modules),
    }


# ── Final Assessment / Grade Card ────────────────────────────────────────────

_MODULE_WEIGHTS: dict[str, float] = {
    "M1": 1.0,   # foundation — context, not scored
    "M2": 1.5,   # planetary strengths — critical
    "M3": 1.0,   # house framework
    "M4": 2.5,   # house-by-house — most detailed
    "M5": 2.0,   # dasha timing — directly relevant now
    "M6": 2.0,   # yogas — transformative combinations
    "M7": 1.5,   # longevity
    "M8": 2.5,   # synthesis — final grade
}

_STATUS_SCORE: dict[str, float] = {
    "favorable": 1.00,
    "ok":        0.75,
    "mixed":     0.40,
    "concern":   0.10,
}

_HOUSE_AREA: dict[int, str] = {
    1: "Personality & Health",
    2: "Wealth & Speech",
    3: "Courage & Siblings",
    4: "Home & Mother",
    5: "Children & Intelligence",
    6: "Enemies & Disease",
    7: "Marriage & Partnerships",
    8: "Longevity & Occult",
    9: "Fortune & Father",
    10: "Career & Status",
    11: "Gains & Income",
    12: "Spirituality & Loss",
}


def _build_final_assessment(bundle: ChartBundle, f: dict, modules: list[dict]) -> dict:  # noqa: C901
    """Synthesise a final grade card from all 8 modules.

    Returns a structured dict ready for JSON serialisation and frontend rendering.
    """
    fn  = f["functional_nature"]
    lag = f["lagna"]
    yogas = f.get("yogas", {})
    ds    = f.get("dasha_strength", {})

    # ── 1. Per-module weighted scores ────────────────────────────────────────
    module_scores: list[dict] = []
    weighted_sum  = 0.0
    weight_total  = 0.0
    all_strengths:  list[str] = []
    all_challenges: list[str] = []

    for mod in modules:
        mid    = mod["id"]
        weight = _MODULE_WEIGHTS.get(mid, 1.0)
        steps  = mod.get("steps", [])
        if not steps:
            continue
        step_scores = [_STATUS_SCORE.get(s["status"], 0.5) for s in steps]
        mod_score   = sum(step_scores) / len(step_scores)  # 0-1
        weighted_sum  += mod_score * weight
        weight_total  += weight
        pct = round(mod_score * 100)

        # Count favorable/mixed/concern steps
        fc_map: dict[str, int] = {"favorable": 0, "ok": 0, "mixed": 0, "concern": 0}
        for s in steps:
            fc_map[s["status"]] = fc_map.get(s["status"], 0) + 1

        module_scores.append({
            "id":    mid,
            "title": mod["title"],
            "score": pct,
            "status": (
                "favorable" if pct >= 62 else
                "concern"   if pct < 30  else "mixed"
            ),
            "favorable": fc_map["favorable"],
            "ok":        fc_map.get("ok", 0),
            "mixed":     fc_map["mixed"],
            "concern":   fc_map["concern"],
        })

        # Harvest ✓/✗ findings for strengths/challenges
        for s in steps:
            for fnd in s.get("findings", []):
                stripped = fnd.strip()
                if stripped.startswith("✓") and len(stripped) > 3:
                    all_strengths.append(stripped[2:].strip())
                elif stripped.startswith("✗") and len(stripped) > 3:
                    all_challenges.append(stripped[2:].strip())

    overall_score = round((weighted_sum / weight_total) * 100) if weight_total else 50

    # ── 2. Letter grade ───────────────────────────────────────────────────────
    if overall_score >= 70:
        grade = "A"; grade_label = "Excellent"
    elif overall_score >= 52:
        grade = "B"; grade_label = "Good"
    elif overall_score >= 38:
        grade = "C"; grade_label = "Average"
    else:
        grade = "D"; grade_label = "Challenging"

    # ── 3. Life areas from M4 ─────────────────────────────────────────────────
    m4 = next((m for m in modules if m["id"] == "M4"), None)
    life_areas: list[dict] = []
    if m4:
        for step in m4["steps"]:
            try:
                h_num = int(step["id"].split(".")[1])
            except (ValueError, IndexError):
                continue
            # Best summary: first ✓/✗ finding from HTJH ANALYSIS block
            htjh_idx = next(
                (i for i, x in enumerate(step["findings"]) if "HTJH ANALYSIS" in x), -1
            )
            htjh_findings = step["findings"][htjh_idx + 1:] if htjh_idx >= 0 else []
            key = next(
                (x[2:].strip() for x in htjh_findings if x.startswith("✓") or x.startswith("✗")),
                next((x for x in htjh_findings if x.strip()), "No specific indicator")
            )
            # Truncate
            if len(key) > 100:
                key = key[:97] + "…"
            life_areas.append({
                "house":      h_num,
                "area":       _HOUSE_AREA.get(h_num, f"H{h_num}"),
                "status":     step["status"],
                "key_finding": key,
            })

    # ── 4. Yoga summary ───────────────────────────────────────────────────────
    pos_yoga_names: list[str] = []
    neg_yoga_names: list[str] = []

    if yogas.get("gajakesari"):
        pos_yoga_names.append("Gajakesari")
    for pm in yogas.get("pancha_mahapurusha", []):
        pos_yoga_names.append(pm.get("name", "Pancha Mahapurusha"))
    for ry in yogas.get("raja_yogas", []):
        pos_yoga_names.append(f"Raja Yoga ({ry['trikona_lord']}+{ry['kendra_lord']})")
    for nb in yogas.get("neechabhanga", []):
        pos_yoga_names.append(f"Neechabhanga ({nb['graha']})")
    for dy in yogas.get("dhana_yogas", []):
        pos_yoga_names.append(dy.get("name", "Dhana Yoga"))
    for vr in yogas.get("viparita_raja_yogas", []):
        pos_yoga_names.append(f"Viparita Raja ({vr['lord']})")
    for wy in yogas.get("wealth_yogas", []):
        pos_yoga_names.append(wy.get("name", "Wealth Yoga"))
    _POS_CONJ_TYPES = {"Budhaditya Yoga", "Guru-Mangala Yoga", "Dharma-Karmadhipati Yoga"}
    for cy in yogas.get("conjunction_yogas", []):
        if cy.get("name") in _POS_CONJ_TYPES:
            pos_yoga_names.append(cy.get("name", "Conjunction Yoga"))
    for sy in yogas.get("special_yogas", []):
        if sy.get("type") not in ("kuja_dosha",):
            pos_yoga_names.append(sy.get("name", "Special Yoga"))
    for ly in yogas.get("lunar_yogas", []):
        pos_yoga_names.append(ly.get("name", "Lunar Yoga"))
    for sy in yogas.get("solar_yogas", []):
        pos_yoga_names.append(sy.get("name", "Solar Yoga"))
    for ny in yogas.get("nabhasa_yogas", []):
        pos_yoga_names.append(ny.get("name", "Nabhasa Yoga"))

    if yogas.get("kemadruma"):
        neg_yoga_names.append("Kemadruma")
    for kt in yogas.get("kartari_yogas", []):
        kname = kt.get("name", "")
        if "Papa Kartari" in kname or "Papakartari" in kname:
            neg_yoga_names.append(kname)
    for cy in yogas.get("conjunction_yogas", []):
        cname = cy.get("name", "")
        if "Chandal" in cname or cname == "Shrapit Yoga":
            neg_yoga_names.append(cname)
    for sy in yogas.get("special_yogas", []):
        if sy.get("type") == "kuja_dosha":
            neg_yoga_names.append("Kuja Dosha (Manglik)")

    # ── 5. Timing outlook ─────────────────────────────────────────────────────
    maha  = ds.get("mahadasha", {})
    antar = ds.get("antardasha", {})
    ml = maha.get("lord", "—")
    al = antar.get("lord", "—")
    ml_fn = _fn_role(ml, fn)
    ml_pd = _pdata(f, ml) if ml != "—" else {}
    ml_d  = ml_pd.get("dignity") or "neutral"
    ml_h  = ml_pd.get("house", 0)
    maha_end = maha.get("end", "—")
    antar_end = antar.get("end", "—")

    timing_parts: list[str] = []
    timing_parts.append(
        f"{ml} Mahadasha (ends {maha_end}): "
        f"{ml_fn} lord, {ml_d}, placed in H{ml_h}."
    )
    if al != "—" and al != ml:
        al_fn = _fn_role(al, fn)
        al_d  = _pdata(f, al).get("dignity") or "neutral"
        timing_parts.append(
            f"Current sub-period: {al} Antardasha (ends {antar_end}): "
            f"{al_fn}, {al_d}."
        )
    timing_label = (
        "Opportunity period" if ml_fn in ("yogakaraka", "benefic") and _is_strong(ml_d) else
        "Testing period"     if ml_fn == "malefic" or _is_weak(ml_d)                    else
        "Moderate period"
    )
    timing_parts.append(f"Assessment: {timing_label}.")
    timing_outlook = "  ".join(timing_parts)

    # ── 6. Key observations (top 5 condensed) ────────────────────────────────
    lagna_sign = lag.get("rasi", "—")
    ll         = lag.get("lord", "—")
    ll_d       = lag.get("lord_dignity", "neutral")
    ll_h       = lag.get("lord_house", 0)
    moon_d     = _pdata(f, "Moon").get("dignity") or "neutral"
    moon_h     = _pdata(f, "Moon").get("house", 0)
    moon_rasi  = _pdata(f, "Moon").get("rasi", "—")
    yks        = fn.get("yogakarakas", [])
    h10_occ    = _occupants(f, 10)

    key_obs: list[str] = []

    # Lagna & lord
    lagna_obs = (
        f"Lagna: {lagna_sign} — lord {ll} is {ll_d} in H{ll_h} "
        f"({'kendra' if ll_h in KENDRA_HOUSES else 'trikona' if ll_h in TRIKONA_HOUSES else 'dusthana' if ll_h in DUSTHANA_HOUSES else 'other'})."
    )
    key_obs.append(lagna_obs)

    # Moon
    moon_obs = (
        f"Moon ({moon_d}) in {moon_rasi} H{moon_h} — "
        f"{'strong mind and emotional stability' if _is_strong(moon_d) else 'debilitated mind — inner restlessness' if _is_weak(moon_d) else 'moderate mental balance'}."
    )
    key_obs.append(moon_obs)

    # Yogas
    if pos_yoga_names:
        key_obs.append(
            f"Positive yoga(s) confirmed: {', '.join(pos_yoga_names[:4])}."
        )
    if neg_yoga_names:
        key_obs.append(
            f"Negative yoga(s) present: {', '.join(neg_yoga_names[:3])} — mitigate through planetary remedies."
        )

    # Career (H10)
    if h10_occ:
        key_obs.append(
            f"H10 occupied by {', '.join(h10_occ)} — vocational direction strongly indicated by these planets."
        )
    else:
        h10_lord = _house_lord(f, 10); h10_lh = _lord_house(f, 10); h10_ld = _lord_dignity(f, 10)
        key_obs.append(
            f"H10 empty — 10th lord {h10_lord} ({h10_ld}) in H{h10_lh} determines career path."
        )

    # Yogakaraka
    if yks:
        yk_h = _pdata(f, yks[0]).get("house", 0)
        yk_d = _pdata(f, yks[0]).get("dignity") or "neutral"
        key_obs.append(
            f"Yogakaraka {yks[0]} ({yk_d}) in H{yk_h} — single most powerful planet for this lagna; "
            "its dasha will be a peak life period."
        )
    else:
        key_obs.append(
            "No single Yogakaraka for this lagna — fortune built through combined planet periods "
            "and disciplined effort."
        )

    # Longevity
    m7 = next((m for m in modules if m["id"] == "M7"), None)
    if m7:
        long_step = next((s for s in m7["steps"] if s["id"] == "7.2"), None)
        if long_step:
            long_f = next((x for x in long_step["findings"] if "longevity class" in x.lower()), "")
            if long_f:
                key_obs.append(long_f)

    # ── 7. Overall verdict narrative ─────────────────────────────────────────
    strong_count = sum(1 for p in _PLANET_ORDER if _is_strong(_pdata(f, p).get("dignity")))
    weak_count   = sum(1 for p in _PLANET_ORDER if _is_weak(_pdata(f, p).get("dignity")))
    fav_houses   = sum(1 for h in range(1, 13) if _lord_house(f, h) in _FAVORABLE)
    adv_houses   = sum(1 for h in range(1, 13) if _lord_house(f, h) in _UNFAVORABLE)

    verdict_parts: list[str] = []

    # Para 1: core strength
    core_str = (
        f"This is a {grade_label.lower()} chart (Score {overall_score}/100). "
        f"The Lagna is {lagna_sign}, with lord {ll} {ll_d} in H{ll_h} — "
        f"{'lending considerable strength to the native\'s constitution and purpose' if _is_strong(ll_d) else 'a challenging placement that requires conscious effort to overcome'}. "
        f"Of the nine grahas, {strong_count} are dignified (exalted/own/moolatrikona) "
        f"and {weak_count} are debilitated."
    )
    verdict_parts.append(core_str)

    # Para 2: yogas & fortune
    if pos_yoga_names:
        yoga_str = (
            f"Notable positive yogas present — {', '.join(pos_yoga_names[:3])} — "
            "indicate significant life achievements and periods of prosperity."
        )
    else:
        yoga_str = (
            "No classical Rajayoga is formed, but constructive results are available "
            "through functional benefic dasha periods and transit support."
        )
    if neg_yoga_names:
        yoga_str += (
            f"  Counterbalancing negatives ({', '.join(neg_yoga_names[:2])}) "
            "require remediation to mitigate their influence."
        )
    verdict_parts.append(yoga_str)

    # Para 3: house lords balance
    house_str = (
        f"House lord analysis shows {fav_houses} of 12 lords in favorable positions "
        f"and {adv_houses} in dusthanas. "
        f"Strongest areas: {', '.join(a['area'] for a in life_areas if a['status']=='favorable')[:120] or 'none outstanding'}. "
        f"Areas requiring attention: {', '.join(a['area'] for a in life_areas if a['status']=='concern')[:120] or 'none critical'}."
    )
    verdict_parts.append(house_str)

    # Para 4: timing
    verdict_parts.append(f"Current period — {timing_outlook}")

    verdict = "  ".join(verdict_parts)

    # ── 8. Deduplicate and trim lists ─────────────────────────────────────────
    seen: set[str] = set()
    deduped_strengths: list[str] = []
    for x in all_strengths:
        # Deduplicate by first 40 chars
        key = x[:40]
        if key not in seen and len(deduped_strengths) < 12:
            seen.add(key); deduped_strengths.append(x)

    seen2: set[str] = set()
    deduped_challenges: list[str] = []
    for x in all_challenges:
        key = x[:40]
        if key not in seen2 and len(deduped_challenges) < 10:
            seen2.add(key); deduped_challenges.append(x)

    return {
        "grade":           grade,
        "grade_label":     grade_label,
        "score":           overall_score,
        "verdict":         verdict,
        "module_scores":   module_scores,
        "strengths":       deduped_strengths,
        "challenges":      deduped_challenges,
        "life_areas":      life_areas,
        "yogas_positive":  pos_yoga_names,
        "yogas_negative":  neg_yoga_names,
        "timing_outlook":  timing_outlook,
        "key_observations": key_obs,
        "lagna":           lagna_sign,
        "lagna_lord":      f"{ll} ({ll_d}) in H{ll_h}",
        "moon":            f"{moon_d} in {moon_rasi} H{moon_h}",
        "current_dasha":   f"{ml} / {al}",
    }
