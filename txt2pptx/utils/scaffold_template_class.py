"""scaffold_template_class.py — generate a TemplateStrategy subclass skeleton.

Reads template structure via inspect_template, applies heuristics to guess
layout_map, placeholder_map, and font_scale, and writes a Python file to
backend/templates/<snake_case_name>.py with TODO comments where guesses
are uncertain.

Usage:
    python -m txt2pptx.utils.scaffold_template_class <template.pptx>
    python -m txt2pptx.utils.scaffold_template_class <template.pptx> --force
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

from .inspect_template import inspect, TemplateReport, LayoutInfo

# ────────────────────────────────────────────────
# Heuristic mappings
# ────────────────────────────────────────────────

# Keywords in layout names that suggest a SlideLayout match.
# Ordered by specificity: first match wins.
LAYOUT_KEYWORDS = [
    # English / Chinese / German keywords. Order matters — first match wins.
    ("TITLE",       ["title slide", "cover", "title_slide", "titelfolie", "封面"]),
    ("SECTION",     ["section header", "section_header", "abschnitt", "divider", "章節"]),
    ("KEY_STATS",   ["stats", "metrics", "kpi", "caption_only", "namenskarte", "數據", "統計"]),
    ("COMPARISON",  ["comparison", "compare", "vergleich", "vs.", "two_columns_1",
                     "two_columns_alt", "對比"]),
    ("TWO_COLUMN",  ["two column", "two_columns", "two-col", "two contents", "zwei inhalte",
                     "split", "雙欄"]),
    ("IMAGE_LEFT",  ["image left", "image_left", "圖左", "panoramabild"]),
    ("IMAGE_RIGHT", ["image right", "image_right", "one_column_text",
                     "bild mit überschrift", "圖右"]),
    # NOTE: "blank/leer" intentionally excluded — those layouts usually have no
    # title/body placeholder, which would render an empty conclusion slide.
    ("CONCLUSION",  ["conclusion", "summary", "結論", "總結", "thank you", "danke"]),
    ("BULLETS",     ["title and content", "title_and_body", "title and body", "titel und inhalt",
                     "inhalt mit", "content with", "bullets", "條列", "list"]),
    # Title-only layouts → BULLETS fallback (single body region)
    ("BULLETS",     ["title only", "title_only", "nur titel"]),
    # A bare "TITLE"/"Titel" at the start usually means cover
    ("TITLE",       ["title", "titel"]),
]


def _has_content_placeholder(layout: LayoutInfo) -> bool:
    """True if the layout has at least a TITLE/CENTER_TITLE or BODY/OBJECT/SUBTITLE
    placeholder — i.e., it can hold content. Pure blank/footer-only layouts return False."""
    for ph in layout.placeholders:
        if ph.type in ("TITLE", "CENTER_TITLE", "BODY", "OBJECT", "SUBTITLE"):
            return True
    return False

# Reference (ocean_gradient) BODY dimensions used to compute font_scale
REFERENCE_BODY_AREA_IN2 = 8.58 * 5.30  # ~45.5 sq in

# Required SlideLayout enum values (must all appear in layout_map)
SLIDE_LAYOUT_NAMES = [
    "TITLE", "SECTION", "BULLETS", "TWO_COLUMN",
    "IMAGE_LEFT", "IMAGE_RIGHT", "KEY_STATS", "COMPARISON", "CONCLUSION",
]


def _snake_case(name: str) -> str:
    """Convert 'College_Elegance' or 'CollegeElegance' to 'college_elegance'."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    s3 = s2.replace("-", "_").replace(" ", "_").lower()
    # Collapse multiple consecutive underscores
    return re.sub(r"_+", "_", s3).strip("_")


def _camel_case(name: str) -> str:
    """Convert 'college_elegance' to 'CollegeElegance'."""
    parts = re.split(r"[_\s\-]+", name)
    return "".join(p.capitalize() for p in parts if p)


# ────────────────────────────────────────────────
# Heuristics
# ────────────────────────────────────────────────

