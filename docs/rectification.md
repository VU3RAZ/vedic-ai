# Birth-Time Rectification

Given an *approximate* birth time and the **actual dates** of major life events,
this engine finds the birth time whose chart most strongly activates those events
on those exact dates. It is the inverse of the [Life Events Timeline](life_events_timeline.md):
the timeline asks *when* an event is likely; rectification asks *which birth time*
makes the known events line up.

- **Engine:** `src/vedic_ai/engines/rectification.py`
- **API:** `POST /rectify/compute`, `GET /rectify/domains` (`src/vedic_ai/api/routes_rectification.py`)
- **UI:** "🎯 Rectify" tab in `src/vedic_ai/static/index.html`

---

## Why birth time matters

A small change in birth time reshapes the chart in three timing-critical ways:

1. **Lagna (ascendant)** moves ~1°/4 min and changes whole-sign at ~2 h
   boundaries → every bhāva lordship changes.
2. **Moon's nakṣatra / longitude** changes ~0.5°/h → the **Vimśottarī daśā
   balance** shifts, moving *when* every daśā/antardaśā runs.
3. **Divisional charts** (D9, D7, D10, …) are extremely time-sensitive.

So two birth times a few minutes apart can place a marriage daśā years apart — which
is exactly the signal rectification exploits.

---

## Algorithm

For each candidate birth time `t = given_time + offset`:

1. Recompute the full chart + vargas (`D4, D7, D9, D10, D16, D20, D24`).
2. For every supplied event `(domain, actual_date)`, call
   `life_events.score_event_fit(...)` which finds the daśā/antardaśā **active on
   that date** and scores activation = daśā-phala (BPHS 47) + varga confirmation
   (BPHS 7) + Guru/Śani Gochara (PD 26). **The classical age-prior is disabled** —
   the date is a known fact, so it must not be re-biased toward the "expected" age.
3. Sum the per-event scores → the candidate's **fitness**.

The search is two-stage to stay responsive:

- **Coarse sweep** — step every `coarse_step` minutes across ±`window_minutes`.
- **Fine sweep** — step every `fine_step` minutes around the best coarse hit.

The candidate with the highest fitness is the **rectified birth time**.

A typical ±2 h / 15 min search evaluates ~30 charts in well under a second.

---

## API

### `POST /rectify/compute`

```json
{
  "birth_datetime": "1972-08-15T10:30:00+05:30",
  "latitude": 21.15,
  "longitude": 79.08,
  "place_name": "Nagpur",
  "name": "Native",
  "events": [
    { "domain_key": "marriage",     "actual_date": "2000-05-15" },
    { "domain_key": "first_child",  "actual_date": "2003-09-10" },
    { "domain_key": "career_start", "actual_date": "1995-07-01" }
  ],
  "window_minutes": 120,
  "coarse_step": 15,
  "fine_step": 2
}
```

`domain_key` values come from `GET /rectify/domains` (same catalog as the
timeline: `marriage`, `first_child`, `career_start`, `career_peak`,
`education_higher`, `property_house`, `vehicle`, `financial_success`,
`health_challenge`, `foreign_travel`, `spiritual_awakening`, `education_primary`).

### Response (abridged)

```json
{
  "original": { "birth_datetime": "...10:30...", "total_fit": 44.0, "lagna_sign": "Libra", "per_event": [...] },
  "best":     { "birth_datetime": "...11:30...", "total_fit": 46.0, "lagna_sign": "Libra",
                "moon_nakshatra": "Swati",
                "per_event": [
                  { "label": "Marriage / Partnership", "actual_date": "2000-05-15",
                    "score": 22, "dasha_score": 14, "varga_score": 5, "transit_score": 3,
                    "mahadasha_lord": "Jupiter", "antardasha_lord": "Mars", "factors": [...] }
                ] },
  "candidates": [ ...top N by fitness... ],
  "delta_minutes": 60,
  "fit_improvement": 2.0,
  "lagna_changed": false,
  "moon_sign_changed": false,
  "search": { "window_minutes": 120, "coarse_step": 15, "fine_step": 2, "evaluated": 25 },
  "disclaimer": "..."
}
```

---

## Public functions

| Function | Purpose |
|----------|---------|
| `rectify(birth, engine, events, window_minutes=120, coarse_step=15, fine_step=2, top_n=6, use_transits=True)` | Run the two-stage search; returns `RectificationResult`. |
| `life_events.score_event_fit(bundle, domain_key, target_date, chara=None, indu=None, engine=None)` | Activation score for one event on one date (age-prior disabled). |
| `life_events.list_domains()` | Event-domain catalog for UI selectors. |

---

## UI

The Rectify tab lets the user add `(event, date)` rows, choose a search window
(±30 min … ±12 h for a fully unknown time) and coarse step, then runs the search.
Results show:

- a **given → rectified** hero with the time delta and fitness improvement,
- whether the **Lagna / Moon sign** changed,
- a **per-event activation table** (fit score with daśā/varga/transit breakdown
  and the active Mahā/Antardaśā lords),
- a **top-candidates** bar chart, and
- an **Apply & recompute** button that writes the rectified time back into the
  birth form.

> **Disclaimer.** Rectification suggests the birth time best matching the supplied
> events per classical timing rules. It is probabilistic and improves with more
> well-dated events; it is not a substitute for an accurate birth record.
