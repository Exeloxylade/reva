---
name: reva-browse
description: "BRANCH 2D - REVA Web Browsing & External Ingredient Sourcing. Equip REVA Engineering Lab to fetch JS-rendered docs, take diagram screenshots, discover direct asset links (PDF/SVG/MP4/GLB/CSV/MP3), and source external ingredients across 6 open aisles: docs/papers (Wikipedia/OpenAlex/arXiv), diagrams/photos (Wikimedia Commons/Openverse), archival footage (Internet Archive), CC audio (Openverse Audio), downloadable 3D models (Sketchfab), and datasets/geo (Nominatim/World Bank). Use whenever a study needs outside references, diagrams, real data, footage, audio, or 3D assets."
---

# REVA Browse & External Ingredient Sourcing

Think of REVA Lab as an engineering studio that needs verified outside **ingredients** ("groceries") before building any scene or style: technical specifications, diagrams, archival b-roll, CC soundscapes, 3D reference geometry, and real quantitative datasets.

- **Headless Browser Kit:** [`lab/kit/web_capture.py`](../../lab/kit/web_capture.py) (`web-browser` in [`lab/engines.json`](../../lab/engines.json))
- **CLI Entry Points:** `python reva.py research browse ...` and `python reva.py research shop ...`

---

## 1. The 6 External Ingredient Aisles (`reva research shop`)

Search one aisle or `"all"` aisles in a single command, caching downloaded items cleanly under `studies/<study>/research/assets/`:

| Aisle | Flag | Live Providers (+ Optional Env Keys) | Returns / Caches |
|---|---|---|---|
| **Docs & Papers** | `--aisle docs` | Wikipedia (EN/ID), OpenAlex, **arXiv API**, DDG (`TAVILY_API_KEY`, `BRAVE_API_KEY`) | Standard summaries, paper URLs, DOI/PDF links |
| **Diagrams & Photos** | `--aisle images` | Wikimedia Commons, **Openverse Images** (`PEXELS_API_KEY`, `PIXABAY_API_KEY`) | SVG/PNG/JPG diagrams, reference photos + licenses |
| **Archival Footage** | `--aisle footage` | **Internet Archive (`mediatype:movies`)**, Wikimedia Video (`PEXELS_API_KEY`) | Public-domain / CC footage URLs & MP4 derivatives |
| **CC Audio & Foley** | `--aisle audio` | **Openverse Audio**, Wikimedia Audio (`FREESOUND_API_KEY`) | CC-licensed SFX, ambient & foley MP3/WAV/OGG links |
| **3D Models** | `--aisle models3d` | **Sketchfab Search API** (`downloadable=true`) | Downloadable `.glb`/`.gltf` viewer URLs, vertex counts, CC licenses |
| **Datasets & Geo** | `--aisle data` | **OpenStreetMap Nominatim**, **World Bank Indicators** | Lat/lon bounding boxes, GeoJSON bounds, macro indicator IDs |

### Quick Commands
```cmd
python reva.py research shop my-study "concrete stirrup 135" --aisle images --download 2
python reva.py research shop my-study "construction hammer" --aisle audio --max-results 5
python reva.py research shop my-study "concrete column" --aisle models3d --max-results 5
python reva.py research shop my-study "bridge construction" --aisle footage --max-results 5
python reva.py research shop my-study "Jakarta" --aisle data
```

---

## 2. Rendering JS Pages & Discovering Embedded Assets (`reva research browse`)

Plain HTTP (`research fetch`) cannot execute client-side JavaScript. Use **`browse`** when a site loads diagrams, math, interactive tables, or asset links dynamically:

```cmd
python reva.py research browse my-study "https://example.org/spec" --query "135 degree seismic hook" --discover-links
```

- Renders full client-side DOM via local Edge/Chrome `--headless=new` (`--dump-dom`).
- Strips boilerplate and caches readable text in `research/assets/<slug>.txt`.
- Saves a visual screenshot `research/assets/<slug>.png` (skip with `--no-screenshot`) so you can inspect diagrams with `read_file`.
- With `--discover-links`, extracts direct `.svg`, `.png`, `.pdf`, `.mp4`, `.glb`, `.csv`, `.json`, and `.mp3` links from the rendered page.

---

## 3. When to Use Headless CLI (`reva research browse`) vs Interactive Agent (`/browser`)

| Use **REVA CLI (`research shop` / `browse` / `fetch`)** when... | Use **Interactive Agent Browser (`/browser`)** when... |
|---|---|
| Sourcing public docs, specs, arXiv/OpenAlex papers, Wikimedia diagrams, Internet Archive clips, Sketchfab models, Openverse audio, or datasets | Logging into an authenticated site or navigating gated SaaS portals |
| Batch-capturing reproducible study evidence (`research/assets/` + `brief.json`) | Clicking UI filters, scrolling infinite galleries, or human-in-the-loop curation |
| Running automated `research auto` or repeatable lab scripts | Inspecting or debugging live interactive web apps visually |

---

## 4. Optional API Keys (All Documented & Optional)

All core aisles work out-of-the-box with zero API keys. Adding optional environment variables unlocks richer results automatically:

- `TAVILY_API_KEY` / `BRAVE_API_KEY` — broad web search for `research search` & `docs` aisle
- `PEXELS_API_KEY` / `PIXABAY_API_KEY` — HD stock b-roll photos & videos (`images` / `footage`)
- `FREESOUND_API_KEY` — targeted SFX/foley clips (`audio`)

---

## 5. Quality, Attribution & Safety Guardrails

- **Always inspect downloaded visuals:** Open downloaded diagrams and screenshots (`research/assets/*.png`) with `read_file` before referencing their measurements or anatomy.
- **Record licenses:** Keep the source `url` and license (`CC-BY`, `CC0`, `PD`) recorded via `add-source` / `shop --download` for proper attribution.
- **Never bypass gates or copy IP:** `web_capture.py` immediately halts and reports `blocked_by_gate` on CAPTCHA / Cloudflare walls—never attempt to bypass CAPTCHAs, paywalls, or private accounts, and never copy third-party logos or characters verbatim into generated renders.
