# TXT2PPTX — Project Hand-over Manual

**Author of this document:** outgoing developer (closing transfer)
**Last revised:** 2026-04-25
**Audience:** the next programmer continuing work on this codebase
**Reading time:** ~30 minutes for a thorough first pass

---

## 0. TL;DR — Read This First

You are inheriting a working FastAPI web app that converts plain text into PowerPoint decks via an LLM-generated outline. The codebase is small (≈2k Python lines, no build step on the frontend) and most of it is straightforward. **The single non-trivial design topic you must understand before touching anything is the template strategy system in `txt2pptx/backend/templates/`** — it was rewritten in this final transfer cycle to solve the recurring "every new template breaks the layout" problem.

Three things to do on day one:

1. Read **§4 Architecture overview** (10 min) and **§5 The Template Strategy system** (15 min).
2. Run the test pipeline end-to-end (`§7 How to run / develop`). If it doesn't pass, stop and fix the environment before writing code.
3. Skim **§9 Known issues & gotchas** so you don't lose a day to a problem already discovered.

Everything else can be looked up as needed.

---

## 1. Project Snapshot

| Attribute | Value |
|---|---|
| **Name** | TXT2PPTX (sometimes called "TeacherAssist" in the UI) |
| **Goal** | Convert Chinese/English text into a professional `.pptx` deck |
| **Stack** | Python 3.10+, FastAPI, Uvicorn, python-pptx, Pydantic v2, Ollama (LLM), vanilla HTML/CSS/JS |
| **UI language** | Traditional Chinese (zh-TW), some English fallbacks |
| **LLM** | Ollama, OpenAI-compatible endpoint (default model `gpt-oss:20b`) |
| **Status** | Functional. 8 templates supported. Upload-and-onboard workflow for arbitrary user templates is wired up but requires manual code addition (by design — see §5.4). |
| **Test framework** | None configured. Verification is via dedicated CLI scripts in `txt2pptx/utils/`. |

### Estimated maturity vs. gamma.app

The previous developer's claim was the project covers ≈30–40 % of gamma.app's text-to-pptx core. After the strategy refactor (§5) the **template-handling story is now solid**, but several gamma.app features remain unimplemented — see §10 Roadmap.

---

## 2. Quick Glossary

| Term | Meaning |
|---|---|
| **Outline** | Intermediate structured representation. A `PresentationOutline` (Pydantic model) of `SlideData` items. Produced by the LLM, consumed by the generator. |
| **SlideLayout** | Enum of 9 layout types (`title_slide`, `section_header`, `bullets`, `two_column`, `image_left`, `image_right`, `key_stats`, `comparison`, `conclusion`). Each `SlideData` declares one. |
| **Template** | A `.pptx` file in `txt2pptx/templates/` that supplies the visual look. |
| **Strategy** | A Python class in `txt2pptx/backend/templates/` (subclass of `TemplateStrategy`) that knows the recalculated parameters for one specific template — which slide-layout indices to use, which placeholder idx is title/body, the font scale, etc. |
| **Code-drawn mode** | Alternative path that skips templates entirely and draws every shape via Inches coordinates (`pptx_generator.py`). Kept for backward compatibility. |
| **Demo fallback** | When Ollama is unreachable, the LLM call falls back to a heuristic text-splitter (`generate_outline_demo` in `llm_service.py`). Produces structurally-valid but cosmetically poor outlines. |

---

## 3. Repository Layout

