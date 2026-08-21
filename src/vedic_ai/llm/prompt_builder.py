"""Build deterministic prompts for the local LLM interpretation call.

The LLM's role is SYNTHESIS ONLY.
All planetary positions, house lords, dasha periods, transit results, and
remedies are pre-computed by the rule engine and gochara engine.  The LLM
must not re-derive, recalculate, or invent any of these — it reads the
ENGINE FINDINGS sections and weaves them into a coherent narrative.
"""

from __future__ import annotations

import json

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.corpus import RetrievedPassage
from vedic_ai.domain.prediction import RuleTrigger
from vedic_ai.features.bhava_analysis import build_bhava_context_block
from vedic_ai.features.raman_flowchart import scope_flowchart_excerpt

# ---------------------------------------------------------------------------
# Section headers
# ---------------------------------------------------------------------------
_SECTION_CONTEXT    = "### NATIVE CONTEXT"
_SECTION_FINDINGS   = "### ENGINE FINDINGS (pre-computed — treat as authoritative)"

# Aliases for backwards compatibility with existing tests
_SECTION_CHART_FACTS = _SECTION_CONTEXT
_SECTION_DERIVED     = _SECTION_FINDINGS
_SECTION_FUNCTIONAL = "### FUNCTIONAL PLANETARY NATURE"
_SECTION_DASHA_STR  = "### DASHA LORD STRENGTH"
_SECTION_VARGA      = "### VARGA (DIVISIONAL) ANALYSIS"
_SECTION_DASHA      = "### DASHA TIMING"
_SECTION_GOCHARA    = "### TRANSIT / GOCHARA CONTEXT (pre-computed — do not re-derive)"
_SECTION_BHAVA      = "### BHAVA ACTIVATION — DASHA + TRANSIT ANALYSIS (pre-computed)"
_SECTION_SHADBALA   = "### SHADBALA — PLANETARY STRENGTH (pre-computed)"
_SECTION_ASHTAKA    = "### ASHTAKAVARGA — TRANSIT BINDU QUALITY (pre-computed)"
_SECTION_FLOWCHART  = "### RAMAN HTJH FLOWCHART (deterministic, book-derived — authoritative, in module priority order)"
_SECTION_RULES      = "### TRIGGERED RULE FINDINGS (engine output)"
_SECTION_PASSAGES   = "### SUPPORTING CLASSICAL PASSAGES"
_SECTION_TASK       = "### YOUR TASK"

# ---------------------------------------------------------------------------
# System instructions
# ---------------------------------------------------------------------------
_INSTRUCTION = """\
You are a Vedic astrology synthesis writer.

ROLE: Narrative synthesis — NOT calculation.
The sections below contain pre-computed findings from a deterministic rule
engine and (if present) a Gochara transit engine.  Your job is to weave these
findings into a clear, coherent interpretation for the requested scope.

STRICT PROHIBITIONS — you must NEVER:
  • Re-derive or re-calculate planetary positions, longitudes, or house placements.
  • Re-derive dasha periods, their lords, or their dates.
  • Suggest remedies, mantras, gemstones, or upayas — these are provided by the
    engine when relevant; do not invent new ones.
  • Introduce any planetary placement, yoga, or dasha not already listed in the
    ENGINE FINDINGS or TRIGGERED RULE FINDINGS sections.
  • Contradict the engine-computed tone (e.g. if a planet is listed as
    "unfavorable", do not reframe it as beneficial).

WHAT YOU SHOULD DO:
  • Read the ENGINE FINDINGS, TRIGGERED RULES, and GOCHARA CONTEXT sections.
  • Identify the 2-4 most significant factors for the requested scope.
  • Synthesize how they interact — especially where dasha timing, natal yogas,
    and current transits converge or conflict.
  • Ground every sentence in a specific finding from the sections below.
  • Reference classical passages only to add context or depth, not to introduce
    new interpretations.

Respond ONLY with a valid JSON object — no markdown fences, no commentary."""

