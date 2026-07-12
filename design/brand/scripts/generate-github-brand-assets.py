#!/usr/bin/env python3
"""Deterministically generate GitHub-facing SecureHub brand assets.

Only files beneath design/brand are written. The three supplied background
images are treated as immutable input and are guarded by SHA-256 checks.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import xml.etree.ElementTree as element_tree
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


BRAND_ROOT = Path(__file__).resolve().parents[1]
MASTER_DIRECTORY = BRAND_ROOT / "master"
GENERATED_DIRECTORY = BRAND_ROOT / "generated"
ARCHIVE_DIRECTORY = BRAND_ROOT / "archive"
EXPORTS_DIRECTORY = BRAND_ROOT / "exports"
ICONS_DIRECTORY = BRAND_ROOT / "icons"
PREVIEWS_DIRECTORY = BRAND_ROOT / "previews"
MANIFEST_PATH = BRAND_ROOT / "github-brand-assets-manifest.json"

MASTER_SVG = MASTER_DIRECTORY / "logo-symbol-primary.svg"
MASTER_PNG = MASTER_DIRECTORY / "logo-symbol-primary-1024.png"
GITHUB_BACKGROUND = GENERATED_DIRECTORY / "github-social-background.png"
README_BACKGROUND = GENERATED_DIRECTORY / "readme-banner-background.png"
ARCHIVE_CONCEPT = ARCHIVE_DIRECTORY / "github-social-background-concept-a.png"
FONT_PATH = Path("C:/Windows/Fonts/NotoSansSC-VF.ttf")

BRAND_INK = "#0B1B2D"
BRAND_BLUE = "#174BFF"
BRAND_BLUE_DARK_MODE = "#4D73FF"
BRAND_TEXT = "#1F2937"
BRAND_MUTED = "#667085"
BRAND_MUTED_DARK = "#CBD5E1"
BRAND_BORDER = "#DDE3EA"
BRAND_SURFACE = "#F6F8FB"
BRAND_BACKGROUND = "#FFFFFF"
BRAND_WHITE = "#F8FAFC"

RGB = tuple[int, int, int]
INK_RGB: RGB = (11, 27, 45)
BLUE_RGB: RGB = (23, 75, 255)
TEXT_RGB: RGB = (31, 41, 55)
MUTED_RGB: RGB = (102, 112, 133)
SURFACE_RGB: RGB = (246, 248, 251)
WHITE_RGB: RGB = (255, 255, 255)
WHITE_MARK_RGB: RGB = (248, 250, 252)

BACKGROUND_HASHES = {
    "generated/github-social-background.png": "A88CF5EF350EBEC3C940526DC74B95163982559E521E311EE152C205254E5CBD",
    "generated/readme-banner-background.png": "551D7774FD00F74E36E5E08B6344E4ADB2EE9BFFDEC925EBBA2FFA5C12CECC4C",
    "archive/github-social-background-concept-a.png": "01E7B3101EDDC053AD260285E152464C66625E69E7C504AE42F3944198310C49",
}

SVG_FONT_STACK = "'Noto Sans SC', 'Microsoft YaHei', DengXian, sans-serif"
LOGO_CROP_VIEWBOX = "205 195 610 610"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def ensure_inputs() -> None:
    required = (MASTER_SVG, MASTER_PNG, GITHUB_BACKGROUND, README_BACKGROUND, ARCHIVE_CONCEPT, FONT_PATH)
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"Required brand input is missing: {path}")
    for relative_path, expected_hash in BACKGROUND_HASHES.items():
        actual_hash = sha256(BRAND_ROOT / relative_path)
        if actual_hash != expected_hash:
            raise RuntimeError(f"Immutable background hash mismatch: {relative_path}")


def load_logo_renderer() -> Any:
    renderer_path = BRAND_ROOT / "scripts" / "render-logo-assets.py"
    spec = importlib.util.spec_from_file_location("securehub_logo_renderer", renderer_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load existing logo renderer: {renderer_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def font(size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    face = ImageFont.truetype(FONT_PATH, size)
    try:
        face.set_variation_by_axes([weight])
    except OSError:
        pass
    return face


def text_top(draw: ImageDraw.ImageDraw, x: int, y: int, value: str, face: ImageFont.ImageFont, fill: RGB) -> None:
    box = draw.textbbox((0, 0), value, font=face)
    draw.text((x - box[0], y - box[1]), value, font=face, fill=fill)


def alpha_crop(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    bounds = alpha.getbbox()
    if not bounds:
        raise RuntimeError("The official logo render is empty.")
    return image.crop(bounds)


def resize_to_max(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    ratio = min(max_width / image.width, max_height / image.height)
    size = (max(1, round(image.width * ratio)), max(1, round(image.height * ratio)))
    return image.resize(size, Image.Resampling.LANCZOS)


def paste_centered(canvas: Image.Image, image: Image.Image, x: int, y: int, width: int, height: int) -> None:
    fitted = resize_to_max(image, width, height)
    target = (x + (width - fitted.width) // 2, y + (height - fitted.height) // 2)
    canvas.alpha_composite(fitted, target)


def paste_at_max(canvas: Image.Image, image: Image.Image, x: int, y: int, max_dimension: int) -> Image.Image:
    fitted = resize_to_max(image, max_dimension, max_dimension)
    canvas.alpha_composite(fitted, (x, y))
    return fitted


def master_inner_markup() -> str:
    source = MASTER_SVG.read_text(encoding="utf-8")
    opening = re.search(r"<svg\b[^>]*>", source)
    closing = source.rfind("</svg>")
    if not opening or closing < 0:
        raise RuntimeError("Official logo master is not a valid SVG container.")
    return source[opening.end() : closing].strip()


def recolored_logo_markup(ink: str, accent: str) -> str:
    return master_inner_markup().replace(BRAND_INK, ink).replace(BRAND_BLUE, accent)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def symbol_svg(ink: str, accent: str) -> str:
    return "\n".join((
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" preserveAspectRatio="xMidYMid meet">',
        recolored_logo_markup(ink, accent),
        "</svg>",
    ))


def horizontal_logo_svg(dark: bool) -> str:
    ink = BRAND_WHITE if dark else BRAND_INK
    accent = BRAND_BLUE_DARK_MODE if dark else BRAND_BLUE
    english = BRAND_MUTED_DARK if dark else BRAND_MUTED
    return "\n".join((
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 192" preserveAspectRatio="xMidYMid meet">',
        f'  <svg x="22" y="22" width="148" height="148" viewBox="{LOGO_CROP_VIEWBOX}" preserveAspectRatio="xMidYMid meet">',
        "    " + recolored_logo_markup(ink, accent).replace("\n", "\n    "),
        "  </svg>",
        f'  <text x="198" y="56" dominant-baseline="hanging" fill="{ink}" font-family="{SVG_FONT_STACK}" font-size="52" font-weight="600">安枢智梯</text>',
        f'  <text x="200" y="120" dominant-baseline="hanging" fill="{english}" font-family="{SVG_FONT_STACK}" font-size="27" font-weight="500">SecureHub</text>',
        "</svg>",
    ))


def readme_banner_svg() -> str:
    return "\n".join((
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 480" preserveAspectRatio="xMidYMid meet">',
        f'  <rect width="1440" height="480" fill="{BRAND_BACKGROUND}" />',
        '  <image id="background" href="../generated/readme-banner-background.png" x="40" y="13" width="1360" height="454" preserveAspectRatio="xMidYMid meet" />',
        f'  <svg x="96" y="86" width="80" height="80" viewBox="{LOGO_CROP_VIEWBOX}" preserveAspectRatio="xMidYMid meet">',
        "    " + recolored_logo_markup(BRAND_INK, BRAND_BLUE).replace("\n", "\n    "),
        "  </svg>",
        f'  <text x="96" y="190" dominant-baseline="hanging" fill="{BRAND_INK}" font-family="{SVG_FONT_STACK}" font-size="49" font-weight="600">安枢智梯 · SecureHub</text>',
        f'  <text x="98" y="276" dominant-baseline="hanging" fill="{BRAND_TEXT}" font-family="{SVG_FONT_STACK}" font-size="26" font-weight="400">',
        '    <tspan x="98" dy="0">面向网络安全人才培养的</tspan>',
        '    <tspan x="98" dy="38">开源智能学习与科研平台</tspan>',
        "  </text>",
        "</svg>",
    ))


ICON_SVGS: dict[str, str] = {
    "knowledge-base.svg": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" color="#174BFF" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <path d="M3.5 8.5 C5.9 7.1 8.2 7.1 10.5 8.7 V18.7 C8.2 17.1 5.9 17.1 3.5 18.5 Z" />
  <path d="M20.5 8.5 C18.1 7.1 15.8 7.1 13.5 8.7 V18.7 C15.8 17.1 18.1 17.1 20.5 18.5 Z" />
  <path d="M10.5 8.7 V18.7" />
  <circle cx="8" cy="4.5" r="1.25" />
  <circle cx="16" cy="4.5" r="1.25" />
  <path d="M9.25 4.5 H14.75" />
</svg>""",
    "learning-path.svg": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" color="#174BFF" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="4" cy="18" r="1.5" />
  <path d="M5.5 18 H8 V14 H12 V10 H16 V6" />
  <path d="M17 3.5 C17.4 4.6 18.1 5.3 19.3 5.7 C18.1 6.1 17.4 6.8 17 8 C16.6 6.8 15.9 6.1 14.7 5.7 C15.9 5.3 16.6 4.6 17 3.5 Z" />