```
TeacherAssistV3/
├── CLAUDE.md                       # ≪ project instructions for Claude/AI tooling
├── claudedocs/                     # human + AI-authored docs
│   ├── HANDOVER.md                 # ◀ THIS FILE
│   ├── dev_diary/                  # dated work log
│   ├── how_to/                     # task-specific guides
│   └── … older analyses
├── pptxenv/                        # Python venv (gitignored ideally)
├── refData/                        # reference papers/specs (read-only)
└── txt2pptx/                       # ◀ ALL CODE LIVES HERE
    ├── backend/
    │   ├── main.py                 # FastAPI entrypoint
    │   ├── models.py               # Pydantic models — schemas of truth
    │   ├── llm_service.py          # Ollama client + demo fallback
    │   ├── pptx_generator.py       # code-drawn generator (no template)
    │   ├── pptx_generator_template.py  # legacy template generator (kept as fallback)
    │   └── templates/              # ◀ NEW STRATEGY PACKAGE (§5)
    │       ├── __init__.py         # STRATEGIES registry
    │       ├── base.py             # TemplateStrategy ABC
    │       ├── ocean_gradient.py   # canonical baseline strategy
    │       ├── college_elegance.py # one strategy per supported template
    │       ├── data_centric.py
    │       ├── high_contrast.py
    │       ├── minimalist_corporate.py
    │       ├── modernist.py
    │       ├── startup_edge.py
    │       └── zen_serenity.py
    ├── frontend/                   # vanilla HTML/CSS/JS, no build step
    │   ├── index.html
    │   ├── app.js
    │   └── style.css
    ├── generated/                  # output PPTX files (auto-created)
    ├── templates/                  # the .pptx template files themselves
    │   ├── ocean_gradient.pptx
    │   ├── College_Elegance.pptx
    │   ├── … 6 more
    │   └── MyCustom.pptx           # ⚠ leftover from upload-flow test, see §11
    ├── utils/                      # ◀ NEW TOOLING (§5.4)
    │   ├── __init__.py
    │   ├── inspect_template.py     # introspect any .pptx
    │   ├── scaffold_template_class.py  # auto-generate a strategy skeleton
    │   └── validate_template_class.py  # end-to-end validator
    ├── start.sh / stop.sh          # PID-managed Uvicorn lifecycle
    └── server.log                  # runtime log (gitignored ideally)
```

---

## 4. Architecture Overview

### 4.1 Three-stage pipeline

```
┌──────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│ User text    │ ──> │ LLM outline service  │ ──> │ PPTX generator       │ ──> .pptx
│ (frontend)   │     │ llm_service.py       │     │ TemplateStrategy +   │
└──────────────┘     │ (Ollama or demo)     │     │ python-pptx          │
                     └──────────────────────┘     └──────────────────────┘
                              │                              │
                              ▼                              ▼
                   PresentationOutline             ocean_gradient.pptx,
                   (validated Pydantic)            College_Elegance.pptx, …
```

Stage 1 is well-isolated: the LLM is asked to return strict JSON conforming to `PresentationOutline`. The system prompt (in `llm_service.py:SYSTEM_PROMPT`, ~50 lines of Chinese) does most of the work. Retries (`LLM_MAX_RETRIES`, default 3) wrap the call.

Stage 2 is where this transfer cycle's work lives. The dispatcher in `main.py` chooses one of three paths based on `request.template`:

| `request.template` | Path |
|---|---|
| `"code_drawn"` | `pptx_generator.generate_pptx()` — programmatic shapes, no template file |
| anything in `STRATEGIES` (8 entries today) | `STRATEGIES[id]().generate(outline)` — strategy class fills placeholders in the matching `.pptx` |
| anything else | `pptx_generator_template.generate_pptx()` — legacy single-script generator (kept as a safety net) |

### 4.2 The `PresentationOutline` contract

This is the data shape both sides must agree on. See `backend/models.py`:

- `PresentationOutline` has `title`, `subtitle`, `theme`, `slides: list[SlideData]`.
- `SlideData` has every possible field for every layout type. Each layout uses a subset (e.g. `BULLETS` uses `title` + `bullets`; `KEY_STATS` uses `title` + `stats: list[StatItem]`; `TWO_COLUMN` uses `left_title/left_column/right_title/right_column`).
- `speaker_notes: str` has a Pydantic constraint `min_length=50, max_length=200`. **This constraint has bitten the demo fallback twice — see §9.1.** Any code that constructs `SlideData` and passes a non-empty `speaker_notes` shorter than 50 characters will raise `ValidationError`.

### 4.3 Frontend at a glance

`frontend/` is intentionally low-tech: three files, no bundler, no React. `app.js` is ~300 lines and uses thin selector helpers (`els.foo()`). The UI calls four endpoints:

- `POST /api/generate` — main flow
- `GET /api/templates` — populate the template dropdown
- `GET /api/download/{filename}` — download the produced PPTX
- `POST /api/upload-template` — added in this cycle (§5.5)

---

## 5. The Template Strategy System

This is the chapter to read carefully.

### 5.1 The problem we were solving

Before this cycle, `pptx_generator_template.py` had a **single hard-coded `LAYOUT_MAP` and `placeholder_map`** that every template was assumed to obey:

```python
LAYOUT_MAP = {
    SlideLayout.TITLE: 0, SlideLayout.SECTION: 1, SlideLayout.BULLETS: 2, …
}
PH_TITLE = 0; PH_BODY = 1; PH_PICTURE = 10; PH_SLIDE_NUM = 12
```

This worked for `ocean_gradient.pptx` because it had been hand-tuned via `utils/fix_for_pptx_format.py` to match those numbers. The other 7 templates were "supported" only because the loader didn't crash — the placeholder indices were often wrong, and content silently went to the wrong shapes (or got dropped).

The previous lead identified this as the project's central technical difficulty in `CLAUDE.md` ("when applying different reference pptx template, the whole parameters of this new referenced pptx template needs to be recalculated").

### 5.2 The chosen solution: Strategy pattern + scaffolding tools

We rejected the gamma.app-style "any user template, fully automatic" approach. Reasons:

1. Real templates have arbitrary layout count, arbitrary placeholder indices, and variable aspect ratios. No heuristic produces consistently good output.
2. Even gamma.app shows visible quality drops on user-uploaded themes.
3. The supported template set is small (8) and grows slowly. Hand-tuning is manageable.

Instead, we built:

- **A `TemplateStrategy` abstract base class** that encapsulates one template's recalculated parameters and exposes a uniform `generate(outline) -> bytes` API.
- **One concrete subclass per supported template** with hardcoded `layout_map`, `placeholder_map`, `font_scale`, `aspect_ratio`. Subclasses can override any `fill_*` method when the default behaviour isn't enough.
- **A 5-step onboarding workflow** for adding the next template: 80 % of the work is automated by `inspect_template.py` and `scaffold_template_class.py`; the remaining 20 % is the human resolving `TODO` comments and validating the output.
- **An upload UI** that lets a non-developer drop a `.pptx` file into the system. If a strategy is already registered for that filename, it works immediately. Otherwise the UI shows the 5-step instructions in a modal and disables the option until a developer registers it.

### 5.3 The `TemplateStrategy` contract

File: `backend/templates/base.py`. Every concrete strategy inherits from this class. Class-level attributes a subclass MUST set or accept defaults for:

| Attribute | Type | Purpose |
|---|---|---|
| `template_file` | `str` | Filename inside `txt2pptx/templates/` (e.g. `"ocean_gradient.pptx"`) |
| `layout_map` | `dict[SlideLayout, int]` | Maps each of the 9 SlideLayouts to the slide-layout index in the .pptx |
| `placeholder_map` | `dict[str, int]` | Semantic name → placeholder idx. Required keys: `title`, `body`. Optional: `body_right`, `body_col2`, `body_col3`, `picture`, `slide_num` |
| `font_scale` | `float` | Multiplier applied to hardcoded font sizes (e.g. `0.85`); calibrated against `ocean_gradient` (= 1.0) |
| `aspect_ratio` | `tuple[float, float]` | Slide dimensions in inches |

The default `fill_*` methods (one per `SlideLayout`) handle the common case of placing text into the named placeholder. Override only if a layout needs special treatment (none of the 8 current strategies override anything — the defaults are sufficient).

The class also has a fallback chain in `_layout_index` so that if a strategy doesn't map (say) `IMAGE_LEFT`, requests for that layout type fall back to `BULLETS`. In practice the scaffolder fills every slot, so this is rarely triggered.

### 5.4 The 5-step onboarding workflow (the deliverable)

When a new `.pptx` template arrives:

```bash
# 1. Inspect the template — see its layouts, placeholders, theme
python -m txt2pptx.utils.inspect_template MyTemplate.pptx

# 2. Generate a strategy class skeleton
python -m txt2pptx.utils.scaffold_template_class MyTemplate.pptx
#  → writes backend/templates/my_template.py with TODOs

# 3. Manually edit my_template.py
#    - Resolve any TODO comments
#    - Verify auto-detected layout_map mappings match what the design intends
#    - Tune font_scale if rendered text looks too big/small

# 4. Validate
python -m txt2pptx.utils.validate_template_class MyTemplateStrategy
#  → writes /tmp/validation/validation_MyTemplateStrategy.pptx
#    Open it in PowerPoint or LibreOffice and inspect visually

# 5. Register in backend/templates/__init__.py
#    Add the import + STRATEGIES entry. 1-2 lines.
```