_INSTRUCTION_RAMAN = """\
You are a Vedic astrology synthesis writer trained in the B.V. Raman school.

ROLE: Narrative synthesis — NOT calculation.
The sections below contain pre-computed findings from a deterministic rule
engine and (if present) a Gochara transit engine.  Your job is to weave these
findings into a coherent interpretation using B.V. Raman's method:
examine the relevant house, its lord's placement, occupants, aspects, and
divisional chart confirmation.

STRICT PROHIBITIONS — you must NEVER:
  • Re-derive or re-calculate any planetary position, longitude, or house number.
  • Re-derive dasha periods, their lords, or their dates.
  • Suggest remedies, mantras, gemstones, or upayas — the engine provides these.
  • Introduce any yoga or placement not listed in the ENGINE FINDINGS sections.
  • Contradict the engine-computed tone for any planet or transit.

WHAT YOU SHOULD DO:
  • Use the ENGINE FINDINGS as your factual base.
  • Apply Raman's analytical lens: house lord strength, mutual aspects, varga
    confirmation, and dasha timing.
  • For the requested scope cite the relevant house, its lord, divisional chart
    position, and active dasha — all drawn from the pre-computed sections.
  • Synthesize how natal strengths interact with the current dasha and transits.

Respond ONLY with a valid JSON object — no markdown fences, no commentary."""

# Scope → priority divisional charts
_SCOPE_VARGAS: dict[str, list[str]] = {
    "personality":   ["D9", "D1"],
    "career":        ["D10", "D9"],
    "relationships": ["D9", "D7"],
    "health":        ["D6", "D8", "D30"],
    # Bhava scopes use D9 + D1 by default; high-significance bhavas get specific charts
    "bhava_1":  ["D1", "D9"],
    "bhava_2":  ["D2", "D1"],
    "bhava_3":  ["D3", "D1"],
    "bhava_4":  ["D4", "D1"],
    "bhava_5":  ["D7", "D5", "D1"],
    "bhava_6":  ["D6", "D1"],
    "bhava_7":  ["D9", "D7"],
    "bhava_8":  ["D8", "D1"],
    "bhava_9":  ["D9", "D1"],
    "bhava_10": ["D10", "D1"],
    "bhava_11": ["D11", "D1"],
    "bhava_12": ["D12", "D1"],
}


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _context_section(bundle: ChartBundle, features: dict) -> str:
    """Brief native context — lagna, Moon sign, Sun sign only."""
    d1 = bundle.d1
    lagna_info = features.get("lagna", {})
    planets = features.get("planets", {})
    moon = planets.get("Moon", {})
    sun  = planets.get("Sun", {})
    lines = [
        f"Lagna (Ascendant): {lagna_info.get('rasi', '?')}  "
        f"lord={lagna_info.get('lord','?')} in H{lagna_info.get('lord_house','?')}  "
        f"longitude={d1.ascendant_longitude:.4f}",
        f"Moon: {moon.get('rasi','?')} H{moon.get('house','?')}  "
        f"nakshatra={moon.get('nakshatra','?')}",
        f"Sun:  {sun.get('rasi','?')} H{sun.get('house','?')}",
    ]
    return "\n".join(lines)