</svg>""",
    "security-lab.svg": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" color="#174BFF" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <path d="M7 5 H5.5 A2.5 2.5 0 0 0 3 7.5 V16.5 A2.5 2.5 0 0 0 5.5 19 H7 M17 5 H18.5 A2.5 2.5 0 0 1 21 7.5 V16.5 A2.5 2.5 0 0 1 18.5 19 H17" />
  <path d="M10 4 H14 M11 4 V9 L8.5 14 A2 2 0 0 0 10.3 17 H13.7 A2 2 0 0 0 15.5 14 L13 9 V4" />
  <path d="M10.3 14 H13.7" />
  <circle cx="4" cy="12" r="1" />
  <circle cx="20" cy="12" r="1" />
</svg>""",
    "agent-collaboration.svg": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" color="#174BFF" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 12 L6.2 7.4 M12 12 L17.8 7.4 M12 12 V18.4" />
  <circle cx="12" cy="12" r="3" />
  <circle cx="5" cy="6.5" r="2" />
  <circle cx="19" cy="6.5" r="2" />
  <circle cx="12" cy="19" r="2" />
</svg>""",
    "research.svg": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" color="#174BFF" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <path d="M5 3.5 H13 L17 7.5 V20.5 H5 Z M13 3.5 V7.5 H17" />
  <path d="M8 16.5 L10.5 14 L12.5 15.5 L16 11.5" />
  <path d="M19 2.5 C19.3 3.3 19.9 3.9 20.8 4.2 C19.9 4.5 19.3 5.1 19 6 C18.7 5.1 18.1 4.5 17.2 4.2 C18.1 3.9 18.7 3.3 19 2.5 Z" />
</svg>""",
    "talent-development.svg": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" color="#174BFF" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 18.5 C6.6 17.1 9.2 17.1 12 18.8 C14.8 17.1 17.4 17.1 20 18.5" />
  <path d="M7 16 H10 V13 H13 V10 H16 V7" />
  <circle cx="16" cy="5" r="1.5" />