Steps 1, 2, 4 are tooling. Step 3 is the human judgment call. Step 5 is mechanical.

The scaffolder uses three passes to guarantee every `SlideLayout` gets a layout assignment:

1. **Keyword match** on layout names — a multilingual table (`LAYOUT_KEYWORDS`) recognizes English, Chinese, and German layout names.
2. **Auto-fill remaining slots** with any unused layout that has a real content placeholder (skipping pure blank/footer-only layouts — that bug bit us once, see §9.2).
3. **Last-resort fallback** to the BULLETS layout for any still-unmapped slot.

This is why all 8 current templates pass the validator's "every slide has visible text" check: the scaffolder never leaves a `SlideLayout` unmapped.

### 5.5 Upload flow (the user-facing UX)

```
┌────────────────────────────────────────────────────────────────────┐
│ User clicks "上傳自訂模板 (.pptx)"                                  │
│      │                                                             │
│      ▼                                                             │
│ POST /api/upload-template (multipart)                              │
│      │                                                             │
│      ├── Saves to txt2pptx/templates/<name>.pptx                   │
│      ├── Validates with python-pptx (rejects malformed files)      │
│      └── Checks STRATEGIES dict                                    │
│           │                                                        │
│      ┌────┴────┐                                                   │
│      ▼         ▼                                                   │
│  registered    NOT registered                                      │
│  (200 OK)      (202 Accepted)                                      │
│      │         │                                                   │
│      │         └─→ returns onboarding payload:                     │
│      │             { steps: [{cmd, desc} × 5] }                    │
│      │             frontend shows modal with 5 numbered steps      │
│      │                                                             │
│      ▼                                                             │
│  refresh /api/templates dropdown, select the new template          │
└────────────────────────────────────────────────────────────────────┘
```

Notes:

- The endpoint always saves the file. This makes the developer's life easier (the .pptx is already in `templates/`, ready for `inspect_template`).
- An unregistered template appears in the dropdown labeled `<name> ⚠ 未註冊` and is `disabled` until the next server restart after registration.
- `/api/templates` exposes `is_registered: bool` per template; the frontend uses this to gray-out unsupported entries.

### 5.6 What this system does **not** solve

Be honest with yourself and your stakeholders:

- **Auto-fitting text to arbitrary placeholder sizes** — `font_scale` is a single global multiplier, not a per-shape recalculation. Long bullets in tight templates can overflow.
- **Theme-aware color extraction** — strategies don't read the template's `theme1.xml` to recolor accent shapes added by code. We didn't need this because the 9 default `fill_*` methods only set text content, not colors.
- **Content-aware layout selection** — gamma.app picks layouts based on content shape ("4 short bullets → BULLETS, 2 long passages → TWO_COLUMN"). Here the LLM does this in the outline; the strategy just renders.
- **Image insertion** — the `image_prompt` field on `SlideData` is collected but no image is actually placed. PICTURE placeholders remain empty. (Gamma calls a generation API. We don't.)

If you commit to closing any of these gaps, file an issue and budget at least one full week per item.

---

## 6. File-by-file Inventory of This Cycle's Changes

### 6.1 Files added

| File | Purpose | Size |
|---|---|---|
| `backend/templates/__init__.py` | `STRATEGIES` registry; helper functions `get_strategy` / `is_registered` / `list_registered` | ~40 lines |
| `backend/templates/base.py` | `TemplateStrategy` ABC — the contract every strategy implements | ~290 lines |
| `backend/templates/ocean_gradient.py` | First concrete strategy. `font_scale=1.0` is the calibration baseline. | ~38 lines |
| `backend/templates/college_elegance.py` | Auto-scaffolded then registered | ~60 lines |
| `backend/templates/data_centric.py` | "" | ~60 lines |
| `backend/templates/high_contrast.py` | "" | ~60 lines |
| `backend/templates/minimalist_corporate.py` | "" | ~60 lines |
| `backend/templates/modernist.py` | "" | ~60 lines |
| `backend/templates/startup_edge.py` | "" | ~60 lines |
| `backend/templates/zen_serenity.py` | "" | ~60 lines |
| `utils/__init__.py` | empty package marker | 0 lines |
| `utils/inspect_template.py` | Read-only template introspection. `--json` flag for tooling. | ~200 lines |
| `utils/scaffold_template_class.py` | Strategy class generator with multilingual heuristics. | ~330 lines |
| `utils/validate_template_class.py` | 7-check end-to-end validator. `--all` flag iterates the registry. | ~270 lines |

### 6.2 Files modified

| File | What changed |
|---|---|
| `backend/main.py` | (a) wired `STRATEGIES` into `/api/generate` dispatch; (b) added `is_registered` field in `/api/templates`; (c) added `POST /api/upload-template` endpoint with onboarding payload. |
| `backend/llm_service.py` | Extended two demo-mode `speaker_notes` strings to ≥50 chars to satisfy the Pydantic `min_length` constraint. **Pre-existing bug, not caused by this cycle's work** but blocked verification — see §9.1. |
| `frontend/index.html` | Added file-upload button next to the template selector and a modal element for the 5-step warning. |
| `frontend/app.js` | Added upload handler, `is_registered` rendering in the dropdown, modal show/close. |
| `frontend/style.css` | Styles for the upload button, status badges, and modal (≈140 lines appended). |

### 6.3 Files NOT modified but worth knowing

| File | Why it matters |
|---|---|
| `backend/pptx_generator_template.py` | The **legacy** template generator. Still present and reachable via the `else` branch in `main.py` for any template whose name isn't in `STRATEGIES`. Kept deliberately as a safety net. Once you trust the strategy system in production, you can remove this file and the dispatch branch. |
| `backend/pptx_generator.py` | The fully **code-drawn** generator. ~460 lines. Still the active path when `request.template == "code_drawn"`. Independent of templates. Useful for debugging because it has zero external dependencies on .pptx files. |
| `backend/llm_service.py` (rest) | Has a robust 3-attempt retry loop, the system prompt, and the demo fallback. Read top-to-bottom once. |
| `start.sh` / `stop.sh` | PID-managed Uvicorn lifecycle. Uses `txt2pptx/server.log` for output. Read these instead of guessing how to start the server. |

---

## 7. How to Run / Develop / Verify

### 7.1 First-time setup

```bash
cd TeacherAssistV3

# Activate the venv (the previous developer used pptxenv/, but it may be missing in fresh environments)
python3 -m venv pptxenv
source pptxenv/bin/activate

# Dependencies — there is no requirements.txt yet (see §10)
pip install fastapi uvicorn python-pptx pydantic httpx python-multipart

# If you plan to run with Ollama, install it separately and pull the model:
ollama pull gpt-oss:20b
```

### 7.2 Running the server

```bash
cd txt2pptx
OLLAMA_MODEL=gpt-oss:20b bash start.sh        # PID-managed
# or
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open `http://localhost:8000`.

```bash
curl http://localhost:8000/api/health     # {"status":"ok",…}
bash stop.sh
```

### 7.3 Validating a template strategy (the developer loop)

```bash
# from repo root, NOT txt2pptx/
python -m txt2pptx.utils.validate_template_class --all              # all registered
python -m txt2pptx.utils.validate_template_class OceanGradientStrategy  # one
```

Output goes to `/tmp/validation/validation_<Name>.pptx`. **Always open it visually** before claiming a strategy works — the validator only checks structural correctness, not aesthetics.

### 7.4 Smoke test of the API end-to-end

There is no automated test suite (yet — see §10). The script the previous developer used during transfer is below; copy into `/tmp/test_gen.py`:

```python
import json, urllib.request

PAYLOAD = {
    "text": "人工智慧（AI）正在革命性地改變各行各業。…",
    "num_slides": 5,
    "language": "zh-TW",
    "style": "professional",
}
TEMPLATES = ["ocean_gradient", "College_Elegance", "Data_Centric",
             "High_Contrast", "Minimalist_Corporate", "Modernist",
             "Startup_Edge", "Zen_Serenity"]

for tid in TEMPLATES:
    body = dict(PAYLOAD, template=tid)
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/generate",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=900) as r:
        data = json.loads(r.read())
    print(f"{tid:24s}  success={data.get('success')}  file={data.get('filename')}")
```

Expected: `success=True` for all 8.

### 7.5 Testing the upload flow without the UI

```bash
# Registered template
curl -X POST http://127.0.0.1:8000/api/upload-template \
     -F "file=@txt2pptx/templates/ocean_gradient.pptx"

# Unregistered template (rename to trigger the 202 path)
cp txt2pptx/templates/ocean_gradient.pptx /tmp/SomeNewLook.pptx
curl -X POST http://127.0.0.1:8000/api/upload-template \
     -F "file=@/tmp/SomeNewLook.pptx" -w "\nHTTP %{http_code}\n"
```

The second call should return HTTP 202 and a JSON body with a `steps` array.

---

## 8. API Reference (Concise)

### `POST /api/generate`
Body (`GenerateRequest`):
```json
{
  "text": "string (1..50000)",
  "num_slides": 8,
  "language": "zh-TW",
  "style": "professional",
  "template": "ocean_gradient"
}
```
Response (`GenerateResponse`): `{ success, filename, message, outline }`.

### `GET /api/templates`
Returns `{ templates: [{ id, name, description, available, is_template, is_registered }] }`.

### `POST /api/upload-template` (multipart)
Field name: `file`. Returns 200 if registered, 202 with onboarding payload if not, 400 if malformed.

### `GET /api/download/{filename}`
Streams the PPTX with the correct MIME type.

### `GET /api/health`
`{"status":"ok","version":"0.1.0"}`.

---

## 9. Known Issues & Gotchas

### 9.1 Demo-fallback `speaker_notes` length is fragile

`SlideData.speaker_notes` has `min_length=50`. The demo fallback constructs hard-coded notes; **two of these are short enough that a one-character edit can break Pydantic validation**. We extended both to ≥56 chars during this cycle, but the underlying brittleness remains. Future fix: either lower `min_length` to 30 or have the demo fallback synthesise notes programmatically. See `llm_service.py:186` and `:269`.

### 9.2 Heuristic must skip "blank" layouts when matching CONCLUSION

Several PowerPoint themes ship with a "Leer" / "Blank" layout that has only DATE/FOOTER/SLIDE_NUMBER placeholders. The first version of the scaffolder matched these to `CONCLUSION` because of the `"blank"` keyword — result: empty conclusion slides. **Fixed** in `scaffold_template_class.py` by introducing `_has_content_placeholder()` and removing the misleading keywords. If you add new keywords, do not include `"blank"`/`"leer"` for any non-blank `SlideLayout`.

### 9.3 Placeholder idx is per-layout, not global

The `placeholder_map` in each strategy is a flat `dict[str, int]`. This works because all 8 supported templates happen to use stable indices across layouts (idx 0 = title, idx 1 = body in nearly every layout). **This assumption can break for any future template.** If it does, the cleanest fix is to extend `TemplateStrategy` so `placeholder_map` becomes `dict[SlideLayout, dict[str, int]]` (per-layout). Keep an eye on this.

### 9.4 SOCKS proxy + httpx

If the environment has `ALL_PROXY` set to a SOCKS URL, httpx will refuse to start without `socksio`. Install `httpx[socks]` or unset the env var before launching.

### 9.5 Sandbox file-permission gotcha during transfer

During the upload-flow smoke test we left a leftover file `txt2pptx/templates/MyCustom.pptx`. It is a valid PPTX (a copy of `ocean_gradient.pptx`) but has no registered strategy, so it shows as `⚠ 未註冊` in the UI. **Please delete it manually**:

```bash
rm txt2pptx/templates/MyCustom.pptx
```

(The previous developer's sandbox didn't have permission to delete it.)

### 9.6 No tests, no linter, no requirements.txt

These were on the previous developer's "want to add" list. None blocking. See §10.

### 9.7 The `code_drawn` generator and the strategy generator drift independently

If you change `Theme` colours or layout coordinates in `pptx_generator.py`, **none of the strategy classes pick that up** — they each read from their own `.pptx` file. This is fine architecturally, but be aware so you don't expect "I tweaked the brand colour" to propagate.

### 9.8 Frontend "簡報風格" select is intentionally hidden

`index.html` has a `<!-- commented-out -->` block for the style selector. The user can see only template selection. Don't accidentally re-enable it without first deciding what `style` should mean alongside `template`.

---

## 10. Roadmap & Suggested Next Work

In rough priority order. Each item is a contained week or less unless noted.

### High-leverage, low risk

1. **Add a `requirements.txt`** with pinned versions, derived from the current `pptxenv/`. One-hour task.
2. **Add a smoke-test script** in `txt2pptx/test/` (this folder already exists per CLAUDE.md). At minimum, run `validate_template_class --all` and the API smoke test from §7.4 in CI. Half-day task.
3. **Pre-commit hook** running `python -m compileall txt2pptx/` and `python -m pyflakes txt2pptx/` to catch syntax breaks early. One-hour task.
4. **Delete the leftover `MyCustom.pptx`** (§9.5).

### Medium

5. **Real image insertion in PICTURE placeholders.** Pick an image source (Unsplash search by `image_prompt`? Local AI image gen?) and wire it into the `_fill_image_left/right` methods. 1 week.
6. **Auto-fit text** — measure rendered text width via PIL or python-pptx text-frame autosize and adjust `font_scale` per-shape. 1 week.
7. **Theme-aware colour pulling** — in each strategy, read the template's `theme1.xml` and recolour any decorative shapes the code adds. 3 days.
8. **Per-layout placeholder maps** (§9.3) when the next template breaks the flat-map assumption. 2 days.

### Larger

9. **A proper test suite** with `pytest`. Especially golden-file tests for each strategy: render the validation deck, assert XML structure matches a snapshot. 1 week.
10. **Drop the legacy `pptx_generator_template.py`** once you trust the strategy registry has no regressions for ≥1 month in production. Update `main.py` to remove the legacy fallback branch. Half-day cleanup.
11. **Inline editing UI** — the closest gap to gamma.app parity. Render the outline on the page with editable cells before final generation. 2 weeks minimum.

### Speculative

12. **Plug-in marketplace for templates** — let users share strategy classes. Requires sandboxing untrusted code; not trivial.

---

## 11. Decision Log — Why Things Are the Way They Are

### Why Strategy pattern, not a config file?

We prototyped both. A single `templates.yaml` listing layout indices and font scales is shorter (~10 lines per template), but it can't express override behaviour. The instant a template needs a custom `_fill_key_stats` (think: stats laid out in a circle instead of a row) the YAML approach forces invention of a mini-language. Subclassing keeps overrides as plain Python.

### Why three passes in the scaffolder?

Pass 1 alone leaves gaps (fail loud). Pass 2 alone produces silly assignments because rich layouts get matched by name even when the user clearly intended something else. The combination means: rule-based when names are descriptive, fall back gracefully when they aren't, and never leave a slot empty.

### Why keep the legacy `pptx_generator_template.py`?

Risk management. The strategy system is new. If a regression appears in production, the legacy generator gives the operator one config-flag away from a working build. Drop after a month of incident-free strategy-only operation.

### Why fail-closed on upload (require manual class registration)?

Because gamma.app's "any template, fully automatic" UX is the wrong target for this codebase's resourcing. Producing visibly broken output is worse than refusing the file with a clear path to fix it. The developer cost per added template is ~10–30 min of manual review — affordable.

### Why is `font_scale` a single number?

Pragmatism. A perfect implementation would compute font size per `_fill_*` method based on placeholder dimensions. But (a) we don't have ground truth for "correct" font sizes per template, and (b) the templates we ship were authored by humans for human-scale text — so a single global scale is usually within a few points of right. Revisit only if a real overflow problem appears.

---

## 12. Things I Would Tell My Past Self

1. **Read `models.py` first, every time.** Most subtle bugs in this codebase trace back to a Pydantic constraint silently rejecting a value.
2. **Run the validator before opening any PowerPoint file.** It's much faster.
3. **Don't trust the LLM to produce exactly 9-slide outlines.** It usually does, but treat the count as a request, not a guarantee.
4. **The frontend has no build step** — `Ctrl-R` is your only deploy. Don't introduce one without strong justification; the simplicity is a feature.
5. **The `claudedocs/` folder is full of intermediate analyses** from earlier work cycles. Most are still useful as context, but they pre-date this cycle's strategy refactor. When in doubt, this HANDOVER.md supersedes them.

---

## 13. Contact & Further Reading

- The CLAUDE.md at the repo root has the canonical "what does this project do" pitch and the recent-updates log.
- `claudedocs/dev_diary/2026-02-17_speaker_notes_optimization.md` documents the speaker_notes 50-character constraint design.
- `claudedocs/重試機制設計文件.md` covers the LLM retry strategy.
- `claudedocs/architecture_analysis_dual_engine.md` covers the code-drawn vs template-based dual-path design.
- The `refData/` folder has external papers and specs (read-only).

When in doubt, read the source. It's small.

Good luck. — outgoing developer
