"""Build deterministic prompts for the local LLM interpretation call."""

from __future__ import annotations

import json

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.corpus import RetrievedPassage
from vedic_ai.domain.prediction import RuleTrigger

# Section header tokens — fixed order for snapshot stability
_SECTION_CHART_FACTS = "### CHART FACTS"
_SECTION_DERIVED     = "### DERIVED FEATURES"
_SECTION_FUNCTIONAL  = "### FUNCTIONAL PLANETARY NATURE (RAMAN)"
_SECTION_DASHA_STR   = "### DASHA LORD STRENGTH"
_SECTION_VARGA       = "### VARGA (DIVISIONAL) ANALYSIS"
_SECTION_DASHA       = "### DASHA TIMING"
_SECTION_RULES       = "### TRIGGERED RULES"
_SECTION_PASSAGES    = "### SUPPORTING PASSAGES"
_SECTION_TASK        = "### TASK"

_INSTRUCTION = (
    "You are a Vedic astrology analyst. "
    "Respond ONLY with a valid JSON object matching the output schema. "
    "Do not include unsupported claims. "
    "Every statement must be grounded in the chart facts, triggered rules, "
    "or supporting passages provided. "
    "Be specific: name the planets, houses, signs, and divisional chart positions "
    "that support each point. Reference dasha periods when relevant."
)

_INSTRUCTION_RAMAN = (
    "You are a Vedic astrology analyst trained in the B.V. Raman school. "
    "Respond ONLY with a valid JSON object matching the output schema. "
    "Use B.V. Raman's house-by-house analytical method: examine the house lord's "
    "placement, the occupants of the house, and aspects received. "
    "Reference divisional charts (Navamsa for relationships, Dasamsa for career, "
    "Shashthamsha for health) to confirm natal indications. "
    "Every statement must be grounded in the provided chart data, rules, and passages."
)

# Scope → primary divisional charts to emphasise
_SCOPE_VARGAS: dict[str, list[str]] = {
    "personality":   ["D9", "D1"],
    "career":        ["D10", "D9"],
    "relationships": ["D9", "D7"],
    "health":        ["D6", "D8", "D30"],
}


def _chart_facts_section(bundle: ChartBundle) -> str:
    d1 = bundle.d1
    lines = [f"Ascendant longitude: {d1.ascendant_longitude:.4f}"]
    for name in sorted(d1.planets.keys()):
        p = d1.planets[name]
        lines.append(f"{name}: sign={p.rasi.rasi.value}, house={p.house}, lon={p.longitude:.4f}")
    for num in sorted(d1.houses.keys()):
        h = d1.houses[num]
        lines.append(f"House {num}: sign={h.rasi.value}, lon={h.cusp_longitude:.4f}")
    return "\n".join(lines)


def _derived_features_section(features: dict, scope: str) -> str:
    lines: list[str] = []

    planets = features.get("planets", {})
    if planets:
        lines.append("Planets (sign, house, dignity, sandhi):")
        for name in sorted(planets.keys()):
            p = planets[name]
            retro = " (R)" if p.get("is_retrograde") else ""
            flags = "".join([
                " EXALTED"     if p.get("is_exalted") else "",
                " DEBILITATED" if p.get("is_debilitated") else "",
                " OWN-SIGN"    if p.get("is_own_sign") else "",
                " VARGOTTAMA"  if p.get("is_vargottama") else "",
                " COMBUST"     if p.get("is_combust") and not p.get("combust_exempt") else "",
                " COMBUST(exempt)" if p.get("is_combust") and p.get("combust_exempt") else "",
                " YOGAKARAKA"  if p.get("is_yogakaraka") else "",
                " MARAKA"      if p.get("is_maraka") else "",
            ])
            sandhi = ""
            if p.get("is_sandhi"):
                sandhi = f" [{p.get('sandhi_label','Sandhi')}]"
            elif p.get("is_bhava_madhya"):
                sandhi = " [BhavaMadhya]"
            lines.append(
                f"  {name}: {p.get('rasi','?')} H{p.get('house','?')}"
                f"{retro}{flags}{sandhi}  nak={p.get('nakshatra','?')}"
                f"  fn={p.get('functional_role','?')}  strength={p.get('total_strength','?')}"
            )

    houses = features.get("houses", {})
    if houses:
        lines.append("Houses (lord, occupants, aspects, karakas):")
        for h in range(1, 13):
            hd = houses.get(h, {})
            occ = ",".join(hd.get("occupants", [])) or "empty"
            asp = ",".join(hd.get("aspects_received_from", [])) or "none"
            karakas = hd.get("karakas", [])
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

    # Drishti matrix for key houses by scope
    drishti = features.get("drishti", {})
    matrix = drishti.get("matrix", [])
    if matrix:
        key_houses = {
            "personality":   [1, 5, 9],
            "career":        [10, 6, 2],
            "relationships": [7, 5, 11],
            "health":        [1, 6, 8],
        }.get(scope, [1, 7, 10])
        lines.append(f"Drishti on key houses ({scope}):")
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
        lines.append("Yogas:")
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

    lagna = features.get("lagna", {})
    if lagna:
        lines.append(
            f"Lagna: {lagna.get('rasi','?')}  lord={lagna.get('lord','?')}"
            f" in H{lagna.get('lord_house','?')}  dignity={lagna.get('lord_dignity','?')}"
            f"  nak={lagna.get('nakshatra','?')}"
        )

    return "\n".join(lines) if lines else json.dumps(features, sort_keys=True, ensure_ascii=False)


