# Prediction Scope Analysis — What Is Covered & What Is Missing

*Analysed against: rule files, `core_features.py`, `varga_analysis.py`, `prompt_builder.py`*

---

## 1. Personality Scope

### What is analysed

| Layer | Factors currently used |
|---|---|
| **Lagna (H1)** | Planets in H1: Sun, Moon, Jupiter, Saturn, Rahu, Ketu |
| **Lagna lord** | Dignity only — own sign / moolatrikona trigger (P005) |
| **Drishti on H1** | Saturn aspect on Lagna (P011) |
| **Yogas** | Gajakesari (P007), Kemadruma (P006) |
| **Exaltation** | Sun exalted (P008), Moon exalted (P009) |
| **Key drishti houses** | H1, H5, H9 passed to LLM |
| **Divisional charts** | D9 lagna lord strength, D9 dignity stats, D1 notable planets |
| **Dasha context** | Mahadasha/antardasha lord strength sent to LLM |
| **Functional nature** | Yogakarakas, maraka lords, benefic/malefic roles sent to LLM |

### Rules — 11 total

| ID | Trigger | Weight |
|---|---|---|
| P001 | Sun in H1 | 0.70 |
| P002 | Moon in H1 | 0.60 |
| P003 | Jupiter in H1 | 0.65 |
| P004 | Saturn in H1 | 0.55 |
| P005 | Lagna lord in own/moolatrikona | 0.70 |
| P006 | Kemadruma yoga | 0.55 |
| P007 | Gajakesari yoga | 0.75 |
| P008 | Sun exalted | 0.80 |
| P009 | Moon exalted | 0.75 |
| P010 | Rahu in H1 | 0.50 |
| P011 | Saturn aspects H1 | 0.40 |

### What is missing

| Gap | Importance | Notes |
|---|---|---|
| Mars/Venus/Mercury in H1 | HIGH | 3 of 9 planets have no H1 rule; Mars gives courage/aggression, Venus grace/artistic nature, Mercury wit/curiosity |
| Ketu in H1 | HIGH | H009 covers it for health but no personality rule — Ketu in Lagna gives psychic sensitivity, detachment |
| Lagna lord in other houses | HIGH | P005 only covers own sign; lagna lord in H10 (ambition), H8 (mystery), H12 (spiritual/reclusive) shape personality profoundly |
| Moon nakshatra / Janma Nakshatra | HIGH | Fundamental personality indicator in Jyotish; not a single rule uses nakshatra |
| Lagna nakshatra | HIGH | The rising nakshatra's deity, symbol, and pada strongly colour character |
| 5th house analysis | HIGH | Buddhi sthana — intelligence, creativity, past-life merit; H5 is a drishti key house but no rules check it |
| 9th house / Bhagya | MEDIUM | Fortune, dharma, father; is in drishti key houses but no rules trigger on it |
| Pancha Mahapurusha yogas | MEDIUM | Ruchaka/Bhadra/Hamsa/Malavya/Shasha detected in features but no personality rules use them |
| Combustion (planets near Sun) | MEDIUM | Combust Moon → weak mind; combust Mercury → poor reasoning; computed but not used |
| Retrograde planets in H1 | MEDIUM | Retrograde lagna lord or retrograde planet in Lagna has distinct personality implications |
| Sandhi / bhava madhya | LOW | Computed but no rules check whether lagna lord is in sandhi (weakened) or bhava madhya (strong) |
| Functional role rules | LOW | Benefic/malefic/yogakaraka role for each lagna is computed and sent to LLM but no rules enforce it |
| Arudha Lagna | LOW | Jaimini's public image indicator — not computed |
| Atmakaraka | LOW | Highest-degree planet; shows soul's purpose — not computed |
| D1 vargottama planets | LOW | Vargottama computed but no personality rules mention it |

---

## 2. Career Scope

### What is analysed

| Layer | Factors currently used |
|---|---|
| **H10 occupants** | Sun (C001), Saturn (C002), Jupiter (C005), Mars (C006), any planet (C007) |
| **10th lord position** | In kendra (C003), in trikona (C004), exalted (C009), debilitated (C010) |
| **Lagna lord** | Lagna lord in H10 (C008) |
| **Key drishti houses** | H10, H6, H2 passed to LLM |
| **Divisional charts** | D10 planet positions and yogas, D9 confirmatory |
| **Dasha context** | Mahadasha/antardasha lord 7-point strength sent to LLM |
| **Functional nature** | Yogakarakas, maraka lords, benefic/malefic roles |

### Rules — 10 total