def _findings_section(features: dict, scope: str) -> str:
    """Pre-computed planet and house summary — engine output only."""
    lines: list[str] = []

    planets = features.get("planets", {})
    if planets:
        lines.append("Planets (engine-computed):")
        for name in sorted(planets.keys()):
            p = planets[name]
            retro = " (R)" if p.get("is_retrograde") else ""
            flags = "".join([
                " EXALTED"           if p.get("is_exalted") else "",
                " DEBILITATED"       if p.get("is_debilitated") else "",
                " OWN-SIGN"          if p.get("is_own_sign") else "",
                " VARGOTTAMA"        if p.get("is_vargottama") else "",
                " COMBUST"           if p.get("is_combust") and not p.get("combust_exempt") else "",
                " COMBUST(exempt)"   if p.get("is_combust") and p.get("combust_exempt") else "",
                " YOGAKARAKA"        if p.get("is_yogakaraka") else "",
                " MARAKA"            if p.get("is_maraka") else "",
            ])
            sandhi = ""
            if p.get("is_gandanta"):
                sandhi = f" [GANDANTA-{p.get('gandanta_side','')}]"
            elif p.get("is_sandhi"):
                sandhi = f" [{p.get('sandhi_label','Sandhi')}]"
            elif p.get("is_bhava_madhya"):
                sandhi = " [BhavaMadhya]"
            nak_qual = ""
            if p.get("nakshatra_gana") or p.get("nakshatra_nature"):
                nak_qual = (
                    f"  gana={p.get('nakshatra_gana','')} nadi={p.get('nakshatra_nadi','')}"
                    f" nature={p.get('nakshatra_nature','')}"
                )
            lines.append(
                f"  {name}: {p.get('rasi','?')} H{p.get('house','?')}"
                f"{retro}{flags}{sandhi}  nak={p.get('nakshatra','?')} P{p.get('pada','?')}"
                f"{nak_qual}"
                f"  role={p.get('functional_role','?')}  strength={p.get('total_strength','?')}"
            )

    houses = features.get("houses", {})
    if houses:
        lines.append("Houses (engine-computed):")
        for h in range(1, 13):
            hd = houses.get(h, {})
            occ = ",".join(hd.get("occupants", [])) or "empty"
            asp = ",".join(hd.get("aspects_received_from", [])) or "none"
            karaka_cond = hd.get("karaka_conditions", [])
            kara_str = ""
            if karaka_cond:
                kara_str = "  karakas=" + "; ".join(
                    f"{k['karaka']} H{k['house']} {k.get('dignity') or 'neutral'}"
                    + (" DUSTHANA" if k.get("in_dusthana") else "")
                    for k in karaka_cond
                )
            lines.append(
                f"  H{h}: lord={hd.get('lord','?')} in H{hd.get('lord_house','?')}"
                f" {hd.get('lord_rasi','?')}  dignity={hd.get('lord_dignity','?')}"
                f"  occ=[{occ}]  asp=[{asp}]{kara_str}"
            )

    drishti = features.get("drishti", {})
    matrix = drishti.get("matrix", [])
    if matrix:
        # For bhava scopes focus drishti on that bhava + its trines/oppositions
        if scope.startswith("bhava_"):
            try:
                bnum = int(scope.split("_")[1])
                opposite = ((bnum - 1 + 6) % 12) + 1
                trine1   = ((bnum - 1 + 4) % 12) + 1
                trine2   = ((bnum - 1 + 8) % 12) + 1
                key_houses = [bnum, opposite, trine1, trine2]
            except ValueError:
                key_houses = [1, 7, 10]
        else:
            key_houses = {
                "personality":   [1, 5, 9],
                "career":        [10, 6, 2],
                "relationships": [7, 5, 11],
                "health":        [1, 6, 8],
            }.get(scope, [1, 7, 10])
        lines.append(f"Drishti on {scope}-relevant houses:")
        for row in matrix:
            if row["house"] in key_houses:
                lines.append(
                    f"  H{row['house']} ({row['rasi']}): "
                    f"graha_asp={row.get('graha_drishti',[])} "
                    f"rashi_asp={row.get('rashi_drishti',[])} "
                    f"double={row.get('double_aspect',[])} "
                    f"strength={row.get('graha_strength','?')}"
                )

    yogas = features.get("yogas", {})
    if yogas:
        lines.append("Yogas (engine-detected):")
        lines.append(f"  Gajakesari={yogas.get('gajakesari',False)}"
                     f"  Kemadruma={yogas.get('kemadruma',False)}")
        for y in yogas.get("raja_yogas", []):
            lines.append(f"  Raja yoga: {y.get('trikona_lord')}+{y.get('kendra_lord')} ({y.get('association')})")
        for y in yogas.get("dhana_yogas", []):
            lines.append(f"  Dhana yoga: {y.get('wealth_lord')}+{y.get('prosperity_lord')} ({y.get('association')})")
        for y in yogas.get("pancha_mahapurusha", []):
            lines.append(f"  Pancha Mahapurusha: {y.get('name')} ({y.get('graha')} in H{y.get('house')})")
        for y in yogas.get("neechabhanga", []):
            lines.append(f"  Neechabhanga: {y.get('graha')} cancelled by {y.get('cancellation_by')}")
        for y in yogas.get("viparita_raja_yogas", []):
            lines.append(f"  Viparita Raja: {y.get('lord')} owns H{y.get('owns_house')} placed H{y.get('placed_in_house')}")
        for y in yogas.get("kartari_yogas", []):
            lines.append(f"  {y.get('name')}: {y.get('detail','')}")
        for y in yogas.get("lunar_yogas", []):
            lines.append(f"  {y.get('name')}: {y.get('detail','')}")
        for y in yogas.get("solar_yogas", []):
            lines.append(f"  {y.get('name')}: {y.get('detail','')}")
        for y in yogas.get("conjunction_yogas", []):
            lines.append(f"  {y.get('name')}: {y.get('detail','')}")
        for y in yogas.get("wealth_yogas", []):
            lines.append(f"  {y.get('name')}: {y.get('detail','')}")
        for y in yogas.get("special_yogas", []):
            lines.append(f"  {y.get('name')}: {y.get('detail','')}")
        for y in yogas.get("nabhasa_yogas", []):
            lines.append(f"  {y.get('name')}: {y.get('detail','')}")

    # Gandanta summary (if any planet in Gandanta)
    gandanta = features.get("gandanta", {})
    if gandanta.get("gandanta_planets"):
        lines.append(f"Gandanta (karmic stress — water/fire junction):")
        for d in gandanta.get("details", []):
            lines.append(f"  {d.get('graha')} in {d.get('rasi')} H{d.get('house')} [{d.get('gandanta_side')}]")

    return "\n".join(lines) if lines else "(no engine findings available)"


