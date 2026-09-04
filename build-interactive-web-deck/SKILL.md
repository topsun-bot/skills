---
name: build-interactive-web-deck
description: Convert user-provided notes, documents, reports, research, or source material into a polished interactive web presentation that can replace a conventional slide deck. Use when Codex is asked to make a web deck, visual storybook, clickable atlas, flipbook-like presentation, hand-drawn presentation website, interactive briefing, or a browser-based presentation with presenter notes, citations, hotspots, nonlinear exploration, and fullscreen delivery.
---

# Build Interactive Web Deck

Create a self-contained, responsive web presentation with two complementary experiences:

- **Presentation mode:** linear, distraction-free, keyboard-friendly delivery.
- **Explore mode:** clickable annotations, branching paths, evidence, and self-guided reading.

Aim for the confidence of a well-edited talk and the curiosity of an illustrated field notebook. Derive a fresh visual identity from the material; do not clone a reference site's exact branding, artwork, or trade dress.

## Workflow

### 1. Inspect the source before designing

- Read every supplied artifact and inspect relevant workspace files first.
- Use the appropriate document, PDF, spreadsheet, browser, or research skill when the source format requires it.
- Separate confirmed facts, evidence-backed inference, and unresolved items.
- Preserve the source's meaning. Do not trade accuracy for visual drama.
- Browse for current or niche facts when required, and prefer primary sources.

### 2. Resolve consequential uncertainty

Ask only about missing decisions that materially change the result: audience, speaking duration, confidentiality/publication, required brand system, output location, or whether the deliverable is for live presentation, self-guided reading, or both. Use clickable 2–3 option questions when available and put the recommended choice first. Do not manufacture questions when the material already answers them.

If no direction is given, default to:

- both presentation and explore modes;
- the source language;
- a 10–15 minute talk with 8–14 core pages plus optional deep dives;
- a local, dependency-free static site;
- an original editorial field-notebook look with warm paper, ink, muted teal, and restrained coral accents.

### 3. Build the narrative before the interface

Read [references/deck-contract.md](references/deck-contract.md) and create the page plan before generating artwork or writing code.

- Give the deck one governing question and a clear beginning, development, and conclusion.
- Make each core page express one claim that can be spoken in one sentence.
- Use deep-dive pages for evidence, mechanisms, or cases that would overload the main route.
- Give every page a visual job: compare, locate, sequence, explain a mechanism, show a system, reveal evidence, or invite a decision.
- Write speaker notes as spoken language, not copied body text.
- Attach citations and claim boundaries to the page they support.

### 4. Direct the visual system

Read [references/visual-direction.md](references/visual-direction.md) before producing imagery.

- Use a coherent art direction across all pages.
- Prefer one hero illustration or diagram per page over card grids and dense dashboards.
- When bitmap illustration materially improves the result and image generation is available, use the image generation skill. Keep important text in HTML, not inside generated images.
- Store all final assets locally in the output. Add descriptive alt text and record whether each image is generated, supplied, or sourced.
- Use visual metaphors that clarify the claim. Avoid decorative art that competes with it.

### 5. Scaffold and author the site

Create the output with:

```bash
python3 <skill-dir>/scripts/scaffold_web_deck.py \
  --output <output-dir> \
  --title "<deck title>"
```

Then replace the sample in `deck-data.js`, add local images under `assets/`, and refine the styles only as needed. Keep the runtime dependency-free unless the requested interaction truly requires a framework.

The shipped template already provides:

- explore/presentation modes;
- local and branching hotspots;
- previous/next controls, map, progress, timer, and fullscreen;
- speaker-notes and evidence drawers;
- copy controls, optional sound cues, keyboard shortcuts, focus states, mobile layout, and reduced-motion handling.

Do not remove these behaviors merely to finish faster. Adapt them to the content.

### 6. Validate the artifact

Run structural validation:

```bash
python3 <skill-dir>/scripts/validate_web_deck.py <output-dir>
```

Then serve the directory over HTTP and inspect it in a real browser:

```bash
python3 -m http.server 4173 --directory <output-dir>
```

Verify at minimum:

1. landing page renders with no console errors;
2. every core page and map entry opens;
3. previous/next and keyboard navigation work;
4. explore hotspots open the correct card or branch;
5. presentation mode removes exploratory clutter;
6. notes, evidence, timer, fullscreen, and copy controls work;
7. layout remains legible at desktop and narrow widths;
8. missing assets, broken citations, overflow, and accidental placeholder text are absent;
9. `prefers-reduced-motion` keeps the deck usable;
10. claims in the page, notes, and evidence panel agree.

Do not call static validation, mocked interaction, or a screenshot alone complete browser acceptance.

### 7. Hand off clearly

Return the clickable path to `index.html`, the source folder, and a short run command. Summarize the narrative and art direction, list any unverified claims or missing assets, and state exactly which browser interactions were exercised. If publishing was not requested, stop at the local deliverable.