def _match_layout(layout: LayoutInfo, used: set[int]) -> Optional[str]:
    name_lower = layout.name.lower()
    for slide_layout, keywords in LAYOUT_KEYWORDS:
        for kw in keywords:
            if kw in name_lower:
                return slide_layout
    return None


def _classify_placeholders(layout: LayoutInfo) -> dict[str, int]:
    """Return semantic→idx mapping for one layout.
    Picks the first placeholder of each semantic type by ph.type.

    Note: PowerPoint's OBJECT placeholder type is functionally a content
    placeholder (text/image/chart), so we treat it as BODY for content slides.
    """
    mapping = {}
    body_indices = []
    picture_indices = []
    for ph in layout.placeholders:
        t = ph.type
        if t in ("CENTER_TITLE", "TITLE") and "title" not in mapping:
            mapping["title"] = ph.idx
        elif t == "SUBTITLE" and "body" not in mapping:
            mapping["body"] = ph.idx
        elif t in ("BODY", "OBJECT"):  # OBJECT is generic content placeholder
            body_indices.append(ph.idx)
        elif t == "PICTURE":
            picture_indices.append(ph.idx)
        elif t == "SLIDE_NUMBER" and "slide_num" not in mapping:
            mapping["slide_num"] = ph.idx

    # Distribute BODY/OBJECT placeholders into body / body_right / body_col2 / body_col3
    body_slots = ["body", "body_right", "body_col2", "body_col3"]
    for i, idx in enumerate(body_indices):
        if i < len(body_slots) and body_slots[i] not in mapping:
            mapping[body_slots[i]] = idx

    # Picture placeholder (only set if distinct from body indices)
    for pidx in picture_indices:
        if pidx not in body_indices:
            mapping["picture"] = pidx
            break

    return mapping


def _build_layout_map(report: TemplateReport) -> tuple[dict[str, int], dict[str, str]]:
    """Return (layout_map, todo_messages_per_slide_layout).

    Strategy:
      1. Keyword match against layout names — but only for layouts that have
         a real content placeholder (skip pure blank/footer-only layouts).
      2. For SlideLayouts still unmapped, auto-assign to an unused rich
         layout (preferring one whose name suggests content).
      3. As a last resort, reuse BULLETS for missing slots so the fallback
         in TemplateStrategy._layout_index isn't needed at runtime.
    """
    layout_map: dict[str, int] = {}
    todos: dict[str, str] = {}
    used: set[int] = set()

    # Pass 1: keyword match (only on layouts with content placeholders)
    for layout in report.layouts:
        if not _has_content_placeholder(layout):
            continue
        match = _match_layout(layout, used)
        if match and match not in layout_map:
            layout_map[match] = layout.index
            used.add(layout.index)

    # Pass 2: auto-assign remaining SlideLayouts to unused rich layouts
    rich_unused = [l for l in report.layouts
                   if l.index not in used and _has_content_placeholder(l)]
    for sl in SLIDE_LAYOUT_NAMES:
        if sl in layout_map:
            continue
        if rich_unused:
            picked = rich_unused.pop(0)
            layout_map[sl] = picked.index
            used.add(picked.index)
            todos[sl] = (f"auto-assigned to layout {picked.index} "
                         f"\"{picked.name}\" — VERIFY this fits {sl}")

    # Pass 3: last-resort fallback to BULLETS for any still-missing slot
    bullets_idx = layout_map.get("BULLETS")
    if bullets_idx is not None:
        for sl in SLIDE_LAYOUT_NAMES:
            if sl not in layout_map:
                layout_map[sl] = bullets_idx
                todos[sl] = (f"reusing BULLETS layout (idx {bullets_idx}) — "
                             f"no dedicated layout found, consider customising")

    return layout_map, todos


