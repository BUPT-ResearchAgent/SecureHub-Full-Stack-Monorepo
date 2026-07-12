declare function require(moduleName: string): any;
declare const __dirname: string;

const fs = require("node:fs");
const path = require("node:path");
const childProcess = require("node:child_process");

type BrandTokens = {
  primaryColor: string;
  accentColor: string;
};

const brandRoot = path.resolve(__dirname, "../..");
const sourceDirectory = path.join(brandRoot, "src");
const svgDirectory = path.join(brandRoot, "dist", "svg");
const pngDirectory = path.join(brandRoot, "dist", "png");
const previewDirectory = path.join(brandRoot, "dist", "preview");
const tokens = JSON.parse(fs.readFileSync(path.join(sourceDirectory, "brand-tokens.json"), "utf8")) as BrandTokens;

const assert: (condition: unknown, message: string) => asserts condition = (condition, message) => {
  if (!condition) {
    throw new Error(message);
  }
};

type PngInspection = {
  path: string;
  width: number;
  height: number;
  has_alpha: boolean;
  alpha_min: number;
  alpha_max: number;
  corner_alpha: number;
  opaque: number;
  dark: number;
  blue: number;
};

const svgFiles = [
  "logo-symbol-primary.svg",
  "logo-symbol-black.svg",
  "logo-symbol-white.svg",
  "logo-symbol-grayscale.svg",
  "favicon.svg",
  "app-icon-light.svg",
  "app-icon-dark.svg"
].map((filename) => path.join(svgDirectory, filename));

const guideSvg = path.join(previewDirectory, "logo-clearspace-guide.svg");
const sizes = [16, 32, 48, 64, 128, 256, 512, 1024];
const pngFiles = sizes.map((size) => ({
  size,
  path: path.join(pngDirectory, `logo-symbol-primary-${size}.png`)
}));

const requiredFiles = [
  ...svgFiles,
  guideSvg,
  ...pngFiles.map((asset) => asset.path),
  path.join(previewDirectory, "logo-comparison.png"),
  path.join(previewDirectory, "logo-size-test.png")
];

const parseXml = (files: string[]): void => {
  const program = [
    "import sys, xml.etree.ElementTree as ET",
    "for filename in sys.argv[1:]:",
    "    ET.parse(filename)",
    "print('XML parse ok:', len(sys.argv) - 1)"
  ].join("\n");
  const result = childProcess.spawnSync("python", ["-c", program, ...files], {
    encoding: "utf8",
    windowsHide: true
  });
  assert(result.status === 0, `XML parse failed: ${result.stderr || result.stdout}`);
};

const validateSvg = (filePath: string): void => {
  const svg = fs.readFileSync(filePath, "utf8");
  assert(/viewBox="0 0 1024 1024"/.test(svg), `${path.basename(filePath)} must use viewBox 0 0 1024 1024.`);
  assert(!/<image\b/i.test(svg), `${path.basename(filePath)} contains a forbidden image element.`);
  assert(!/base64/i.test(svg), `${path.basename(filePath)} contains forbidden base64 data.`);
  assert(!/<filter\b|\bfilter\s*=/i.test(svg), `${path.basename(filePath)} contains a forbidden filter.`);
  assert(!/<script\b|javascript:/i.test(svg), `${path.basename(filePath)} contains forbidden script content.`);
  assert(!/<mask\b|<clipPath\b/i.test(svg), `${path.basename(filePath)} contains a forbidden mask or clipPath.`);
  assert(!/<style\b/i.test(svg), `${path.basename(filePath)} contains a forbidden style block.`);
  assert(!/opacity\s*=|stroke-opacity\s*=|fill-opacity\s*=/i.test(svg), `${path.basename(filePath)} contains forbidden opacity styling.`);
  assert(fs.statSync(filePath).size > 250 && fs.statSync(filePath).size < 30000, `${path.basename(filePath)} has an unreasonable file size.`);
};

