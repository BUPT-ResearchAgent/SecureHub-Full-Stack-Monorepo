# Status: real

from app.services.knowledge.chapter_classifier import HeadingLevel, classify_heading


def test_classify_heading_recognises_chinese_textbook_levels() -> None:
    cases = [
        ("## 第1章 密码学概论", HeadingLevel.CHAPTER),
        ("## 第 三 章 网络攻击", HeadingLevel.CHAPTER),
        ("## 第一部分 密码学基础", HeadingLevel.PART),
        ("## 1.1 信息安全", HeadingLevel.SECTION),
        ("## 1.1.1 机密性", HeadingLevel.SUBSECTION),
        ("## (1) 机密性", HeadingLevel.ITEM),
        ("## 1. 攻击的主要形式", HeadingLevel.ITEM),
        ("## 其它任意文本", HeadingLevel.UNKNOWN),
    ]

    for line, expected in cases:
        heading = classify_heading(line, line_no=1)

        assert heading is not None
        assert heading.level == expected


def test_classify_heading_handles_leading_whitespace() -> None:
    heading = classify_heading("   ## 1.1 信息安全目标", line_no=12)

    assert heading is not None
    assert heading.text == "1.1 信息安全目标"
    assert heading.level == HeadingLevel.SECTION
    assert heading.line_no == 12


def test_classify_heading_returns_none_for_non_heading() -> None:
    assert classify_heading("第1章 密码学概论", line_no=1) is None
    assert classify_heading("", line_no=2) is None


def test_classify_heading_treats_h1_as_book_title() -> None:
    heading = classify_heading("# 现代密码学教程", line_no=3)

    assert heading is not None
    assert heading.level == HeadingLevel.BOOK
    assert heading.text == "现代密码学教程"


def test_classify_heading_avoids_false_chapter_matches() -> None:
    heading = classify_heading("## 第一次警告", line_no=1)

    assert heading is not None
    assert heading.level == HeadingLevel.UNKNOWN


def test_classify_heading_accepts_chapter_with_colon_separator() -> None:
    heading = classify_heading("## 第十二章：密码协议", line_no=1)

    assert heading is not None
    assert heading.level == HeadingLevel.CHAPTER