def _functional_nature_section(features: dict) -> str:
    fn = features.get("functional_nature", {})
    if not fn:
        return "(not available)"

    lines: list[str] = []
    lagna = fn.get("lagna_rasi", "?")
    yks   = fn.get("yogakarakas", [])
    mks   = fn.get("maraka_lords", [])
    lines.append(f"Lagna: {lagna}")
    lines.append(f"Yogakarakas: {', '.join(yks) if yks else 'none'}")
    lines.append(f"Maraka lords: {', '.join(mks) if mks else 'none'}")

    _ROLE_ORDER = ["yogakaraka", "benefic", "neutral", "malefic"]
    by_role: dict[str, list[str]] = {}
    for name, info in fn.get("planets", {}).items():
        role = info.get("role", "neutral")
        houses = info.get("houses_owned", [])
        tag = f"{name}(H{'|H'.join(str(h) for h in houses)})"
        by_role.setdefault(role, []).append(tag)
    for role in _ROLE_ORDER:
        grps = by_role.get(role, [])
        if grps:
            lines.append(f"  {role.upper()}: {', '.join(grps)}")
    return "\n".join(lines)


def _dasha_strength_section(features: dict) -> str:
    ds = features.get("dasha_strength", {})
    if not ds:
        return "(not available)"

    lines: list[str] = []
    for key in ("mahadasha", "antardasha"):
        rec = ds.get(key)
        if not rec:
            continue
        label = "Mahadasha" if key == "mahadasha" else "Antardasha"
        lord  = rec.get("lord", "?")
        lines.append(f"{label} Lord: {lord}  ({rec.get('start','?')} → {rec.get('end','?')})")
        lines.append(f"  Houses owned: H{', H'.join(str(h) for h in rec.get('houses_owned', []))}")
        lines.append(f"  Placement: H{rec.get('placement_house','?')}")
        lines.append(f"  Sign strength: {rec.get('sign_strength','?')}")
        asp = rec.get("aspects_received", []) or []
        lines.append(f"  Aspects from: {', '.join(asp) or 'none'}")
        conj = rec.get("conjunctions", []) or []
        lines.append(f"  Conjunctions: {', '.join(conj) or 'none'}")
        lines.append(f"  Vargottama: {rec.get('is_vargottama', False)}  Retrograde: {rec.get('is_retrograde', False)}")
        lines.append(f"  Role: {rec.get('functional_role','?')}  Score: {rec.get('assessment_score','?')}")
        for note in rec.get("notes", []):
            lines.append(f"  → {note}")

    # Pratyantara (level-3) period if active
    pratya = ds.get("pratyantara")
    if pratya:
        lines.append(
            f"Pratyantara (PD) Lord: {pratya.get('graha','?')}  "
            f"({pratya.get('start','?')} → {pratya.get('end','?')})"
        )

    return "\n".join(lines) if lines else "(no active dasha)"


def _varga_section(features: dict, scope: str) -> str:
    varga_analysis = features.get("varga_analysis", {})
    if not varga_analysis:
        return "(not available)"

    priority = _SCOPE_VARGAS.get(scope, ["D9", "D10"])
    lines: list[str] = []

    for div in priority:
        v = varga_analysis.get(div)
        if not v:
            continue
        stats   = v.get("dignity_stats", {})
        yogas   = v.get("yogas", [])
        karakas = v.get("karaka_analysis", [])
        lines.append(
            f"{div} {v.get('name','')} [{v.get('domain','')}]:"
            f" Lagna={v.get('lagna','?')} lord={v.get('lagna_lord','?')}"
            f" H{v.get('lagna_lord_house','?')} ({v.get('lagna_lord_dignity','?')})"
            f"  score={stats.get('strength_score','?')}"
            f"  exalted={stats.get('exalted',0)} debilitated={stats.get('debilitated',0)}"
        )
        if karakas:
            ktext = "; ".join(
                f"{k['graha']} {k['rasi']} H{k['house']} {k.get('dignity','?')}"
                for k in karakas
            )
            lines.append(f"  Karakas: {ktext}")
        if yogas:
            ytext = "; ".join(_fmt_yoga(y) for y in yogas[:4])
            lines.append(f"  Yogas: {ytext}")
        planets = v.get("planets", [])
        notable = [
            f"{p['graha']} H{p['house']} {p.get('dignity','')}"
            for p in planets
            if p.get("is_strong") or p.get("is_debilitated") or p["house"] in (1, 10)
        ]
        if notable:
            lines.append(f"  Notable: {'; '.join(notable[:6])}")

    other = sorted(set(varga_analysis.keys()) - set(priority))
    if other:
        brief = []
        for div in other[:8]:
            v = varga_analysis[div]
            s = v.get("dignity_stats", {}).get("strength_score", 0)
            brief.append(f"{div}({v.get('name',div)[:4]}) score={s}")
        lines.append("Other vargas: " + "  ".join(brief))

    return "\n".join(lines) if lines else "(no varga data)"