def _functional_nature_section(features: dict) -> str:
    """Summarise functional planetary nature and yogakarakas for this lagna."""
    fn = features.get("functional_nature", {})
    if not fn:
        return "(functional nature not available)"

    lines: list[str] = []
    lagna = fn.get("lagna_rasi", "?")
    yks   = fn.get("yogakarakas", [])
    mks   = fn.get("maraka_lords", [])
    lines.append(f"Lagna: {lagna}")
    lines.append(f"Yogakarakas (owns kendra+trikona): {', '.join(yks) if yks else 'none'}")
    lines.append(f"Maraka lords (H2/H7 lords): {', '.join(mks) if mks else 'none'}")

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
    """7-point Raman dasha lord strength assessment."""
    ds = features.get("dasha_strength", {})
    if not ds:
        return "(dasha strength not available)"

    lines: list[str] = []
    for key in ("mahadasha", "antardasha"):
        rec = ds.get(key)
        if not rec:
            continue
        label = "Mahadasha" if key == "mahadasha" else "Antardasha"
        lord  = rec.get("lord", "?")
        lines.append(f"{label} Lord: {lord}")
        lines.append(f"  1. Houses owned: H{', H'.join(str(h) for h in rec.get('houses_owned', []))}")
        lines.append(f"  2. Placement: H{rec.get('placement_house','?')}")
        lines.append(f"  3. Sign strength: {rec.get('sign_strength','?')}")
        asp = rec.get("aspects_received", []) or []
        lines.append(f"  4. Aspects received from: {', '.join(asp) or 'none'}")
        conj = rec.get("conjunctions", []) or []
        lines.append(f"  5. Conjunctions: {', '.join(conj) or 'none'}")
        lines.append(f"  6. Vargottama: {rec.get('is_vargottama', False)}")
        lines.append(f"  7. Retrograde: {rec.get('is_retrograde', False)}")
        lines.append(f"  Role: {rec.get('functional_role','?')}  Score: {rec.get('assessment_score','?')}")
        for note in rec.get("notes", []):
            lines.append(f"  → {note}")
    return "\n".join(lines) if lines else "(no active dasha)"


def _varga_section(features: dict, scope: str) -> str:
    """Summarise scope-relevant divisional charts with specific planet positions."""
    varga_analysis = features.get("varga_analysis", {})
    if not varga_analysis:
        return "(varga analysis not available)"

    priority = _SCOPE_VARGAS.get(scope, ["D9", "D10"])
    lines: list[str] = []

    for div in priority:
        v = varga_analysis.get(div)
        if not v:
            continue
        stats = v.get("dignity_stats", {})
        yogas = v.get("yogas", [])
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
            ytext = "; ".join(
                _fmt_yoga(y) for y in yogas[:4]
            )
            lines.append(f"  Yogas: {ytext}")
        # Key planet positions in this varga
        planets = v.get("planets", [])
        notable = [
            f"{p['graha']} H{p['house']} {p.get('dignity','')}"
            for p in planets
            if p.get("is_strong") or p.get("is_debilitated") or p["house"] in (1, 10)
        ]
        if notable:
            lines.append(f"  Notable: {'; '.join(notable[:6])}")

    # Also show all other available vargas briefly
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
    if t == "lagna_lord_kendra":   return f"LL kendra H{y.get('house')}"
    if t == "lagna_lord_trikona":  return f"LL trikona H{y.get('house')}"
    if t == "lagna_lord_strong":   return f"LL {y.get('dignity')}"
    if t == "lagna_lord_dusthana": return f"LL dusthana H{y.get('house')}"
    if t == "sign_exchange":       return f"{y.get('graha_a')}↔{y.get('graha_b')}"
    if t == "d9_7th_lord_strong":  return f"D9 7L {y.get('dignity')}"
    if t == "d10_career_planet_prominent": return f"D10 {y.get('graha')} H{y.get('house')}"
    return t.replace("_", " ")[:30]


