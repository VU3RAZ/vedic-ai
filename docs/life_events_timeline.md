# Life Events Timeline

A 120-year, śāstra-based timing engine that predicts *when* key life events are
most likely to occur. It does **not** use generic house overlap — every score is
derived from explicit classical techniques and each contributing factor cites its
source.

- **Engine:** `src/vedic_ai/engines/life_events.py`
- **API:** `POST /life-events/compute` (`src/vedic_ai/api/routes_life_events.py`)
- **UI:** "🕐 Timeline" tab in `src/vedic_ai/static/index.html`

---

## Classical techniques combined

| # | Technique | Source | Role in scoring |
|---|-----------|--------|-----------------|
| 1 | Vimśottarī Daśā-phala | BPHS Ch.46-47 | A bhāva fructifies in the daśā/antardaśā of its **lord**, its **occupants**, planets **aspecting** it (graha-dṛṣṭi), and its **naisargika kāraka**. |
| 2 | Jaimini Chara Kārakas | Jaimini Sūtras 1.1.10-18 | 8-kāraka scheme (incl. Rāhu). Darākāraka→marriage, Putrakāraka→children, Amātyakāraka→career, Gnātikāraka→disease, Mātṛkāraka→property/education/vehicle, Ātmakāraka→spirituality. |
| 3 | Ṣoḍaśavarga confirmation | BPHS Ch.7 | The event-specific divisional chart must confirm: D9 marriage, D7 children, D10 career, D4 property, D16 vehicle, D24 education, D20 spirituality. |
| 4 | Indu (Dhana) Lagna | Jātaka Pārijāta | Wealth timing via the kalā sum of the 9th-lords from Lagna and Moon. |
| 5 | Gochara of Guru & Śani | Phaladīpikā Ch.26 | Jupiter/Saturn transit **from the natal Moon** at the antardaśā midpoint acts as the trigger; Sāḍe-Sātī is detected and penalises positive events. |

Reference legend used in factor strings: `BPHS` = Bṛhat Parāśara Horā Śāstra ·
`JS` = Jaimini Sūtras · `PD` = Phaladīpikā · `JP` = Jātaka Pārijāta ·
`SAR` = Sārāvalī.

---

## How a window is scored

For every Mahādaśā→Antardaśā window across 120 years and for each event domain:

1. **Significator set (BPHS 47).** Built once per chart: the bhāva lord (weight 4),
   chara-kāraka (3), naisargika kāraka (3), occupants (2), aspecting planets (2),
   and (for wealth) the Indu-Lagna lord (3).
2. **Daśā activation.** If the Mahādaśā lord is in the set it scores full weight;
   the Antardaśā lord scores half. A dignity modifier (±1) is applied to active
   lords (BPHS 7).
3. **Age prior (PD/SAR).** +3 if the window midpoint is inside the classical age
   window, +1 for partial overlap, −8 if entirely outside (prevents implausible
   late-life outliers).
4. **Varga confirmation (BPHS 7).** The relevant divisional chart is scored on its
   own internal house lords, dignities, and kāraka placement.
5. **Gochara trigger (PD 26).** Jupiter/Saturn house-from-Moon at the antardaśā
   midpoint adds or subtracts.

The total maps to a confidence band:

| Score | Confidence |
|-------|-----------|
| ≥ 18 | Very High |
| 13–17 | High |
| 8–12 | Moderate |
| 4–7 | Low |
| < 4 | Very Low |

Repeating domains (property, vehicle, wealth, foreign travel, health) return up to
**3 non-overlapping** high-scoring windows; one-time domains return the single best.

---

## Event domains

