#!/usr/bin/env python3
"""Validate deterministic GitHub-facing SecureHub brand assets."""

from __future__ import annotations

import hashlib
import importlib.util
import re
import xml.etree.ElementTree as element_tree
from pathlib import Path

from PIL import Image


BRAND_ROOT = Path(__file__).resolve().parents[1]
MASTER_SVG = BRAND_ROOT / "master" / "logo-symbol-primary.svg"
MASTER_PNG = BRAND_ROOT / "master" / "logo-symbol-primary-1024.png"
EXPORTS = BRAND_ROOT / "exports"
ICONS = BRAND_ROOT / "icons"
PREVIEW = BRAND_ROOT / "previews" / "brand-assets-preview.png"

BACKGROUND_HASHES = {
    "generated/github-social-background.png": "A88CF5EF350EBEC3C940526DC74B95163982559E521E311EE152C205254E5CBD",
    "generated/readme-banner-background.png": "551D7774FD00F74E36E5E08B6344E4ADB2EE9BFFDEC925EBBA2FFA5C12CECC4C",
    "archive/github-social-background-concept-a.png": "01E7B3101EDDC053AD260285E152464C66625E69E7C504AE42F3944198310C49",
}
ICON_NAMES = (
    "knowledge-base.svg",
    "learning-path.svg",
    "security-lab.svg",
    "agent-collaboration.svg",
    "research.svg",
    "talent-development.svg",
)
LOGO_NAMES = (
    "logo-symbol-primary.svg",
    "logo-symbol-white.svg",
    "logo-horizontal-light.svg",
    "logo-horizontal-dark.svg",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def image_info(path: Path) -> tuple[int, int, str]:
    with Image.open(path) as image:
        return image.width, image.height, image.mode


def svg_text(path: Path) -> str:
    element_tree.parse(path)
    return path.read_text(encoding="utf-8")


def assert_svg_safe(path: Path, allow_image: bool = False) -> str:
    content = svg_text(path)
    lowered = content.lower()
    require("base64" not in lowered, f"{path.name} contains base64.")
    require("<script" not in lowered and "javascript:" not in lowered, f"{path.name} contains script content.")
    require("<filter" not in lowered and "filter=" not in lowered, f"{path.name} contains a filter.")
    if not allow_image:
        require("<image" not in lowered, f"{path.name} contains an image element.")
    return content


def logo_geometry(content: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    paths = tuple(re.findall(r'<path[^>]*\bd="([^"]+)"', content))
    circles = tuple(re.findall(r'<circle[^>]*\bcx="([^"]+)"[^>]*\bcy="([^"]+)"[^>]*\br="([^"]+)"', content))
    return paths, circles


def load_generator() -> object:
    script = BRAND_ROOT / "scripts" / "generate-github-brand-assets.py"
    spec = importlib.util.spec_from_file_location("securehub_github_brand_generator", script)
    if not spec or not spec.loader:
        raise RuntimeError("Cannot load GitHub brand generator.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    expected_files = [
        MASTER_SVG,
        MASTER_PNG,
        EXPORTS / "github-avatar-512.png",
        EXPORTS / "github-avatar-1024.png",
        EXPORTS / "github-social-preview.png",
        EXPORTS / "readme-banner.svg",
        EXPORTS / "readme-banner.png",
        *[EXPORTS / name for name in LOGO_NAMES],
        *[ICONS / name for name in ICON_NAMES],
        PREVIEW,
    ]
    for path in expected_files:
        require(path.exists(), f"Missing required asset: {path.relative_to(BRAND_ROOT)}")

    for relative_path, expected_hash in BACKGROUND_HASHES.items():
        require(sha256(BRAND_ROOT / relative_path) == expected_hash, f"Immutable background changed: {relative_path}")

    require(image_info(EXPORTS / "github-avatar-512.png")[:2] == (512, 512), "github-avatar-512.png is not 512x512.")
    require(image_info(EXPORTS / "github-avatar-1024.png")[:2] == (1024, 1024), "github-avatar-1024.png is not 1024x1024.")
    require(image_info(EXPORTS / "github-social-preview.png")[:2] == (1280, 640), "github-social-preview.png is not 1280x640.")
    require((EXPORTS / "github-social-preview.png").stat().st_size < 1_000_000, "github-social-preview.png must be below 1 MB.")
    require(image_info(EXPORTS / "readme-banner.png")[:2] == (1440, 480), "readme-banner.png is not 1440x480.")
    require(image_info(PREVIEW)[:2] == (2400, 2180), "brand-assets-preview.png dimensions are incorrect.")
    with Image.open(EXPORTS / "github-avatar-512.png") as image:
        require(image.getpixel((0, 0))[:3] == (246, 248, 251), "Avatar background is not #F6F8FB.")

    master_content = assert_svg_safe(MASTER_SVG)
    primary_content = assert_svg_safe(EXPORTS / "logo-symbol-primary.svg")
    white_content = assert_svg_safe(EXPORTS / "logo-symbol-white.svg")
    require(primary_content == master_content, "Primary export must match the formal SVG master byte-for-byte.")
    require(logo_geometry(master_content) == logo_geometry(white_content), "White logo export changed the formal logo geometry.")
    require("#F8FAFC" in white_content and "#4D73FF" in white_content, "White logo colors are incorrect.")

    for name in ("logo-horizontal-light.svg", "logo-horizontal-dark.svg"):
        content = assert_svg_safe(EXPORTS / name)
        paths, _ = logo_geometry(content)
        for master_path in logo_geometry(master_content)[0]:
            require(master_path in paths, f"{name} does not inline the official logo geometry.")
    dark_horizontal = (EXPORTS / "logo-horizontal-dark.svg").read_text(encoding="utf-8")
    require("#F8FAFC" in dark_horizontal and "#4D73FF" in dark_horizontal and "#CBD5E1" in dark_horizontal, "Dark horizontal logo colors are incorrect.")

    banner_content = assert_svg_safe(EXPORTS / "readme-banner.svg", allow_image=True)
    require('viewBox="0 0 1440 480"' in banner_content, "readme-banner.svg viewBox is incorrect.")
    require(banner_content.lower().count("<image") == 1, "readme-banner.svg may contain exactly one image element.")
    require('href="../generated/readme-banner-background.png"' in banner_content, "readme-banner.svg must use the expected relative background path.")

    generator = load_generator()
    renderer = generator.load_logo_renderer()
    for name in ICON_NAMES:
        content = assert_svg_safe(ICONS / name)
        require('viewBox="0 0 24 24"' in content, f"{name} viewBox is incorrect.")
        require('width="24"' in content and 'height="24"' in content, f"{name} size attributes are incorrect.")
        require('stroke="currentColor"' in content and 'stroke-width="1.75"' in content, f"{name} stroke tokens are incorrect.")
        require('color="#174BFF"' in content, f"{name} must set the standalone brand-blue color for theme-safe image embedding.")
        icon = generator.rasterize_icon(renderer, ICONS / name, 16, (11, 27, 45))
        require(icon.getchannel("A").getbbox() is not None, f"{name} is not recognizable at 16px.")

    forbidden_fonts = [path for path in BRAND_ROOT.rglob("*") if path.is_file() and path.suffix.lower() in {".ttf", ".otf", ".woff", ".woff2"}]
    require(not forbidden_fonts, "No font files may be committed beneath design/brand.")
    print("Validated GitHub brand assets: files, dimensions, hashes, SVG safety, logo geometry, icon recognizability, and font policy all pass.")
    print(f"GitHub social preview size: {(EXPORTS / 'github-social-preview.png').stat().st_size} bytes.")


if __name__ == "__main__":
    main()