def _fmt_yoga(y: dict) -> str:
    t = y.get("type", "")
    if t == "lagna_lord_kendra":           return f"LL kendra H{y.get('house')}"
    if t == "lagna_lord_trikona":          return f"LL trikona H{y.get('house')}"
    if t == "lagna_lord_strong":           return f"LL {y.get('dignity')}"
    if t == "lagna_lord_dusthana":         return f"LL dusthana H{y.get('house')}"
    if t == "sign_exchange":               return f"{y.get('graha_a')}↔{y.get('graha_b')}"
    if t == "d9_7th_lord_strong":          return f"D9 7L {y.get('dignity')}"
    if t == "d10_career_planet_prominent": return f"D10 {y.get('graha')} H{y.get('house')}"
    return t.replace("_", " ")[:30]


def _dasha_section(features: dict, bundle: ChartBundle) -> str:
    if not bundle.dashas:
        return "(not available)"

    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date()

    lines = [f"Vimshottari Dashas (reference date: {today.isoformat()}):"]
    shown = 0
    current_maha = None
    for d in bundle.dashas:
        start = d.start_date
        end   = d.end_date
        is_current = start <= today <= end
        marker = " ← CURRENT" if is_current else ""
        graha_name = d.graha.value if hasattr(d.graha, 'value') else str(d.graha)
        lines.append(f"  {graha_name} Maha: {start} → {end}{marker}")
        if is_current:
            current_maha = d
        shown += 1
        if shown >= 5:
            break

    if current_maha and getattr(current_maha, 'sub_periods', None):
        maha_name = current_maha.graha.value if hasattr(current_maha.graha, 'value') else str(current_maha.graha)
        for sub in current_maha.sub_periods[:5]:
            is_active = sub.start_date <= today <= sub.end_date
            marker = " ← ACTIVE" if is_active else ""
            sub_name = sub.graha.value if hasattr(sub.graha, 'value') else str(sub.graha)
            lines.append(f"    {maha_name}/{sub_name}: {sub.start_date} → {sub.end_date}{marker}")

    return "\n".join(lines)


def _gochara_section(gochara: dict) -> str:
    """Format pre-computed Gochara engine output as a structured context block.

    The LLM must treat all values here as authoritative and must not recalculate
    any transit position or suggest additional remedies.
    """
    lines = [
        f"Transit date: {gochara.get('transit_datetime', '?')}",
        f"Natal Moon sign: {gochara.get('natal_moon_sign', '?')}  "
        f"(H{gochara.get('natal_moon_house','?')})",
        f"Active dasha: {gochara.get('current_mahadasha','?')} Maha / "
        f"{gochara.get('current_antardasha','?')} Antar  "
        f"(ends {gochara.get('mahadasha_end','?')})",
        f"Overall transit tone: {gochara.get('overall_tone','?')}  "
        f"[fav={gochara.get('favorable_count',0)}  "
        f"unfav={gochara.get('unfavorable_count',0)}  "
        f"mixed={gochara.get('mixed_count',0)}]",
    ]

    sadhe = gochara.get("sadhe_sati", {})
    if sadhe.get("active"):
        lines.append(
            f"Sadhe Sati/Ashtama: ACTIVE — phase={sadhe.get('phase','?')}  "
            f"Saturn H{sadhe.get('saturn_house_from_moon','?')} from Moon  "
            f"({sadhe.get('description','')})"
        )

    alerts = gochara.get("special_alerts", [])
    if alerts:
        lines.append("Special alerts (engine-flagged):")
        for a in alerts:
            lines.append(f"  [{a.get('severity','?').upper()}] {a.get('name','?')}: {a.get('description','')}")

    results = gochara.get("planet_results", [])
    if results:
        lines.append("Planet-by-planet Gochara (engine output):")
        for r in results:
            vedha = f"  VEDHA by {r.get('vedha_planet','?')}" if r.get("vedha_active") else ""
            dasha = ""
            if r.get("is_dasha_lord"):     dasha = " [MAHADASHA LORD]"
            elif r.get("is_antardasha_lord"): dasha = " [ANTARDASHA LORD]"
            retro = " (R)" if r.get("is_retrograde") else ""
            lines.append(
                f"  {r.get('graha','?')}{retro}: H{r.get('transit_house_from_moon','?')} from Moon"
                f" ({r.get('transit_sign','?')}) → {r.get('result_key','?').upper()}"
                f" — {r.get('short_effect','')}{vedha}{dasha}"
            )

    obs = gochara.get("observations", [])
    if obs:
        lines.append("Engine observations:")
        for o in obs:
            lines.append(f"  • {o}")

    return "\n".join(lines)