const validatePrimaryColors = (): void => {
  const primaryPath = path.join(svgDirectory, "logo-symbol-primary.svg");
  const svg = fs.readFileSync(primaryPath, "utf8");
  const matchedColors = (svg.match(/#[0-9A-Fa-f]{6}\b/g) || []) as string[];
  const usedColors: string[] = [...new Set(matchedColors.map((value) => value.toUpperCase()))];
  const approved = new Set([tokens.primaryColor.toUpperCase(), tokens.accentColor.toUpperCase()]);
  assert(usedColors.length === 2, "Primary mark must use exactly the two production brand colors.");
  assert(usedColors.every((color) => approved.has(color)), `Primary mark uses a non-token color: ${usedColors.join(", ")}`);
};

const inspectPngs = (files: string[]): PngInspection[] => {
  const program = [
    "from PIL import Image",
    "import json, sys",
    "for filename in sys.argv[1:] :",
    "    original = Image.open(filename)",
    "    has_alpha = 'A' in original.getbands()",
    "    image = original.convert('RGBA')",
    "    alpha = image.getchannel('A')",
    "    pixels = list(image.getdata())",
    "    opaque = sum(1 for r,g,b,a in pixels if a > 0)",
    "    dark = sum(1 for r,g,b,a in pixels if a > 96 and r < 60 and g < 85 and b < 110)",
    "    blue = sum(1 for r,g,b,a in pixels if a > 96 and b > r * 1.12 and b > g * 1.05)",
    "    result = {'path': filename, 'width': image.width, 'height': image.height, 'has_alpha': has_alpha, 'alpha_min': alpha.getextrema()[0], 'alpha_max': alpha.getextrema()[1], 'corner_alpha': alpha.getpixel((0, 0)), 'opaque': opaque, 'dark': dark, 'blue': blue}",
    "    print(json.dumps(result))"
  ].join("\n");
  const result = childProcess.spawnSync("python", ["-c", program, ...files], {
    encoding: "utf8",
    windowsHide: true
  });
  assert(result.status === 0, `PNG inspection failed: ${result.stderr || result.stdout}`);
  return result.stdout.trim().split(/\r?\n/).filter(Boolean).map((line: string) => JSON.parse(line) as PngInspection);
};

const run = (): void => {
  for (const filePath of requiredFiles) {
    assert(fs.existsSync(filePath), `Expected output is missing: ${filePath}`);
  }

  parseXml([...svgFiles, guideSvg]);
  for (const filePath of [...svgFiles, guideSvg]) {
    validateSvg(filePath);
  }
  validatePrimaryColors();

  const pngInspections = inspectPngs(pngFiles.map((asset) => asset.path));
  for (const asset of pngFiles) {
    const inspection = pngInspections.find((item) => item.path === asset.path);
    assert(inspection, `No PNG inspection result for ${asset.path}`);
    assert(inspection.width === asset.size && inspection.height === asset.size, `${path.basename(asset.path)} dimensions do not match its filename.`);
    assert(inspection.has_alpha, `${path.basename(asset.path)} has no alpha channel.`);
    assert(inspection.alpha_min === 0 && inspection.alpha_max > 0 && inspection.corner_alpha === 0, `${path.basename(asset.path)} is not a transparent PNG with transparent corners.`);
    const byteLength = fs.statSync(asset.path).size;
    assert(byteLength > 100 && byteLength < 1600000, `${path.basename(asset.path)} has an unreasonable file size.`);
  }

  const icon16 = pngInspections.find((item) => item.width === 16);
  assert(icon16, "16px PNG inspection is missing.");
  assert(Number(icon16.opaque) >= 20 && Number(icon16.dark) >= 12 && Number(icon16.blue) >= 1, "16px icon lost a required visual signal (dark geometry or blue spark).");

  console.log(`Validated ${svgFiles.length + 1} SVG files, ${pngFiles.length} transparent PNG files, and 2 preview PNG files.`);
  console.log(`16px signal check: opaque=${icon16.opaque}, dark=${icon16.dark}, blue=${icon16.blue}.`);
};

run();
