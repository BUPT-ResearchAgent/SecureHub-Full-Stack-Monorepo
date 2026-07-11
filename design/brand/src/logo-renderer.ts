import { LogoGeometry, Point } from "./logo-geometry";

export type LogoPalette = {
  ink: string;
  accent: string;
  background?: string;
};

export type SymbolOptions = {
  geometry: LogoGeometry;
  palette: LogoPalette;
  simplifiedBook?: boolean;
};

const number = (value: number): string => {
  const rounded = Math.round(value * 100) / 100;
  return Number.isInteger(rounded) ? String(rounded) : String(rounded);
};

const point = ({ x, y }: Point): string => `${number(x)} ${number(y)}`;

const polar = (center: Point, radius: number, degrees: number): Point => {
  const radians = (degrees * Math.PI) / 180;
  return {
    x: center.x + radius * Math.cos(radians),
    y: center.y + radius * Math.sin(radians)
  };
};

const ringPath = (geometry: LogoGeometry): string => {
  const start = polar(geometry.ringCenter, geometry.ringRadius, geometry.ringStartAngle);
  const end = polar(geometry.ringCenter, geometry.ringRadius, geometry.ringEndAngle);
  const angle = Math.abs(geometry.ringEndAngle - geometry.ringStartAngle) % 360;
  const largeArc = angle > 180 ? 1 : 0;
  const sweep = geometry.ringEndAngle >= geometry.ringStartAngle ? 1 : 0;
  return `M ${point(start)} A ${number(geometry.ringRadius)} ${number(geometry.ringRadius)} 0 ${largeArc} ${sweep} ${point(end)}`;
};

const stairPath = (geometry: LogoGeometry): string => {
  const { x, y } = geometry.stairOrigin;
  const y0 = y - geometry.stairInitialRise;
  const y1 = y0 - geometry.stairStepHeight;
  const y2 = y1 - geometry.stairStepHeight;
  const y3 = y2 - geometry.stairStepHeight;
  const x1 = x + geometry.stairStepWidth;
  const x2 = x1 + geometry.stairStepWidth;
  const x3 = x2 + geometry.stairStepWidth;
  return `M ${number(x)} ${number(y)} V ${number(y0)} H ${number(x1)} V ${number(y1)} H ${number(x2)} V ${number(y2)} H ${number(x3)} V ${number(y3)}`;
};

const bookPaths = (geometry: LogoGeometry, simplified: boolean): { upper: string; lower?: string } => {
  const upperY = geometry.bookCenter.y - geometry.bookHeight / 2;
  const lowerY = upperY + geometry.bookPageGap;
  const upperSpineY = geometry.bookCenter.y + geometry.bookSpineUpperOffset;
  const lowerSpineY = geometry.bookCenter.y + geometry.bookHeight / 2;
  const lowerHalfWidth = geometry.bookWidth / 2;
  const upperHalfWidth = lowerHalfWidth - geometry.bookUpperInset;

  const upperLeft = { x: geometry.bookCenter.x - upperHalfWidth, y: upperY };
  const upperRight = { x: geometry.bookCenter.x + upperHalfWidth, y: upperY };
  const upperSpine = { x: geometry.bookCenter.x, y: upperSpineY };
  const upper = [
    `M ${point(upperLeft)}`,
    `C ${number(upperLeft.x + upperHalfWidth * 0.45)} ${number(upperY)} ${number(upperSpine.x - upperHalfWidth * 0.24)} ${number(upperY + (upperSpineY - upperY) * 0.2)} ${point(upperSpine)}`,
    `C ${number(upperSpine.x + upperHalfWidth * 0.24)} ${number(upperY + (upperSpineY - upperY) * 0.2)} ${number(upperRight.x - upperHalfWidth * 0.45)} ${number(upperY)} ${point(upperRight)}`
  ].join(" ");

  if (simplified) {
    return { upper };
  }

  const lowerLeft = { x: geometry.bookCenter.x - lowerHalfWidth, y: lowerY };
  const lowerRight = { x: geometry.bookCenter.x + lowerHalfWidth, y: lowerY };
  const lowerSpine = { x: geometry.bookCenter.x, y: lowerSpineY };
  const lower = [
    `M ${point(lowerLeft)}`,
    `C ${number(lowerLeft.x + lowerHalfWidth * 0.45)} ${number(lowerY)} ${number(lowerSpine.x - lowerHalfWidth * 0.25)} ${number(lowerY + (lowerSpineY - lowerY) * 0.25)} ${point(lowerSpine)}`,
    `C ${number(lowerSpine.x + lowerHalfWidth * 0.25)} ${number(lowerY + (lowerSpineY - lowerY) * 0.25)} ${number(lowerRight.x - lowerHalfWidth * 0.45)} ${number(lowerY)} ${point(lowerRight)}`
  ].join(" ");
  return { upper, lower };
};