def _build_placeholder_map(report: TemplateReport, layout_map: dict[str, int]) -> dict[str, int]:
    """Aggregate placeholder map by inspecting the BULLETS layout (most common).
    Falls back to any layout that has body+title.

    NOTE: PowerPoint placeholder idx is per-layout, so an idx valid in one
    layout may be a different placeholder in another. Augmentations from
    other layouts only run when the idx doesn't clash with already-chosen ones.
    """
    target_idx = layout_map.get("BULLETS")
    if target_idx is None:
        for layout in report.layouts:
            classified = _classify_placeholders(layout)
            if "title" in classified and "body" in classified:
                target_idx = layout.index
                break
    if target_idx is None and report.layouts:
        target_idx = report.layouts[0].index

    target_layout = next((l for l in report.layouts if l.index == target_idx), None)
    if target_layout is None:
        return {"title": 0, "body": 1, "slide_num": 12}

    mapping = _classify_placeholders(target_layout)
    used_indices = set(mapping.values())

    # Augment picture from a layout that explicitly has a PICTURE placeholder
    # (only if its idx doesn't collide with what we've already chosen).
    if "picture" not in mapping:
        for layout in report.layouts:
            for ph in layout.placeholders:
                if ph.type == "PICTURE" and ph.idx not in used_indices:
                    mapping["picture"] = ph.idx
                    used_indices.add(ph.idx)
                    break
            if "picture" in mapping:
                break

    # Augment col2/col3 from KEY_STATS if missing
    stats_idx = layout_map.get("KEY_STATS")
    if stats_idx is not None:
        stats_layout = next((l for l in report.layouts if l.index == stats_idx), None)
        if stats_layout:
            stats_cls = _classify_placeholders(stats_layout)
            for k in ("body_right", "body_col2", "body_col3"):
                if k not in mapping and k in stats_cls and stats_cls[k] not in used_indices:
                    mapping[k] = stats_cls[k]
                    used_indices.add(stats_cls[k])

    # Slide number: pick from any layout
    if "slide_num" not in mapping:
        for layout in report.layouts:
            for ph in layout.placeholders:
                if ph.type == "SLIDE_NUMBER":
                    mapping["slide_num"] = ph.idx
                    break
            if "slide_num" in mapping:
                break

    return mapping


def _compute_font_scale(report: TemplateReport, layout_map: dict[str, int]) -> float:
    """Compute font_scale from BULLETS body placeholder area vs reference."""
    bullets_idx = layout_map.get("BULLETS")
    if bullets_idx is None:
        return 1.0
    layout = next((l for l in report.layouts if l.index == bullets_idx), None)
    if layout is None:
        return 1.0
    body = next((p for p in layout.placeholders
                 if p.type == "BODY" and p.width_in is not None), None)
    if body is None or body.width_in is None or body.height_in is None:
        return 1.0
    area = body.width_in * body.height_in
    ratio = (area / REFERENCE_BODY_AREA_IN2) ** 0.5
    # Clamp to a sane range
    return round(max(0.6, min(1.3, ratio)), 2)


# ────────────────────────────────────────────────
# Code generation
# ────────────────────────────────────────────────

CLASS_TEMPLATE = '''"""{class_name} template strategy — auto-scaffolded.

Source: {template_file}
Aspect: {aspect}
Detected layouts: {n_layouts}

⚠️  This file was auto-generated by scaffold_template_class.py.
    Review every TODO comment before using in production.
"""
from .base import TemplateStrategy
from ..models import SlideLayout


class {class_name}Strategy(TemplateStrategy):
    template_file = "{template_file}"

    layout_map = {{
{layout_map_lines}
    }}

    placeholder_map = {{
{placeholder_map_lines}
    }}

    font_scale = {font_scale}  # TODO: tune if rendered text looks too big/small
    aspect_ratio = ({width}, {height})


# ────────────────────────────────────────────────
# Detection report (for reference)
# ────────────────────────────────────────────────
# Layouts found:
{layouts_comment}
'''


def _safe(s: str) -> str:
    """Strip newlines/quotes from a string so it can be embedded in a Python comment."""
    return s.replace("\n", " ").replace("\r", " ").replace('"', "'").strip()