| Domain | Bhāvas | Naisargika kāraka | Chara kāraka | Varga | Age window |
|--------|--------|-------------------|--------------|-------|------------|
| Primary/Secondary Education | 2,4,5 | Mercury, Jupiter | MK | D24 | 5–18 |
| Higher Education | 4,5,9 | Jupiter, Mercury | MK | D24 | 16–30 |
| Career / First Employment | 6,10,11 | Sun, Saturn, Mercury | AmK | D10 | 18–35 |
| Career Peak | 9,10,11 | Sun, Jupiter, Saturn | AmK | D10 | 30–65 |
| Marriage | 2,7,11 | Venus, Jupiter | DK | D9 | 18–50 |
| First Child | 5,9 | Jupiter | PK | D7 | 22–55 |
| Property / House | 4,11,12 | Mars, Moon, Saturn | MK | D4 | 25–70 |
| Vehicle | 4,11 | Venus, Mars | MK | D16 | 18–70 |
| Financial Wealth | 2,9,11 | Jupiter, Venus, Mercury | — (Indu Lagna) | — | 28–75 |
| Health Challenge | 6,8,12 | Saturn, Mars, Rahu | GK | — | 1–90 |
| Foreign Travel | 9,12,3 | Rahu, Saturn | — | — | 18–80 |
| Spiritual Growth | 9,12,5 | Jupiter, Ketu, Saturn | AK | D20 | 35–120 |

---

## API

### Request — `POST /life-events/compute`

```json
{
  "birth_datetime": "1972-08-15T10:30:00+05:30",
  "latitude": 21.15,
  "longitude": 79.08,
  "place_name": "Nagpur",
  "name": "Native",
  "ayanamsa": "lahiri",
  "house_system": "whole_sign"
}
```

`birth_datetime` **must** include a timezone offset.

### Response (abridged)

```json
{
  "name": "Native",
  "total_events": 22,
  "by_category": { "Marriage": 1, "Property": 3, "...": 0 },
  "methods": {
    "chara_karakas": [
      { "role": "DK", "planet": "Jupiter", "meaning": "Darākāraka — spouse / marriage" }
    ],
    "indu_lagna": { "house_from_lagna": 4, "lord": "Saturn" },
    "references": "BPHS 46-47, Jaimini Sūtras 1.1, BPHS 7 (Ṣoḍaśavarga), Jātaka Pārijāta, Phaladīpikā 26"
  },
  "events": [
    {
      "label": "Marriage / Partnership",
      "category": "Marriage",
      "start_date": "2000-04-12",
      "end_date": "2001-02-20",
      "age_start": 27.7,
      "age_end": 28.6,
      "score": 26,
      "confidence": "Very High",
      "mahadasha_lord": "Jupiter",
      "antardasha_lord": "Mars",
      "method_note": "7th-lord/Darākāraka (JS) daśā; Śukra=Kalatra-kāraka; D9 Navāṁśa confirms (BPHS 7).",
      "supporting_factors": [
        "Jupiter (MD) DK Chara-kāraka [JS 1.1.10-18 (Chara Kāraka)] +3",
        "Mars (AD) rules H7 in D9 [BPHS 7 (Ṣoḍaśavarga)]",
        "[PD 26 (Gochara of Guru/Śani from Moon)] Guru śubha-gochara H2 from Moon — triggers event"
      ],
      "divisional_signal": "Mars (AD) rules H2 in D9; Mars (AD) rules H7 in D9",
      "transit_signal": "[PD 26 ...] Guru śubha-gochara H2 from Moon — triggers event"
    }
  ]
}
```

---

## Public functions

| Function | Purpose |
|----------|---------|
| `compute_life_events(bundle, engine=None)` | Full 120-year timeline. Pass `engine` to enable Gochara confirmation. Returns `list[LifeEventPrediction]` sorted by start date. |
| `compute_chara_karakas(bundle)` | `{Graha: role}` Jaimini 8-kāraka assignment. |
| `compute_indu_lagna(bundle)` | `(house_from_lagna, lord)` per Jātaka Pārijāta. |

The bundle must include the vargas `D4, D7, D9, D10, D16, D20, D24` (the API route
requests these automatically).

---

## UI

The Timeline tab renders:

- a **Jaimini Chara Kāraka** panel + Indu Lagna + reference list,
- a **0–120 year age bar** with clickable event markers,
- **category filter chips**, and
- **event cards** showing the daśā lords, confidence band, methodology line, and
  every cited supporting factor (D1 daśā-phala, varga confirmation, Gochara).

> **Disclaimer.** Predictive timing in Jyotiṣa is probabilistic. These windows
> indicate periods of heightened likelihood per classical rules, not certainties.
