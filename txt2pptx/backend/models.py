# txt2pptx/backend/models.py
"""Data models for TXT2PPTX pipeline."""
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class SlideLayout(str, Enum):
    TITLE = "title_slide"
    SECTION = "section_header"
    BULLETS = "bullets"
    TWO_COLUMN = "two_column"
    IMAGE_LEFT = "image_left"
    IMAGE_RIGHT = "image_right"
    KEY_STATS = "key_stats"
    COMPARISON = "comparison"
    CONCLUSION = "conclusion"


class StatItem(BaseModel):
    value: str
    label: str


class SlideData(BaseModel):
    layout: SlideLayout
    title: str
    subtitle: Optional[str] = None
    bullets: Optional[list[str]] = None
    left_column: Optional[list[str]] = None
    right_column: Optional[list[str]] = None
    left_title: Optional[str] = None
    right_title: Optional[str] = None
    stats: Optional[list[StatItem]] = None
    image_prompt: Optional[str] = None
    speaker_notes: str = Field(default="", min_length=50, max_length=200, description="詳細補充說明，50-100字為佳")


class PresentationOutline(BaseModel):
    title: str
    subtitle: Optional[str] = None
    theme: Optional[str] = "professional"
    slides: list[SlideData]


class GenerateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)
    num_slides: int = Field(default=8, ge=3, le=20)
    language: str = Field(default="zh-TW")
    style: str = Field(default="professional")
    template: str = Field(default="code_drawn")


class GenerateResponse(BaseModel):
    success: bool
    filename: Optional[str] = None
    message: str
    outline: Optional[PresentationOutline] = None