| ID | Trigger | Weight |
|---|---|---|
| C001 | Sun in H10 | 0.75 |
| C002 | Saturn in H10 | 0.65 |
| C003 | 10th lord in kendra | 0.60 |
| C004 | 10th lord in trikona | 0.60 |
| C005 | Jupiter in H10 | 0.70 |
| C006 | Mars in H10 | 0.65 |
| C007 | Any planet in H10 | 0.40 |
| C008 | Lagna lord in H10 | 0.65 |
| C009 | 10th lord exalted | 0.85 |
| C010 | 10th lord debilitated | 0.50 |

### What is missing

| Gap | Importance | Notes |
|---|---|---|
| Venus/Mercury/Moon/Rahu/Ketu in H10 | HIGH | 5 planets unrepresented in H10 rules; Venus in H10 → creative/luxury fields; Mercury → communication/trade; Moon → public-facing/hospitality |
| 2nd house lord / H2 conditions | HIGH | Dhana bhava — income, accumulated wealth, speech; key for career output but only appears in drishti key houses |
| 11th house / H11 analysis | HIGH | Labha sthana — gains, fulfillment of ambitions, income from career; completely absent from rules |
| 6th house lord position | HIGH | H6 is the service/employment house; where the 6th lord sits strongly predicts the work environment |
| Dharma-Karmadhipati yoga | HIGH | 9th lord + 10th lord association = highly auspicious career yoga; detected as Raja yoga but not specifically labelled for career |
| D10 lagna lord strength | HIGH | D10 lagna sets the career chart's overall strength; computed but no rule checks it specifically |
| Atmakaraka in D10 | MEDIUM | Where the soul's planet lands in Dasamsa reveals life's professional purpose — not computed |
| Dasha lord in H10 or H10 lord aspects | MEDIUM | Active dasha lord's relationship to the 10th is the primary timing tool; data is sent but no rule fires on it |
| Saturn as natural karaka of profession | MEDIUM | No rule checks Saturn's natal dignity independently of H10; a debilitated Saturn anywhere can affect career |
| 3rd house / effort and skill | MEDIUM | H3 = parakrama, communication skill, technical ability; completely absent |
| Arudha of H10 (Rajya Pada) | LOW | Jaimini's public status indicator — not computed |
| Yogakaraka running dasha | LOW | If the current dasha lord is the yogakaraka for this lagna, career should surge — no rule for it |
| Vargottama Saturn or Sun | LOW | Vargottama status of career significators adds strength — not used in rules |

---

## 3. Relationships Scope

### What is analysed

| Layer | Factors currently used |
|---|---|
| **H7 occupants** | Venus (R001), Jupiter (R002), Saturn (R003), Mars (R006), any planet (R007) |
| **7th lord dignity** | Own/moolatrikona (R004) |
| **Venus exaltation** | Venus exalted globally (R005) |
| **Key drishti houses** | H7, H5, H11 passed to LLM |
| **Divisional charts** | D9 (7th lord, Venus, Jupiter strength), D7 (children/progeny) |
| **Dasha context** | Mahadasha/antardasha strength sent to LLM |

### Rules — 7 total (smallest rule set)

| ID | Trigger | Weight |
|---|---|---|
| R001 | Venus in H7 | 0.75 |
| R002 | Jupiter in H7 | 0.70 |
| R003 | Saturn in H7 | 0.55 |
| R004 | 7th lord in own/moolatrikona | 0.70 |
| R005 | Venus exalted | 0.80 |
| R006 | Mars in H7 | 0.50 |
| R007 | Any planet in H7 | 0.35 |

### What is missing ← **most under-developed scope**

