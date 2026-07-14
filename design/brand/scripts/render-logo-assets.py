#!/usr/bin/env python3
"""Render the generated native SVG subset with Pillow for deterministic PNG exports.

The renderer intentionally supports only the SVG primitives emitted by
logo-renderer.ts: rect, circle, and path commands M/A/H/V/C/Z. It reads the
written SVG exports instead of the source PNG, so raster assets remain tied to
the same native geometry as the production masters.
"""

from __future__ import annotations

import argparse
import math
import re
import xml.etree.ElementTree as element_tree
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


Point = tuple[float, float]
Subpath = tuple[list[Point], bool]
COMMAND_PATTERN = re.compile(r"[AaCcHhLlMmVvZz]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")


def color(value: str | None) -> tuple[int, int, int, int] | None:
    if value is None or value.lower() == "none":
        return None
    if value.startswith("#") and len(value) == 7:
        return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5)) + (255,)
    raise ValueError(f"Unsupported flat color: {value}")


def local_name(element: element_tree.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def distance(first: Point, second: Point) -> float:
    return math.hypot(second[0] - first[0], second[1] - first[1])


def vector_angle(first: Point, second: Point) -> float:
    dot = first[0] * second[0] + first[1] * second[1]
    determinant = first[0] * second[1] - first[1] * second[0]
    return math.atan2(determinant, dot)


def cubic_points(start: Point, first_control: Point, second_control: Point, end: Point) -> list[Point]:
    estimated_length = distance(start, first_control) + distance(first_control, second_control) + distance(second_control, end)
    steps = max(12, math.ceil(estimated_length / 5))
    points: list[Point] = []
    for index in range(1, steps + 1):
        t = index / steps
        inverse = 1 - t
        x = inverse**3 * start[0] + 3 * inverse**2 * t * first_control[0] + 3 * inverse * t**2 * second_control[0] + t**3 * end[0]
        y = inverse**3 * start[1] + 3 * inverse**2 * t * first_control[1] + 3 * inverse * t**2 * second_control[1] + t**3 * end[1]
        points.append((x, y))
    return points


def arc_points(start: Point, radius_x: float, radius_y: float, rotation_degrees: float, large_arc: int, sweep: int, end: Point) -> list[Point]:
    if radius_x == 0 or radius_y == 0 or start == end:
        return [end]

    radius_x = abs(radius_x)
    radius_y = abs(radius_y)
    rotation = math.radians(rotation_degrees % 360)
    cosine = math.cos(rotation)
    sine = math.sin(rotation)
    delta_x = (start[0] - end[0]) / 2
    delta_y = (start[1] - end[1]) / 2
    start_x = cosine * delta_x + sine * delta_y
    start_y = -sine * delta_x + cosine * delta_y
    radius_scale = start_x**2 / radius_x**2 + start_y**2 / radius_y**2
    if radius_scale > 1:
        scale = math.sqrt(radius_scale)
        radius_x *= scale
        radius_y *= scale

    numerator = radius_x**2 * radius_y**2 - radius_x**2 * start_y**2 - radius_y**2 * start_x**2
    denominator = radius_x**2 * start_y**2 + radius_y**2 * start_x**2
    coefficient = 0.0 if denominator == 0 else math.sqrt(max(0.0, numerator / denominator))
    if large_arc == sweep:
        coefficient = -coefficient
    center_x = coefficient * (radius_x * start_y / radius_y)
    center_y = coefficient * (-radius_y * start_x / radius_x)
    midpoint_x = (start[0] + end[0]) / 2
    midpoint_y = (start[1] + end[1]) / 2
    center = (
        cosine * center_x - sine * center_y + midpoint_x,
        sine * center_x + cosine * center_y + midpoint_y,
    )

    start_vector = ((start_x - center_x) / radius_x, (start_y - center_y) / radius_y)
    end_vector = ((-start_x - center_x) / radius_x, (-start_y - center_y) / radius_y)
    start_angle = vector_angle((1.0, 0.0), start_vector)
    sweep_angle = vector_angle(start_vector, end_vector)
    if not sweep and sweep_angle > 0:
        sweep_angle -= math.tau
    if sweep and sweep_angle < 0:
        sweep_angle += math.tau
    steps = max(24, math.ceil(abs(sweep_angle) * max(radius_x, radius_y) / 1.75))

    points: list[Point] = []
    for index in range(1, steps + 1):
        theta = start_angle + sweep_angle * index / steps
        local_x = radius_x * math.cos(theta)
        local_y = radius_y * math.sin(theta)
        points.append((
            cosine * local_x - sine * local_y + center[0],
            sine * local_x + cosine * local_y + center[1],
        ))
    return points


def parse_path(data: str) -> list[Subpath]:
    tokens = COMMAND_PATTERN.findall(data)
    index = 0
    command = ""
    current: Point = (0.0, 0.0)
    start: Point = (0.0, 0.0)
    points: list[Point] = []
    closed = False
    subpaths: list[Subpath] = []

    def read_numbers(count: int) -> list[float]:
        nonlocal index
        if index + count > len(tokens):
            raise ValueError(f"Malformed SVG path: {data}")
        values = [float(token) for token in tokens[index : index + count]]
        index += count
        return values

    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
        if not command:
            raise ValueError(f"Missing SVG path command: {data}")
        if command == "M":
            if points:
                subpaths.append((points, closed))
            x, y = read_numbers(2)
            current = (x, y)
            start = current
            points = [current]
            closed = False
        elif command == "L":
            x, y = read_numbers(2)
            current = (x, y)
            points.append(current)
        elif command == "H":
            x = read_numbers(1)[0]
            current = (x, current[1])
            points.append(current)
        elif command == "V":
            y = read_numbers(1)[0]
            current = (current[0], y)
            points.append(current)
        elif command == "C":
            c1x, c1y, c2x, c2y, x, y = read_numbers(6)
            end = (x, y)
            points.extend(cubic_points(current, (c1x, c1y), (c2x, c2y), end))
            current = end
        elif command == "A":
            radius_x, radius_y, rotation, large_arc, sweep, x, y = read_numbers(7)
            end = (x, y)
            points.extend(arc_points(current, radius_x, radius_y, rotation, int(large_arc), int(sweep), end))
            current = end
        elif command in ("Z", "z"):
            if points and points[-1] != start:
                points.append(start)
            current = start
            closed = True
            command = ""
        else:
            raise ValueError(f"Unsupported SVG path command {command}")

    if points:
        subpaths.append((points, closed))
    return subpaths


def scaled(points: Iterable[Point], scale: float) -> list[tuple[int, int]]:
    return [(round(x * scale), round(y * scale)) for x, y in points]


def draw_round_stroke(image: Image.Image, points: list[Point], scale: float, paint: tuple[int, int, int, int], stroke_width: float) -> None:
    if len(points) < 2:
        return
    drawing = ImageDraw.Draw(image)
    scaled_points = scaled(points, scale)
    width = max(1, round(stroke_width * scale))
    drawing.line(scaled_points, fill=paint, width=width, joint="curve")
    radius = width / 2
    for x, y in scaled_points:
        drawing.ellipse((round(x - radius), round(y - radius), round(x + radius), round(y + radius)), fill=paint)


def render_svg(svg_path: Path, pixel_size: int, antialias: int = 4) -> Image.Image:
    root = element_tree.parse(svg_path).getroot()
    view_box = [float(value) for value in root.attrib["viewBox"].split()]
    if view_box != [0.0, 0.0, 1024.0, 1024.0]:
        raise ValueError(f"Unexpected viewBox in {svg_path}: {root.attrib['viewBox']}")
    scale = pixel_size * antialias / view_box[2]
    image = Image.new("RGBA", (pixel_size * antialias, pixel_size * antialias), (0, 0, 0, 0))
    drawing = ImageDraw.Draw(image)

    for element in root.iter():
        tag = local_name(element)
        if tag == "rect":
            paint = color(element.attrib.get("fill"))
            if paint:
                x = float(element.attrib.get("x", "0")) * scale
                y = float(element.attrib.get("y", "0")) * scale
                width = float(element.attrib["width"]) * scale
                height = float(element.attrib["height"]) * scale
                drawing.rectangle((round(x), round(y), round(x + width), round(y + height)), fill=paint)
        elif tag == "circle":
            paint = color(element.attrib.get("fill"))
            if paint:
                center_x = float(element.attrib["cx"]) * scale
                center_y = float(element.attrib["cy"]) * scale
                radius = float(element.attrib["r"]) * scale
                drawing.ellipse((round(center_x - radius), round(center_y - radius), round(center_x + radius), round(center_y + radius)), fill=paint)
        elif tag == "path":
            subpaths = parse_path(element.attrib["d"])
            fill = color(element.attrib.get("fill"))
            stroke = color(element.attrib.get("stroke"))
            if fill:
                for points, _ in subpaths:
                    if len(points) >= 3:
                        drawing.polygon(scaled(points, scale), fill=fill)
            if stroke:
                stroke_width = float(element.attrib.get("stroke-width", "1"))
                for points, _ in subpaths:
                    draw_round_stroke(image, points, scale, stroke, stroke_width)
    return image.resize((pixel_size, pixel_size), Image.Resampling.LANCZOS)


def save_symbol_png(svg_path: Path, output_path: Path, size: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    render_svg(svg_path, size).save(output_path, format="PNG", optimize=True)


def load_font(size: int) -> ImageFont.ImageFont:
    for font_path in (Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/arial.ttf")):
        if font_path.exists():
            return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default()


def center_paste(canvas: Image.Image, asset: Image.Image, bounds: tuple[int, int, int, int]) -> None:
    left, top, width, height = bounds
    image = asset.copy()
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    target = (left + (width - image.width) // 2, top + (height - image.height) // 2)
    canvas.alpha_composite(image, target)


def render_comparison(reference: Path, primary_svg: Path, black_svg: Path, output: Path) -> None:
    canvas = Image.new("RGBA", (1800, 760), (238, 242, 247, 255))
    drawing = ImageDraw.Draw(canvas)
    heading_font = load_font(30)
    label_font = load_font(20)
    drawing.text((48, 38), "Anshu Zhiti logo reconstruction review", fill=(11, 27, 45, 255), font=heading_font)
    labels = ("Source reference", "Vector master", "Pure black")
    assets = (
        Image.open(reference).convert("RGBA"),
        render_svg(primary_svg, 500),
        render_svg(black_svg, 500),
    )
    panel_width = 549
    panel_top = 102
    for index, (label, asset) in enumerate(zip(labels, assets)):
        left = 48 + index * (panel_width + 28)
        drawing.rectangle((left, panel_top, left + panel_width, 730), fill=(255, 255, 255, 255), outline=(215, 222, 232, 255), width=2)
        label_box = drawing.textbbox((0, 0), label, font=label_font)
        label_x = left + (panel_width - (label_box[2] - label_box[0])) // 2
        drawing.text((label_x, 126), label, fill=(11, 27, 45, 255), font=label_font)
        center_paste(canvas, asset, (left + 24, 165, panel_width - 48, 525))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, format="PNG", optimize=True)


def render_size_test(primary_svg: Path, white_svg: Path, output: Path) -> None:
    canvas = Image.new("RGBA", (1800, 1024), (255, 255, 255, 255))
    drawing = ImageDraw.Draw(canvas)
    drawing.rectangle((0, 512, 1800, 1024), fill=(11, 27, 45, 255))
    title_font = load_font(28)
    label_font = load_font(20)
    drawing.text((48, 36), "Primary mark on light background", fill=(11, 27, 45, 255), font=title_font)
    drawing.text((48, 548), "White mark on dark background", fill=(255, 255, 255, 255), font=title_font)
    sizes = (16, 24, 32, 48, 64, 128, 256)
    positions = (150, 395, 640, 885, 1130, 1375, 1620)
    for offset, svg_path, foreground, outline in (
        (0, primary_svg, (11, 27, 45, 255), (123, 135, 148, 150)),
        (512, white_svg, (255, 255, 255, 255), (255, 255, 255, 90)),
    ):
        for position, size in zip(positions, sizes):
            box_size = max(size + 54, 94)
            left = position - box_size // 2
            top = offset + 205 + (130 - box_size) // 2
            drawing.rectangle((left, top, left + box_size, top + box_size), outline=outline, width=1)
            center_paste(canvas, render_svg(svg_path, size), (left, top, box_size, box_size))
            label = f"{size} px"
            label_box = drawing.textbbox((0, 0), label, font=label_font)
            drawing.text((position - (label_box[2] - label_box[0]) // 2, offset + 396), label, fill=foreground, font=label_font)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand-root", required=True, type=Path)
    arguments = parser.parse_args()
    brand_root = arguments.brand_root.resolve()
    svg_directory = brand_root / "dist" / "svg"
    png_directory = brand_root / "dist" / "png"
    preview_directory = brand_root / "dist" / "preview"
    reference = brand_root / "reference" / "anshu-zhiti-logo-source.png"
    primary_svg = svg_directory / "logo-symbol-primary.svg"
    black_svg = svg_directory / "logo-symbol-black.svg"
    white_svg = svg_directory / "logo-symbol-white.svg"

    for required in (reference, primary_svg, black_svg, white_svg):
        if not required.exists():
            raise FileNotFoundError(f"Required logo input is missing: {required}")

    for size in (16, 32, 48, 64, 128, 256, 512, 1024):
        save_symbol_png(primary_svg, png_directory / f"logo-symbol-primary-{size}.png", size)
    render_comparison(reference, primary_svg, black_svg, preview_directory / "logo-comparison.png")
    render_size_test(primary_svg, white_svg, preview_directory / "logo-size-test.png")
    print("Rendered 8 transparent symbol PNGs and 2 review PNGs from native SVG exports.")


if __name__ == "__main__":
    main()