def _format_layout_map(layout_map: dict[str, int], todos: dict[str, str], report: TemplateReport) -> str:
    lines = []
    for sl in SLIDE_LAYOUT_NAMES:
        if sl in layout_map:
            idx = layout_map[sl]
            layout_name = next((l.name for l in report.layouts if l.index == idx), "?")
            lines.append(f'        SlideLayout.{sl:<11}: {idx},   # detected: "{_safe(layout_name)}"')
        else:
            lines.append(f'        # SlideLayout.{sl}: TODO  # {_safe(todos.get(sl, ""))}')
    return "\n".join(lines)


def _format_placeholder_map(ph_map: dict[str, int]) -> str:
    canonical_keys = ["title", "body", "body_right", "body_col2", "body_col3", "picture", "slide_num"]
    # Pad the *quoted* key, not the key itself, so dict syntax stays valid.
    width = max(len(k) for k in canonical_keys) + 2  # +2 for surrounding quotes
    lines = []
    for k in canonical_keys:
        quoted = f'"{k}"'
        if k in ph_map:
            lines.append(f'        {quoted:<{width}}: {ph_map[k]},')
        else:
            lines.append(f'        # {quoted}: TODO  # not detected — verify or remove')
    return "\n".join(lines)


def _format_layouts_comment(report: TemplateReport) -> str:
    lines = []
    for lay in report.layouts:
        ph_summary = ", ".join(
            f"idx={p.idx}({p.type})" for p in lay.placeholders[:5])
        lines.append(f'#   [{lay.index}] "{_safe(lay.name)}" — {ph_summary}')
    return "\n".join(lines)


def scaffold(template_path: Path, output_dir: Path, force: bool = False) -> Path:
    report = inspect(template_path)
    stem = template_path.stem
    snake = _snake_case(stem)
    camel = _camel_case(snake)

    layout_map, todos = _build_layout_map(report)
    ph_map = _build_placeholder_map(report, layout_map)
    font_scale = _compute_font_scale(report, layout_map)

    code = CLASS_TEMPLATE.format(
        class_name=camel,
        template_file=template_path.name,
        aspect=report.aspect_ratio,
        n_layouts=report.n_layouts,
        layout_map_lines=_format_layout_map(layout_map, todos, report),
        placeholder_map_lines=_format_placeholder_map(ph_map),
        font_scale=font_scale,
        width=report.width_in,
        height=report.height_in,
        layouts_comment=_format_layouts_comment(report),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{snake}.py"
    if output_path.exists() and not force:
        raise FileExistsError(
            f"{output_path} already exists. Re-run with --force to overwrite."
        )
    output_path.write_text(code, encoding="utf-8")
    return output_path


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a TemplateStrategy subclass from a .pptx template.")
    parser.add_argument("template", help="path to .pptx file (or filename inside templates/)")
    parser.add_argument("--force", action="store_true", help="overwrite if output file exists")
    parser.add_argument("--output-dir", default=None,
                        help="override output dir (default: backend/templates/)")
    args = parser.parse_args(argv)

    p = Path(args.template)
    if not p.exists():
        templates_dir = Path(__file__).resolve().parent.parent / "templates"
        candidate = templates_dir / args.template
        if candidate.exists():
            p = candidate
        elif (templates_dir / f"{args.template}.pptx").exists():
            p = templates_dir / f"{args.template}.pptx"

    output_dir = Path(args.output_dir) if args.output_dir else (
        Path(__file__).resolve().parent.parent / "backend" / "templates")

    out = scaffold(p, output_dir, force=args.force)
    print(f"✓ Scaffolded: {out}")
    print()
    print("Next steps:")
    print(f"  1. Edit {out} — resolve any TODO comments")
    print(f"  2. Add the class to backend/templates/__init__.py STRATEGIES dict")
    print(f"  3. python -m txt2pptx.utils.validate_template_class <ClassName>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