def _dasha_section(features: dict, bundle: ChartBundle) -> str:
    """Include current/upcoming dasha periods for timing context."""
    if not bundle.dashas:
        return "(dasha data not available)"

    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date()
    today_str = today.isoformat()

    lines = [f"Vimshottari Dashas (reference date: {today_str}):"]
    # Show Maha dasha sequence (level 1)
    shown = 0
    current_maha = None
    for d in bundle.dashas:
        start = d.start_date if hasattr(d.start_date, 'isoformat') else d.start_date
        end   = d.end_date   if hasattr(d.end_date,   'isoformat') else d.end_date
        is_current = start <= today <= end
        marker = " ← CURRENT" if is_current else ""
        graha_name = d.graha.value if hasattr(d.graha, 'value') else str(d.graha)
        lines.append(f"  {graha_name} Maha: {start} → {end}{marker}")
        if is_current:
            current_maha = d
        shown += 1
        if shown >= 5:
            break

    # Show Antar dasha within current Maha
    if current_maha and getattr(current_maha, 'sub_periods', None):
        maha_name = current_maha.graha.value if hasattr(current_maha.graha, 'value') else str(current_maha.graha)
        for sub in current_maha.sub_periods[:5]:
            start = sub.start_date
            end   = sub.end_date
            is_active = start <= today <= end
            marker = " ← ACTIVE" if is_active else ""
            sub_name = sub.graha.value if hasattr(sub.graha, 'value') else str(sub.graha)
            lines.append(f"    {maha_name}/{sub_name}: {start} → {end}{marker}")

    return "\n".join(lines)


def _rules_section(triggers: list[RuleTrigger]) -> str:
    lines = []
    for t in sorted(triggers, key=lambda x: x.rule_id):
        lines.append(
            f"[{t.rule_id}] {t.rule_name} (scope={t.scope}, weight={t.weight:.2f}): "
            f"{t.explanation}"
        )
    return "\n".join(lines) if lines else "(none)"


def _passages_section(passages: list[RetrievedPassage]) -> str:
    lines = []
    for p in sorted(passages, key=lambda x: x.chunk_id):
        lines.append(
            f"[{p.chunk_id}] (source={p.source}, score={p.score:.4f})\n{p.text}"
        )
    return "\n\n".join(lines) if lines else "(none)"


def _task_section(scope: str, output_schema: dict, raman_method: bool) -> str:
    method_note = (
        " Use B.V. Raman's method: analyse the relevant house, its lord's placement, "
        "occupants, aspects, and confirm via the appropriate divisional chart."
        if raman_method else
        " Be specific: cite planet names, house numbers, sign names, divisional charts "
        "and dasha periods that substantiate each point."
    )
    return (
        f"Generate a {scope} interpretation.{method_note}\n\n"
        f"Respond with ONLY this JSON object — no markdown fences, no explanation, no extra keys:\n"
        f'{{\n'
        f'  "summary": "2-3 sentence overall {scope} reading grounded in the chart",\n'
        f'  "details": [\n'
        f'    "Plain English sentence citing a specific planet, house, sign, or yoga.",\n'
        f'    "Another plain English sentence. Up to 5 items. Each item is a STRING, not an object."\n'
        f'  ],\n'
        f'  "rule_refs": ["rule_id_1", "rule_id_2"],\n'
        f'  "passage_refs": ["chunk_id_1"]\n'
        f'}}'
    )


def build_interpretation_prompt(
    bundle: ChartBundle,
    features: dict,
    triggers: list[RuleTrigger],
    passages: list[RetrievedPassage],
    scope: str,
    output_schema: dict,
    *,
    raman_method: bool = False,
) -> str:
    """Construct the final prompt sent to the local model.

    Section order: CHART FACTS → DERIVED FEATURES → VARGA ANALYSIS →
    DASHA TIMING → TRIGGERED RULES → SUPPORTING PASSAGES → TASK.
    """
    instruction = _INSTRUCTION_RAMAN if raman_method else _INSTRUCTION
    parts = [
        instruction,
        "",
        _SECTION_CHART_FACTS,
        _chart_facts_section(bundle),
        "",
        _SECTION_DERIVED,
        _derived_features_section(features, scope),
        "",
        _SECTION_FUNCTIONAL,
        _functional_nature_section(features),
        "",
        _SECTION_DASHA_STR,
        _dasha_strength_section(features),
        "",
        _SECTION_VARGA,
        _varga_section(features, scope),
        "",
        _SECTION_DASHA,
        _dasha_section(features, bundle),
        "",
        _SECTION_RULES,
        _rules_section(triggers),
        "",
        _SECTION_PASSAGES,
        _passages_section(passages),
        "",
        _SECTION_TASK,
        _task_section(scope, output_schema, raman_method),
    ]
    return "\n".join(parts)