</svg>""",
}


def write_icons() -> None:
    for filename, content in ICON_SVGS.items():
        write_text(ICONS_DIRECTORY / filename, content)


def render_logo(renderer: Any, svg_path: Path, target_size: int = 2048) -> Image.Image:
    return alpha_crop(renderer.render_svg(svg_path, target_size))


def avatar(renderer: Any, size: int) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (*SURFACE_RGB, 255))
    logo = render_logo(renderer, EXPORTS_DIRECTORY / "logo-symbol-primary.svg")
    fitted = resize_to_max(logo, round(size * 0.81), round(size * 0.81))
    x = (size - fitted.width) // 2
    y = round((size - fitted.height) / 2 - size * 0.01)
    canvas.alpha_composite(fitted, (x, y))
    return canvas


def composite_social(renderer: Any) -> Image.Image:
    canvas = Image.new("RGBA", (1280, 640), (*WHITE_RGB, 255))
    background = Image.open(GITHUB_BACKGROUND).convert("RGBA").resize((1224, 612), Image.Resampling.LANCZOS)
    canvas.alpha_composite(background, (28, 14))
    logo = render_logo(renderer, EXPORTS_DIRECTORY / "logo-symbol-primary.svg")
    paste_at_max(canvas, logo, 88, 98, 96)
    drawing = ImageDraw.Draw(canvas)
    text_top(drawing, 88, 220, "安枢智梯", font(57, 600), INK_RGB)
    text_top(drawing, 90, 293, "SecureHub", font(30, 500), INK_RGB)
    text_top(drawing, 90, 354, "面向网络安全人才培养的", font(24, 400), TEXT_RGB)
    text_top(drawing, 90, 391, "智能学习与科研平台", font(24, 400), TEXT_RGB)
    return canvas


def composite_readme(renderer: Any) -> Image.Image:
    canvas = Image.new("RGBA", (1440, 480), (*WHITE_RGB, 255))
    background = Image.open(README_BACKGROUND).convert("RGBA").resize((1360, 454), Image.Resampling.LANCZOS)
    canvas.alpha_composite(background, (40, 13))
    logo = render_logo(renderer, EXPORTS_DIRECTORY / "logo-symbol-primary.svg")
    paste_at_max(canvas, logo, 96, 86, 80)
    drawing = ImageDraw.Draw(canvas)
    text_top(drawing, 96, 190, "安枢智梯 · SecureHub", font(49, 600), INK_RGB)
    text_top(drawing, 98, 276, "面向网络安全人才培养的", font(26, 400), TEXT_RGB)
    text_top(drawing, 98, 314, "开源智能学习与科研平台", font(26, 400), TEXT_RGB)
    return canvas


def parse_color(value: str | None, current_color: RGB) -> tuple[int, int, int, int] | None:
    if value is None or value == "none":
        return None
    if value == "currentColor":
        return (*current_color, 255)
    if value.startswith("#") and len(value) == 7:
        return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5)) + (255,)
    raise ValueError(f"Unsupported icon color: {value}")


def rasterize_icon(renderer: Any, svg_path: Path, size: int, current_color: RGB) -> Image.Image:
    root = element_tree.parse(svg_path).getroot()
    view_box = [float(value) for value in root.attrib["viewBox"].split()]
    if view_box != [0.0, 0.0, 24.0, 24.0]:
        raise ValueError(f"Unexpected icon viewBox: {svg_path}")
    supersample = 4
    scale = size * supersample / 24
    image = Image.new("RGBA", (size * supersample, size * supersample), (0, 0, 0, 0))
    drawing = ImageDraw.Draw(image)
    for element in root:
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "circle":
            fill = parse_color(element.attrib.get("fill"), current_color)
            stroke = parse_color(element.attrib.get("stroke", "currentColor"), current_color)
            center_x = float(element.attrib["cx"]) * scale
            center_y = float(element.attrib["cy"]) * scale
            radius = float(element.attrib["r"]) * scale
            if fill:
                drawing.ellipse((round(center_x - radius), round(center_y - radius), round(center_x + radius), round(center_y + radius)), fill=fill)
            if stroke:
                width = max(1, round(float(root.attrib["stroke-width"]) * scale))
                drawing.ellipse((round(center_x - radius), round(center_y - radius), round(center_x + radius), round(center_y + radius)), outline=stroke, width=width)
        elif tag == "path":
            subpaths = renderer.parse_path(element.attrib["d"])
            fill = parse_color(element.attrib.get("fill"), current_color)
            stroke = parse_color(element.attrib.get("stroke", "currentColor"), current_color)
            if fill:
                for points, _ in subpaths:
                    drawing.polygon(renderer.scaled(points, scale), fill=fill)
            if stroke:
                stroke_width = float(element.attrib.get("stroke-width", root.attrib["stroke-width"]))
                for points, _ in subpaths:
                    renderer.draw_round_stroke(image, points, scale, stroke, stroke_width)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def draw_horizontal_brand(canvas: Image.Image, renderer: Any, x: int, y: int, dark: bool) -> None:
    logo_path = EXPORTS_DIRECTORY / ("logo-symbol-white.svg" if dark else "logo-symbol-primary.svg")
    logo = render_logo(renderer, logo_path)
    paste_at_max(canvas, logo, x, y, 148)
    drawing = ImageDraw.Draw(canvas)
    ink = WHITE_MARK_RGB if dark else INK_RGB
    muted = (203, 213, 225) if dark else MUTED_RGB
    text_top(drawing, x + 176, y + 33, "安枢智梯", font(52, 600), ink)
    text_top(drawing, x + 178, y + 97, "SecureHub", font(27, 500), muted)


def make_preview(renderer: Any) -> None:
    canvas = Image.new("RGBA", (2400, 2180), (*SURFACE_RGB, 255))
    drawing = ImageDraw.Draw(canvas)
    text_top(drawing, 60, 42, "安枢智梯 / SecureHub Brand Assets", font(38, 600), INK_RGB)
    text_top(drawing, 60, 94, "Deterministic GitHub asset review", font(22, 400), MUTED_RGB)

    avatar_image = Image.open(EXPORTS_DIRECTORY / "github-avatar-512.png").convert("RGBA")
    paste_centered(canvas, avatar_image, 60, 142, 270, 270)
    text_top(drawing, 60, 426, "GitHub avatar", font(22, 600), INK_RGB)
    for index, thumbnail_size in enumerate((32, 64, 128)):
        box_x = 360 + index * 170
        drawing.rounded_rectangle((box_x, 150, box_x + 144, 334), radius=8, fill=(*WHITE_RGB, 255), outline=(221, 227, 234, 255), width=2)
        thumbnail = avatar_image.resize((thumbnail_size, thumbnail_size), Image.Resampling.LANCZOS)
        canvas.alpha_composite(thumbnail, (box_x + (144 - thumbnail_size) // 2, 190 + (120 - thumbnail_size) // 2))
        text_top(drawing, box_x + (144 - len(str(thumbnail_size)) * 12) // 2, 348, f"{thumbnail_size} px", font(18, 400), MUTED_RGB)

    social = Image.open(EXPORTS_DIRECTORY / "github-social-preview.png").convert("RGBA").resize((960, 480), Image.Resampling.LANCZOS)
    banner = Image.open(EXPORTS_DIRECTORY / "readme-banner.png").convert("RGBA").resize((1170, 390), Image.Resampling.LANCZOS)
    canvas.alpha_composite(social, (60, 500))
    canvas.alpha_composite(banner, (1110, 500))
    text_top(drawing, 60, 996, "GitHub social preview", font(22, 600), INK_RGB)
    text_top(drawing, 1110, 910, "README banner", font(22, 600), INK_RGB)

    drawing.rounded_rectangle((60, 1050, 1130, 1290), radius=8, fill=(*WHITE_RGB, 255), outline=(221, 227, 234, 255), width=2)
    draw_horizontal_brand(canvas, renderer, 90, 1092, dark=False)
    text_top(drawing, 60, 1310, "Horizontal logo / light", font(22, 600), INK_RGB)

    drawing.rounded_rectangle((1210, 1050, 2280, 1290), radius=8, fill=(*INK_RGB, 255), outline=(*INK_RGB, 255), width=2)
    draw_horizontal_brand(canvas, renderer, 1240, 1092, dark=True)
    text_top(drawing, 1210, 1310, "Horizontal logo / dark", font(22, 600), INK_RGB)

    drawing.rounded_rectangle((60, 1380, 450, 1770), radius=8, fill=(*WHITE_RGB, 255), outline=(221, 227, 234, 255), width=2)
    primary_symbol = render_logo(renderer, EXPORTS_DIRECTORY / "logo-symbol-primary.svg")
    paste_centered(canvas, primary_symbol, 100, 1420, 310, 310)
    text_top(drawing, 60, 1790, "Primary symbol", font(22, 600), INK_RGB)

    drawing.rounded_rectangle((510, 1380, 900, 1770), radius=8, fill=(*INK_RGB, 255), outline=(*INK_RGB, 255), width=2)
    white_symbol = render_logo(renderer, EXPORTS_DIRECTORY / "logo-symbol-white.svg")
    paste_centered(canvas, white_symbol, 550, 1420, 310, 310)
    text_top(drawing, 510, 1790, "White symbol", font(22, 600), INK_RGB)

    text_top(drawing, 1010, 1384, "README icons", font(28, 600), INK_RGB)
    for index, filename in enumerate(ICON_SVGS):
        column = index % 3
        row = index // 3
        tile_x = 1010 + column * 440
        tile_y = 1442 + row * 310
        drawing.rounded_rectangle((tile_x, tile_y, tile_x + 390, tile_y + 260), radius=8, fill=(*WHITE_RGB, 255), outline=(221, 227, 234, 255), width=2)
        icon_path = ICONS_DIRECTORY / filename
        for step, icon_size in enumerate((16, 24, 32)):
            icon = rasterize_icon(renderer, icon_path, icon_size, INK_RGB)
            icon_x = tile_x + 54 + step * 106
            icon_y = tile_y + 54 + (32 - icon_size) // 2
            canvas.alpha_composite(icon, (icon_x, icon_y))
            text_top(drawing, icon_x - 2, tile_y + 110, f"{icon_size}px", font(16, 400), MUTED_RGB)
        text_top(drawing, tile_x + 32, tile_y + 174, filename.removesuffix(".svg"), font(18, 600), TEXT_RGB)

    PREVIEWS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(PREVIEWS_DIRECTORY / "brand-assets-preview.png", format="PNG", optimize=True)


def write_manifest() -> None:
    manifest = {
        "generator": "design/brand/scripts/generate-github-brand-assets.py",
        "formalLogoSvg": str(MASTER_SVG.relative_to(BRAND_ROOT)).replace("\\", "/"),
        "formalLogoPng": str(MASTER_PNG.relative_to(BRAND_ROOT)).replace("\\", "/"),
        "font": {
            "raster": str(FONT_PATH),
            "svgFallback": SVG_FONT_STACK,
            "weights": {"title": 600, "body": 400, "english": 500},
        },
        "immutableBackgrounds": {key: sha256(BRAND_ROOT / key) for key in BACKGROUND_HASHES},
        "colors": {
            "brandInk": BRAND_INK,
            "brandBlue": BRAND_BLUE,
            "brandBlueDarkMode": BRAND_BLUE_DARK_MODE,
            "brandText": BRAND_TEXT,
            "brandMuted": BRAND_MUTED,
            "brandMutedDark": BRAND_MUTED_DARK,
            "brandBorder": BRAND_BORDER,
            "brandSurface": BRAND_SURFACE,
            "brandBackground": BRAND_BACKGROUND,
            "brandWhite": BRAND_WHITE,
        },
        "imagegen": {
            "formalAssets": "not used",
            "reviewOutputDirectory": "tmp/image-gen-review/",
        },
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ensure_inputs()
    for directory in (EXPORTS_DIRECTORY, ICONS_DIRECTORY, PREVIEWS_DIRECTORY):
        directory.mkdir(parents=True, exist_ok=True)
    renderer = load_logo_renderer()

    shutil.copyfile(MASTER_SVG, EXPORTS_DIRECTORY / "logo-symbol-primary.svg")
    write_text(EXPORTS_DIRECTORY / "logo-symbol-white.svg", symbol_svg(BRAND_WHITE, BRAND_BLUE_DARK_MODE))
    write_text(EXPORTS_DIRECTORY / "logo-horizontal-light.svg", horizontal_logo_svg(dark=False))
    write_text(EXPORTS_DIRECTORY / "logo-horizontal-dark.svg", horizontal_logo_svg(dark=True))
    write_text(EXPORTS_DIRECTORY / "readme-banner.svg", readme_banner_svg())
    write_icons()

    avatar(renderer, 512).convert("RGB").save(EXPORTS_DIRECTORY / "github-avatar-512.png", format="PNG", optimize=True)
    avatar(renderer, 1024).convert("RGB").save(EXPORTS_DIRECTORY / "github-avatar-1024.png", format="PNG", optimize=True)
    composite_social(renderer).convert("RGB").save(EXPORTS_DIRECTORY / "github-social-preview.png", format="PNG", optimize=True)
    composite_readme(renderer).convert("RGB").save(EXPORTS_DIRECTORY / "readme-banner.png", format="PNG", optimize=True)
    make_preview(renderer)
    write_manifest()
    print("Generated deterministic SecureHub GitHub brand assets under design/brand.")


if __name__ == "__main__":
    main()