def _shadbala_section(features: dict) -> str:
    """Shadbala six-fold strength summary for the LLM."""
    sb = features.get("shadbala", {})
    if not sb:
        return "(not available)"

    lines: list[str] = [
        f"Strongest planet (Shadbala): {sb.get('strongest','?')}",
        f"Weakest planet  (Shadbala): {sb.get('weakest','?')}",
    ]
    strong, weak = [], []
    for row in sb.get("summary", []):
        g = row.get("graha","?")
        v = row.get("total_virupas", 0)
        r = row.get("strength_ratio")
        r_str = f"{r:.2f}" if r is not None else "?"
        if row.get("is_strong"):
            strong.append(f"{g}({v:.0f}V ratio={r_str})")
        elif r is not None and r < 0.6:
            weak.append(f"{g}({v:.0f}V ratio={r_str})")
    if strong:
        lines.append(f"Above minimum threshold: {', '.join(strong)}")
    if weak:
        lines.append(f"Significantly weak (<60% of minimum): {', '.join(weak)}")
    lines.append(sb.get("note", ""))
    return "\n".join(lines)


def _ashtakavarga_section(features: dict) -> str:
    """Ashtakavarga SAV + transit quality summary for the LLM."""
    av = features.get("ashtakavarga", {})
    if not av:
        return "(not available)"

    lines: list[str] = []
    strong = av.get("strong_signs", [])
    weak   = av.get("weak_signs", [])
    if strong:
        lines.append(f"SAV strong signs (≥30 bindus — favourable transits): {', '.join(strong)}")
    if weak:
        lines.append(f"SAV weak signs (≤25 bindus — challenging transits): {', '.join(weak)}")

    tg = av.get("transit_guide", [])
    if tg:
        lines.append("Current transit bindu quality (BAV):")
        for t in tg:
            lines.append(
                f"  {t.get('planet','?')} in {t.get('transit_sign','?')}: "
                f"{t.get('bindus','?')}/8 → {t.get('quality','?')} — {t.get('interpretation','')}"
            )
    return "\n".join(lines) if lines else "(no Ashtakavarga data)"


def _bhava_context_section(features: dict, scope: str, gochara_context: dict | None) -> str:
    """Build bhava activation + transit pressure block for a single bhava scope."""
    try:
        bhava_num = int(scope.split("_")[1])
    except (IndexError, ValueError):
        return "(bhava context unavailable)"
    return build_bhava_context_block(features, bhava_num, gochara_context)


def _flowchart_section(features: dict, scope: str) -> str:
    """Render the HTJH flowchart excerpt relevant to `scope`, in the book's
    module priority order (M1 Foundation -> M4 House -> M5 Dasha ->
    M6 Yogas -> M8 Synthesis). Every line here is a pre-computed, book-derived
    finding — not LLM output — and is the primary evidence for raman_method.
    """
    ex = scope_flowchart_excerpt(features, scope)
    lines = [
        f"[M1] Lagna: {ex['lagna'] or '?'}  lord={ex['lagna_lord'] or '?'}",
        f"[M1] Moon: {ex['moon'] or '?'}",
    ]
    step = ex["house_step"]
    if step:
        lines.append(f"[M4] House {ex['house']} ({ex['area']}) — status={step['status']}:")
        lines.extend(f"  {x}" for x in step["findings"])
    else:
        lines.append(f"[M4] House {ex['house']} ({ex['area']}): (not available)")
    if ex["timing_outlook"]:
        lines.append(f"[M5] Dasha timing: {ex['timing_outlook']}")
    if ex["yogas_positive"]:
        lines.append(f"[M6] Positive yogas: {', '.join(ex['yogas_positive'])}")
    if ex["yogas_negative"]:
        lines.append(f"[M6] Negative yogas: {', '.join(ex['yogas_negative'])}")
    if ex["verdict"]:
        lines.append(f"[M8] Synthesis verdict: {ex['verdict']}")
    if ex["life_area_finding"]:
        lines.append(f"[M8] House {ex['house']} key finding: {ex['life_area_finding']}")
    return "\n".join(lines)