| Gap | Importance | Notes |
|---|---|---|
| Sun/Moon/Mercury/Rahu/Ketu in H7 | HIGH | 5 planets have no H7 rule; Sun in H7 → dominant/egoistic partner; Moon → emotional/caring; Mercury → communicative/young partner; Rahu → foreign/unconventional; Ketu → karmic/past-life connection |
| 7th lord in other houses | HIGH | Where the 7th lord sits beyond its own sign completely determines partner characteristics and relationship timing — not one rule covers this |
| 2nd house analysis | HIGH | Kutumba bhava — family life, spouse's family; H2 lord in H7 or vice versa indicates marriage; absent entirely |
| 4th house / domestic happiness | HIGH | H4 = home, emotional security, mother; 4th lord in 7th or vice versa strongly colours domestic life — absent |
| Upapada Lagna (UL) | HIGH | Jaimini's most precise marriage indicator; the Arudha of H12 = UL; not computed |
| Darakaraka | HIGH | Jaimini — lowest-degree planet = karaka of spouse; not computed |
| Kuja Dosha (Mangal Dosha) | HIGH | Mars in H1/H2/H4/H7/H8/H12 causes Kuja Dosha — one of the most used relationship indicators; only H7 Mars rule exists |
| D9 7th house analysis | MEDIUM | The D9 7th house and its lord are the definitive marriage strength indicator; only aggregated stats passed |
| Venus combust or in enemy sign | MEDIUM | Damaged Venus → relationship difficulties; Venus combustion/dignity rules absent |
| 8th house for marriage longevity | MEDIUM | H8 = longevity of marriage, intimacy, in-laws; H8 lord placement absent from all rules |
| 11th house lord | MEDIUM | H11 = desires, fulfillment, social networks; in drishti key houses but no rules trigger |
| Jupiter aspect on H7 | MEDIUM | Jupiter's 5th/7th/9th aspect on H7 is protective for marriage; only physical placement in H7 covered |
| Venus nakshatra | LOW | Venus's nakshatra shapes romantic nature specifically |
| Moon's role | LOW | Moon is the emotional mind; its dignity critically affects relational happiness — no relationship rule for Moon |
| Timing rules for marriage | LOW | Timing rules T001-T010 exist but are never applied to the relationships scope |

---

## 4. Health Scope

### What is analysed

| Layer | Factors currently used |
|---|---|
| **Lagna lord** | In kendra (H001), in dusthana (H002) |
| **H1 occupants** | Saturn (H003), Ketu (H008) |
| **H6 activity** | Mars in H6 (H004), 6th lord in H1 (H011) |
| **Planet dignities** | Moon in enemy sign (H005), Sun in dusthana (H006), Saturn in dusthana (H009) |
| **H8 lord** | Debilitated (H012) |
| **Protective factors** | Jupiter in kendra (H010), Sun exalted (H013), Moon exalted (H014) |
| **Yoga** | Neechabhanga for any planet (H015) |
| **Specific placements** | Rahu in H6 (H007) |
| **Key drishti houses** | H1, H6, H8 passed to LLM |
| **Divisional charts** | D6 (disease), D8 (longevity), D30 (dangers/karma) |

### Rules — 15 total (most comprehensive)

| ID | Trigger | Weight |
|---|---|---|
| H001 | Lagna lord in kendra | 0.75 |
| H002 | Lagna lord in dusthana | 0.65 |
| H003 | Saturn in H1 | 0.65 |
| H004 | Mars in H6 | 0.60 |
| H005 | Moon in enemy sign | 0.60 |
| H006 | Sun in dusthana | 0.55 |
| H007 | Rahu in H6 | 0.55 |
| H008 | Ketu in H1 | 0.50 |
| H009 | Saturn in dusthana | 0.65 |
| H010 | Jupiter in kendra | 0.70 |
| H011 | 6th lord in H1 | 0.60 |
| H012 | 8th lord debilitated | 0.55 |
| H013 | Sun exalted | 0.70 |
| H014 | Moon exalted | 0.65 |
| H015 | Neechabhanga yoga present | 0.60 |

### What is missing

| Gap | Importance | Notes |
|---|---|---|
| 12th house analysis | HIGH | Vyaya bhava — hospitalisation, long-term illness, moksha, sleep disorders; completely absent |
| Mars in H1 or H8 | HIGH | Mars in H1 → injury risk, surgery, blood disorders; Mars in H8 → accidents, violent events; only Mars in H6 covered |
| 6th house lord in other houses | HIGH | 6th lord in H10 (disease disrupts career), H8 (chronic recurring conditions), H12 (hospitalisation) — only 6th lord in H1 covered |
| 8th lord in other houses | HIGH | 8th lord in H6 (chronic illness), H12 (hospitalisation/surgery) critical; only debilitation dignity covered |
| D27 Saptavimshamsha rules | HIGH | D27 is the primary divisional for physical strength and vitality; computed in full but no rules reference it |
| D6 specific rules | MEDIUM | D6 is the health divisional; lagna lord and 6th lord positions in D6 are computed but no scope rules check them |
| Lagna lord nakshatra / body constitution | MEDIUM | Each nakshatra corresponds to a body region and elemental constitution (Vata/Pitta/Kapha); not used |
| Moon-Saturn conjunction or aspect | MEDIUM | Classical indicator of depression, chronic nervous disorders, melancholy — not covered |
| Rahu/Ketu in other dusthanas | MEDIUM | Rahu in H8 (mysterious chronic illness), Ketu in H6 (past-life diseases, healing ability), Ketu in H8 (occult/undiagnosable) — only Rahu in H6 covered |
| Jupiter in H8 | MEDIUM | Jupiter in H8 is a longevity protector (Ayushkaraka) — no rule for it |
| Venus in H8 | LOW | Over-indulgence, substance sensitivity |
| 3rd house (longevity subset) | LOW | H3 is an upachaya and part of longevity triangle (H3, H6, H11) |
| Combustion of health significators | LOW | Combust Moon → mental health issues, combust Mars → injury risk; computed but no health rules use it |
| Ashtakavarga bindus for H6/H8 | LOW | Not computed; would give precise timing of health vulnerability periods |

