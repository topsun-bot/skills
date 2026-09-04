# Deck content contract

Use one JSON-compatible object assigned to `window.DECK_DATA` in `deck-data.js`.

## Top level

```js
window.DECK_DATA = {
  "meta": {
    "title": "Required deck title",
    "subtitle": "Optional one-line promise",
    "label": "Optional series or organization",
    "estimatedMinutes": 12,
    "language": "zh-CN",
    "artDirection": "One sentence describing the visual system"
  },
  "pages": []
};
```

Use 6–20 pages. Keep the main route to the duration the user requested; mark optional supporting pages as `deepDive: true`.

## Page object

```json
{
  "id": "01",
  "chapter": "OPENING",
  "title": "A specific, speakable claim",
  "subtitle": "Optional clarification",
  "claim": "The one sentence the audience should remember",
  "image": "assets/01-opening.webp",
  "imageAlt": "Literal description of the meaningful visual content",
  "layout": "left",
  "durationSeconds": 50,
  "deepDive": false,
  "visualCue": "What the speaker should point at first",
  "speakerNotes": ["Short spoken paragraph.", "Second spoken paragraph."],
  "transition": "The sentence or action that moves to the next page.",
  "boundary": "What this page does not establish or where the claim stops.",
  "hotspots": [],
  "evidence": []
}
```

Allowed `layout` values are `left`, `right`, `bottom`, and `full`. Compose artwork with a quiet text zone matching the layout.

## Hotspot object

Coordinates are percentages of the image stage.

```json
{
  "x": 62,
  "y": 18,
  "w": 22,
  "h": 44,
  "title": "Component name",
  "summary": "Why it matters",
  "detail": "A concise explanation revealed on click.",
  "targetPage": "06",
  "sources": [0]
}
```

- Omit `targetPage` for a local annotation.
- Set `targetPage` to a valid page ID for a branching hotspot.
- Use 0–5 hotspots per page. Large, meaningful target regions are easier than tiny pins.
- `sources` contains zero-based indexes into that page's `evidence` array.

## Evidence object

```json
{
  "label": "Human-readable source title",
  "url": "https://primary.example/source",
  "publisher": "Publisher",
  "note": "The exact claim this source supports"
}
```

- Never invent a citation, publisher, measurement, or quote.
- Prefer primary sources and direct links.
- Keep quotations short; paraphrase by default.
- Put limitations in `boundary`, not in vague footer language.
- When the source material is the authority, cite the supplied filename or document title in `label`; use an empty URL only for genuinely local material.

## Narrative rules

- Core route: hook → mental model → 2–4 supporting moves → implication/decision → close.
- Optional route: mechanisms, comparisons, examples, source details, and appendices.
- Page titles should form a readable argument when viewed in the map.
- Speaker notes should fit the declared duration at roughly 180–240 Chinese characters or 110–150 English words per minute.
- A page should normally contain one hero visual, one title, one claim, and no more than three supporting labels.
- Use dark contrast pages sparingly for pivots, risks, or conclusions.
