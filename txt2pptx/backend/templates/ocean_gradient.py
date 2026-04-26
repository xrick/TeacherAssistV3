"""Ocean Gradient template strategy.

This is the canonical baseline — every other template's font_scale is
calibrated relative to this one. Layout indices and placeholder map
match the structure produced by utils/fix_for_pptx_format.py.
"""
from .base import TemplateStrategy
from ..models import SlideLayout


class OceanGradientStrategy(TemplateStrategy):
    template_file = "ocean_gradient.pptx"

    layout_map = {
        SlideLayout.TITLE:       0,   # CENTER_TITLE + SUBTITLE
        SlideLayout.SECTION:     1,   # SECTION_HEADER (TITLE + SUBTITLE)
        SlideLayout.BULLETS:     2,   # TITLE_AND_BODY (TITLE + BODY + PICTURE)
        SlideLayout.TWO_COLUMN:  3,   # TITLE_AND_TWO_COLUMNS
        SlideLayout.IMAGE_LEFT:  4,   # TITLE_ONLY (TITLE + BODY右 + PICTURE左)
        SlideLayout.IMAGE_RIGHT: 5,   # ONE_COLUMN_TEXT (TITLE + BODY左 + PICTURE右)
        SlideLayout.KEY_STATS:   6,   # CAPTION_ONLY (BODY標題 + BODY×3)
        SlideLayout.COMPARISON:  7,   # TITLE_AND_TWO_COLUMNS_1
        SlideLayout.CONCLUSION:  8,   # BLANK (TITLE + BODY)
    }

    placeholder_map = {
        "title":      0,
        "body":       1,
        "body_right": 2,
        "body_col2":  3,
        "body_col3":  4,
        "picture":   10,
        "slide_num": 12,
    }

    font_scale = 1.0
    aspect_ratio = (13.33, 7.5)