def _rules_section(triggers: list[RuleTrigger]) -> str:
    lines = []
    for t in sorted(triggers, key=lambda x: x.rule_id):
        lines.append(
            f"[{t.rule_id}] {t.rule_name} (scope={t.scope}, weight={t.weight:.2f}): "
            f"{t.explanation}"
        )
    return "\n".join(lines) if lines else "(none triggered)"


def _passages_section(passages: list[RetrievedPassage]) -> str:
    lines = []
    for p in sorted(passages, key=lambda x: x.chunk_id):
        lines.append(
            f"[{p.chunk_id}] (source={p.source}, relevance={p.score:.3f})\n{p.text}"
        )
    return "\n\n".join(lines) if lines else "(none)"


def _task_section(scope: str, raman_method: bool, has_gochara: bool) -> str:
    is_bhava = scope.startswith("bhava_")
    if is_bhava:
        try:
            bhava_num = int(scope.split("_")[1])
        except (IndexError, ValueError):
            bhava_num = 0
        bhava_focus = (
            f"Focus on Bhava {bhava_num} (its lord, occupants, aspects received, dasha activation, "
            f"and current transits through it). "
            f"Check interdependencies: planets aspecting this bhava, the lord's placement and dignity, "
            f"and how the active dasha lord relates to this house."
        )
        scope_label = f"Bhava {bhava_num}"
    else:
        bhava_focus = ""
        scope_label = scope

    method_note = (
        "Follow the RAMAN HTJH FLOWCHART section above in its module priority order "
        "(M1 foundation -> M4 house analysis -> M5 dasha timing -> M6 yogas -> M8 synthesis). "
        "That section is the primary evidence — use ENGINE FINDINGS only to fill in specific "
        "planetary details it already implies. Do not introduce a conclusion the flowchart "
        "findings or M8 synthesis verdict do not support."
        if raman_method else
        "Cite specific planets, house numbers, yogas, and dasha periods from the ENGINE FINDINGS above."
    )
    gochara_note = (
        "\nWhere a TRANSIT / GOCHARA CONTEXT section is present, integrate the "
        "transit tone into the narrative — note which natal significators are under "
        "transit stress or support, and how this intersects with the active dasha. "
        "Do NOT suggest remedies; those are in the engine output."
        if has_gochara else ""
    )
    bhava_note = f"\n{bhava_focus}" if bhava_focus else ""
    return (
        f"Synthesize a {scope_label} interpretation from the ENGINE FINDINGS, "
        f"BHAVA ACTIVATION, and TRIGGERED RULES above.\n"
        f"{method_note}{gochara_note}{bhava_note}\n\n"
        f"Respond with ONLY this JSON object — no markdown fences, no explanation, no extra keys:\n"
        f'{{\n'
        f'  "summary": "2-3 sentence overall {scope_label} synthesis grounded in engine findings",\n'
        f'  "details": [\n'
        f'    "Sentence citing a specific engine finding (planet / house / yoga / dasha).",\n'
        f'    "Another sentence. Up to 5 items. Each item must be a STRING, not an object."\n'
        f'  ],\n'
        f'  "rule_refs": ["rule_id_1"],\n'
        f'  "passage_refs": ["chunk_id_1"]\n'
        f'}}'
    )


