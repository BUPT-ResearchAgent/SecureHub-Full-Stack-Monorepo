# Status: real

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import re


class HeadingLevel(IntEnum):
    """Semantic heading levels used by Chinese textbook Markdown exports."""

    BOOK = 0
    PART = 1
    CHAPTER = 2
    SECTION = 3
    SUBSECTION = 4
    ITEM = 5
    UNKNOWN = 99


CHAPTER_RE = re.compile(r"^第\s*[\d一二三四五六七八九十百]+\s*章(?:\s|$|[、,，:：])")
PART_RE = re.compile(r"^第\s*[\d一二三四五六七八九十百]+\s*(?:部分|篇|编)(?:\s|$|[、,，:：])")
SUBSECTION_RE = re.compile(r"^\d+\.\d+\.\d+\s")
SECTION_RE = re.compile(r"^\d+\.\d+(?!\.)\s")
ITEM_RE = re.compile(r"^(?:[(（]?\d+[)）\.]|[一二三四五六七八九十]+[、\.])")


@dataclass(slots=True, frozen=True)
class ClassifiedHeading:
    raw: str
    text: str
    level: HeadingLevel
    line_no: int


def classify_heading(raw_line: str, *, line_no: int) -> ClassifiedHeading | None:
    """Classify Markdown heading text by semantic textbook level."""

    stripped = raw_line.lstrip()
    if not stripped.startswith("#"):
        return None

    hash_count = 0
    while hash_count < len(stripped) and stripped[hash_count] == "#":
        hash_count += 1
    if hash_count == 0 or hash_count > 6:
        return None

    text = stripped[hash_count:].strip()
    if not text:
        return None

    if hash_count == 1:
        return ClassifiedHeading(
            raw=raw_line.rstrip(),
            text=text,
            level=HeadingLevel.BOOK,
            line_no=line_no,
        )

    if CHAPTER_RE.search(text):
        level = HeadingLevel.CHAPTER
    elif PART_RE.search(text):
        level = HeadingLevel.PART
    elif SUBSECTION_RE.match(text):
        level = HeadingLevel.SUBSECTION
    elif SECTION_RE.match(text):
        level = HeadingLevel.SECTION
    elif ITEM_RE.match(text):
        level = HeadingLevel.ITEM
    else:
        level = HeadingLevel.UNKNOWN

    return ClassifiedHeading(
        raw=raw_line.rstrip(),
        text=text,
        level=level,
        line_no=line_no,
    )