---

## 5. Cross-Scope Gaps (affect all scopes)

| Gap | Affects | Importance | Notes |
|---|---|---|---|
| **Timing rules never applied** | All | CRITICAL | T001–T010 exist in `timing.yaml` but are NOT mapped to any of the 4 prediction scopes; current mahadasha/antardasha data is sent to the LLM as context but no rule fires on it |
| **Nakshatra-based rules** | All | HIGH | Nakshatra, pada, nakshatra lord, deity fully computed for all planets and lagna — zero rules use any of it |
| **Dasha lord functional role** | All | HIGH | Whether the current dasha lord is a yogakaraka, maraka, or malefic for this lagna is computed — no rules enforce timing consequences |
| **Ashtakavarga** | All | HIGH | Not computed; Ashtakavarga bindus per house are the standard tool for house-by-house strength and transit effects |
| **Transit analysis** | All | HIGH | No Gochara (transit) factors computed at all; particularly Saturn and Jupiter transits over natal positions |
| **Upachaya progression rules** | Career, Health | MEDIUM | H3, H6, H10, H11 are upachaya houses that improve with time — no rules capture this pattern |
| **Jaimini Karakas** | All | MEDIUM | Atmakaraka (soul purpose), Amatyakaraka (career), Darakaraka (spouse), Putrakaraka (children) computed and sent to LLM in varga section — no rules use them |
| **Upapada Lagna** | Relationships | MEDIUM | Not computed at all |
| **Shadbala / planetary strength scores** | All | MEDIUM | Total_strength is computed but comes from a simplified model; full Shadbala (6-fold strength) not implemented |
| **House bhava strength** | All | LOW | Bhava Bala (house strength) not computed; would allow ranking of which life areas are strongest |
| **Kartari yoga impact by house** | All | LOW | Kartari yogas detected (papakartari / subhakartari) but no rules check which specific house is hemmed |
| **Chara dasha (Jaimini)** | All | LOW | Not computed; complements Vimshottari for a second timing layer |

---

## 6. Priority Improvement Roadmap

### Immediate (add rules, no new feature computation needed)

| Scope | Add rules for |
|---|---|
| Personality | Mars/Venus/Mercury/Ketu in H1; lagna lord in H10/H4/H7/H8/H12; Pancha Mahapurusha yogas |
| Career | Venus/Mercury/Moon/Rahu/Ketu in H10; 6th lord position; 11th house lord; Dharma-Karmadhipati yoga |
| Relationships | Sun/Moon/Mercury/Rahu/Ketu in H7; 7th lord in each house (12 rules); Kuja Dosha pattern; Venus combust |
| Health | Mars in H1/H8; 6th lord in H8/H12; 8th lord in H6/H12; Rahu in H8; Ketu in H6/H8; Moon-Saturn aspect |
| **All scopes** | **Wire timing.yaml rules T001–T010 into appropriate scopes** (T002 Jupiter dasha → personality/career; T005 Venus dasha → relationships; etc.) |

### Medium-term (requires new feature computation)

| Feature | Scopes | Implementation notes |
|---|---|---|
| Nakshatra rules (Janma Nakshatra, lagna nakshatra, Venus nakshatra) | All | Data already in features; need rule DSL to match nakshatra name |
| Kuja Dosha detection | Relationships | Add yoga: Mars in H1/H2/H4/H7/H8/H12 |
| Upapada Lagna | Relationships | Compute Arudha of H12: project 12th lord from H12 by the same arc |
| Ashtakavarga basic bindus | All | Significant implementation; high value for timing and house strength |
| D6/D27/D8 specific house-lord rules | Health | Lagna lord and 6th/8th lord in D6 chart — data exists, need rules |

### Longer-term

| Feature | Notes |
|---|---|
| Gochara (transits) | Saturn/Jupiter transits over natal Moon, lagna, and natal Sun — standard Vedic timing |
| Jaimini Karakas (full) | Atmakaraka, Amatyakaraka, Darakaraka — chara karaka system |
| Shadbala full computation | 6-fold planetary strength replaces simplified total_strength |
| Chara dasha | Secondary timing system to cross-validate Vimshottari predictions |