const sparkPath = (geometry: LogoGeometry): string => {
  const { x, y } = geometry.sparkCenter;
  const halfWidth = geometry.sparkWidth / 2;
  const halfHeight = geometry.sparkHeight / 2;
  const verticalControl = halfHeight * 0.48;
  const horizontalControl = halfWidth * 0.46;
  return [
    `M ${number(x)} ${number(y - halfHeight)}`,
    `C ${number(x + horizontalControl * 0.28)} ${number(y - verticalControl)} ${number(x + horizontalControl)} ${number(y - halfHeight * 0.16)} ${number(x + halfWidth)} ${number(y)}`,
    `C ${number(x + horizontalControl)} ${number(y + halfHeight * 0.16)} ${number(x + horizontalControl * 0.28)} ${number(y + verticalControl)} ${number(x)} ${number(y + halfHeight)}`,
    `C ${number(x - horizontalControl * 0.28)} ${number(y + verticalControl)} ${number(x - horizontalControl)} ${number(y + halfHeight * 0.16)} ${number(x - halfWidth)} ${number(y)}`,
    `C ${number(x - horizontalControl)} ${number(y - halfHeight * 0.16)} ${number(x - horizontalControl * 0.28)} ${number(y - verticalControl)} ${number(x)} ${number(y - halfHeight)}`,
    "Z"
  ].join(" ");
};

export const renderSymbolSvg = ({ geometry, palette, simplifiedBook = false }: SymbolOptions): string => {
  const book = bookPaths(geometry, simplifiedBook);
  const background = palette.background
    ? `  <rect id="background" width="${number(geometry.canvasSize)}" height="${number(geometry.canvasSize)}" fill="${palette.background}" />\n`
    : "";
  const lowerBook = book.lower
    ? `\n  <path id="book-lower" d="${book.lower}" fill="none" stroke="${palette.ink}" stroke-width="${number(geometry.bookStrokeWidth)}" stroke-linecap="round" stroke-linejoin="round" />`
    : "";

  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${number(geometry.canvasSize)} ${number(geometry.canvasSize)}" preserveAspectRatio="xMidYMid meet">`,
    background.trimEnd(),
    `  <path id="ring" d="${ringPath(geometry)}" fill="none" stroke="${palette.ink}" stroke-width="${number(geometry.ringStrokeWidth)}" stroke-linecap="round" />`,
    `  <circle id="node" cx="${number(geometry.nodeCenter.x)}" cy="${number(geometry.nodeCenter.y)}" r="${number(geometry.nodeRadius)}" fill="${palette.ink}" />`,
    `  <path id="stair" d="${stairPath(geometry)}" fill="none" stroke="${palette.ink}" stroke-width="${number(geometry.stairStrokeWidth)}" stroke-linecap="round" stroke-linejoin="round" />`,
    `  <path id="book-upper" d="${book.upper}" fill="none" stroke="${palette.ink}" stroke-width="${number(geometry.bookStrokeWidth)}" stroke-linecap="round" stroke-linejoin="round" />${lowerBook}`,
    `  <path id="spark" d="${sparkPath(geometry)}" fill="${palette.accent}" />`,
    "</svg>",
    ""
  ].filter((line) => line.length > 0).join("\n");
};

export const renderClearspaceGuideSvg = (geometry: LogoGeometry, palette: LogoPalette, nodeDiameter: number, minimumSize: number): string => {
  const guideScale = 0.57;
  const translateX = 95;
  const translateY = 95;
  const symbolSize = geometry.canvasSize * guideScale;
  const clearspace = nodeDiameter * guideScale;
  const frameX = translateX - clearspace;
  const frameY = translateY - clearspace;
  const frameSize = symbolSize + clearspace * 2;
  const mark = renderSymbolSvg({ geometry, palette });
  const markContents = mark
    .replace(/^<svg[^>]*>\n?/, "")
    .replace(/<\/svg>\n?$/, "")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join("\n    ");

  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">`,
    `  <rect id="guide-background" width="1024" height="1024" fill="#FFFFFF" />`,
    `  <rect id="clearspace-frame" x="${number(frameX)}" y="${number(frameY)}" width="${number(frameSize)}" height="${number(frameSize)}" fill="none" stroke="#7B8794" stroke-width="2" stroke-dasharray="10 8" />`,
    `  <g id="symbol-safe-area" transform="translate(${number(translateX)} ${number(translateY)}) scale(${number(guideScale)})">`,
    `    ${markContents}`,
    "  </g>",
    `  <path id="clearspace-measure" d="M ${number(frameX)} 746 H ${number(frameX + clearspace)} M ${number(frameX)} 732 V 760 M ${number(frameX + clearspace)} 732 V 760" fill="none" stroke="#52606D" stroke-width="2" />`,
    `  <text x="${number(frameX)}" y="790" fill="#263746" font-family="Arial, sans-serif" font-size="28">CLEAR SPACE = 1N</text>`,
    `  <text x="${number(frameX)}" y="826" fill="#52606D" font-family="Arial, sans-serif" font-size="22">N = NODE DIAMETER</text>`,
    `  <text x="${number(frameX)}" y="880" fill="#263746" font-family="Arial, sans-serif" font-size="28">PRIMARY MARK: MIN ${number(minimumSize)} PX</text>`,
    `  <text x="${number(frameX)}" y="918" fill="#52606D" font-family="Arial, sans-serif" font-size="22">FAVICON: MIN 16 PX</text>`,
    "</svg>",
    ""
  ].join("\n");
};
