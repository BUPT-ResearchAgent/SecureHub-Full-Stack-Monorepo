declare function require(moduleName: string): any;
declare const __dirname: string;
declare const process: {
  argv: string[];
  env: Record<string, string | undefined>;
  exitCode?: number;
};

const fs = require("node:fs");
const path = require("node:path");
const childProcess = require("node:child_process");

import { faviconGeometry, primaryGeometry } from "../src/logo-geometry";
import { LogoPalette, renderClearspaceGuideSvg, renderSymbolSvg } from "../src/logo-renderer";

type BrandTokens = {
  primaryColor: string;
  accentColor: string;
  white: string;
  black: string;
  grayscale: {
    ink: string;
    accent: string;
  };
  appIcon: {
    lightBackground: string;
    darkBackground: string;
    darkForeground: string;
  };
  minimumDisplaySize: {
    primarySymbolPx: number;
    faviconPx: number;
  };
};

const brandRoot = path.resolve(__dirname, "../..");
const sourceDirectory = path.join(brandRoot, "src");
const distDirectory = path.join(brandRoot, "dist");
const svgDirectory = path.join(distDirectory, "svg");
const pngDirectory = path.join(distDirectory, "png");
const previewDirectory = path.join(distDirectory, "preview");
const referencePath = path.join(brandRoot, "reference", "anshu-zhiti-logo-source.png");

const tokens = JSON.parse(fs.readFileSync(path.join(sourceDirectory, "brand-tokens.json"), "utf8")) as BrandTokens;

const ensureDirectory = (directory: string): void => {
  fs.mkdirSync(directory, { recursive: true });
};

const writeText = (destination: string, content: string): void => {
  ensureDirectory(path.dirname(destination));
  fs.writeFileSync(destination, content, "utf8");
};

// Equivalent to a conservative SVG optimization pass for generator-owned files.
const optimizeNativeSvg = (svg: string): string => svg
  .replace(/\r\n/g, "\n")
  .replace(/[ \t]+\n/g, "\n")
  .replace(/\n{2,}/g, "\n")
  .trim()
  .concat("\n");

const primaryPalette: LogoPalette = {
  ink: tokens.primaryColor,
  accent: tokens.accentColor
};

const svgExports = [
  {
    filename: "logo-symbol-primary.svg",
    svg: renderSymbolSvg({ geometry: primaryGeometry, palette: primaryPalette })
  },
  {
    filename: "logo-symbol-black.svg",
    svg: renderSymbolSvg({
      geometry: primaryGeometry,
      palette: { ink: tokens.black, accent: tokens.black }
    })
  },
  {
    filename: "logo-symbol-white.svg",
    svg: renderSymbolSvg({
      geometry: primaryGeometry,
      palette: { ink: tokens.white, accent: tokens.white }
    })
  },
  {
    filename: "logo-symbol-grayscale.svg",
    svg: renderSymbolSvg({
      geometry: primaryGeometry,
      palette: { ink: tokens.grayscale.ink, accent: tokens.grayscale.accent }
    })
  },
  {
    filename: "favicon.svg",
    svg: renderSymbolSvg({
      geometry: faviconGeometry,
      palette: primaryPalette,
      simplifiedBook: true
    })
  },
  {
    filename: "app-icon-light.svg",
    svg: renderSymbolSvg({
      geometry: primaryGeometry,
      palette: { ...primaryPalette, background: tokens.appIcon.lightBackground }
    })
  },
  {
    filename: "app-icon-dark.svg",
    svg: renderSymbolSvg({
      geometry: primaryGeometry,
      palette: {
        ink: tokens.appIcon.darkForeground,
        accent: tokens.accentColor,
        background: tokens.appIcon.darkBackground
      }
    })
  }
];

const run = (): void => {
  if (!fs.existsSync(referencePath)) {
    throw new Error(`Reference image is missing: ${referencePath}`);
  }
  ensureDirectory(svgDirectory);
  ensureDirectory(pngDirectory);
  ensureDirectory(previewDirectory);
  fs.rmSync(path.join(previewDirectory, ".render-work"), { recursive: true, force: true });

  for (const asset of svgExports) {
    writeText(path.join(svgDirectory, asset.filename), optimizeNativeSvg(asset.svg));
  }

  const guide = renderClearspaceGuideSvg(
    primaryGeometry,
    primaryPalette,
    primaryGeometry.nodeRadius * 2,
    tokens.minimumDisplaySize.primarySymbolPx
  );
  writeText(path.join(previewDirectory, "logo-clearspace-guide.svg"), optimizeNativeSvg(guide));

  const result = childProcess.spawnSync("python", [
    path.join(brandRoot, "scripts", "render-logo-assets.py"),
    "--brand-root",
    brandRoot
  ], {
    encoding: "utf8",
    timeout: 120000,
    windowsHide: true
  });
  if (result.error || result.status !== 0) {
    const detail = result.error?.message || result.stderr || result.stdout || "unknown SVG rendering failure";
    throw new Error(`Unable to render logo PNG assets: ${detail}`);
  }
  console.log(result.stdout.trim());
  console.log(`Generated ${svgExports.length} SVG exports and 11 raster or review assets in ${distDirectory}.`);
};

run();