# ---------------------------------------------------------------------------
# Chat instruction
# ---------------------------------------------------------------------------
_INSTRUCTION_CHAT = """\
You are a Vedic astrology expert assistant helping someone understand their birth chart.

ROLE: Answer the user's question using ONLY the pre-computed chart data in the sections below.
All planetary positions, house lords, yoga combinations, dasha periods, strength scores,
and transit results are pre-computed by a deterministic engine and are authoritative.

STRICT PROHIBITIONS:
  • Do NOT re-derive or recalculate any positions, longitudes, or house numbers.
  • Do NOT re-derive dasha periods, their lords, or their dates.
  • Do NOT suggest remedies, mantras, or gemstones unless they appear in the engine data.
  • Do NOT introduce any planetary placement or yoga not listed in the ENGINE FINDINGS.
  • Do NOT contradict the engine-computed dignity or tone for any planet.

HOW TO ANSWER:
  • Be specific — cite planets, house numbers, yogas, dasha lords, and strength scores.
  • If a TRANSIT / GOCHARA CONTEXT section is present, treat all values there as authoritative.
    Sadhe Sati, Ashtama Shani, and planet-by-planet gochara results from that section
    OVERRIDE any general inference about current planetary effects.
  • Draw only from the sections below; do not add external knowledge that contradicts the data.
  • Write in clear, flowing prose — no bullet lists unless the question calls for comparison.
  • If the question cannot be answered from the available data, say so briefly and explain why.

Do NOT return JSON. Answer in plain prose."""


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def build_chat_prompt(
    bundle: ChartBundle,
    features: dict,
    question: str,
    *,
    gochara_context: dict | None = None,
) -> str:
    """Build a free-form Q&A prompt for 'Chat with Chart'.

    Includes the full chart context but asks the LLM to answer a specific
    user question in plain prose (no JSON output).
    """
    has_gochara = gochara_context is not None

    parts = [
        _INSTRUCTION_CHAT,
        "",
        _SECTION_CONTEXT,
        _context_section(bundle, features),
        "",
        _SECTION_FINDINGS,
        _findings_section(features, "all"),
        "",
        _SECTION_FUNCTIONAL,
        _functional_nature_section(features),
        "",
        _SECTION_DASHA_STR,
        _dasha_strength_section(features),
        "",
        _SECTION_SHADBALA,
        _shadbala_section(features),
        "",
        _SECTION_ASHTAKA,
        _ashtakavarga_section(features),
        "",
        _SECTION_DASHA,
        _dasha_section(features, bundle),
        "",
    ]

    if has_gochara:
        parts += [
            _SECTION_GOCHARA,
            _gochara_section(gochara_context),
            "",
        ]

    parts += [
        "### USER QUESTION",
        question.strip(),
        "",
        "### YOUR ANSWER",
        "Answer in plain prose, grounding every claim in the engine data above.",
    ]
    return "\n".join(parts)


def build_interpretation_prompt(
    bundle: ChartBundle,
    features: dict,
    triggers: list[RuleTrigger],
    passages: list[RetrievedPassage],
    scope: str,
    output_schema: dict,
    *,
    raman_method: bool = False,
    gochara_context: dict | None = None,
) -> str:
    """Construct the synthesis-only prompt sent to the local LLM.

    Section order:
      NATIVE CONTEXT → [RAMAN HTJH FLOWCHART, if raman_method] → ENGINE FINDINGS →
      FUNCTIONAL NATURE → DASHA STRENGTH → VARGA ANALYSIS → DASHA TIMING →
      [GOCHARA CONTEXT] → TRIGGERED RULE FINDINGS → CLASSICAL PASSAGES → TASK
    """
    instruction = _INSTRUCTION_RAMAN if raman_method else _INSTRUCTION
    has_gochara = gochara_context is not None

    parts = [
        instruction,
        "",
        _SECTION_CONTEXT,
        _context_section(bundle, features),
        "",
    ]

    if raman_method:
        parts += [
            _SECTION_FLOWCHART,
            _flowchart_section(features, scope),
            "",
        ]

    parts += [
        _SECTION_FINDINGS,
        _findings_section(features, scope),
        "",
        _SECTION_FUNCTIONAL,
        _functional_nature_section(features),
        "",
        _SECTION_DASHA_STR,
        _dasha_strength_section(features),
        "",
        _SECTION_SHADBALA,
        _shadbala_section(features),
        "",
        _SECTION_ASHTAKA,
        _ashtakavarga_section(features),
        "",
        _SECTION_VARGA,
        _varga_section(features, scope),
        "",
        _SECTION_DASHA,
        _dasha_section(features, bundle),
        "",
    ]

    if has_gochara:
        parts += [
            _SECTION_GOCHARA,
            _gochara_section(gochara_context),
            "",
        ]

    if scope.startswith("bhava_"):
        parts += [
            _SECTION_BHAVA,
            _bhava_context_section(features, scope, gochara_context),
            "",
        ]

    parts += [
        _SECTION_RULES,
        _rules_section(triggers),
        "",
        _SECTION_PASSAGES,
        _passages_section(passages),
        "",
        _SECTION_TASK,
        _task_section(scope, raman_method, has_gochara),
    ]
    return "\n".join(parts)
