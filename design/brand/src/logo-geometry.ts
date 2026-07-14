export type Point = {
  x: number;
  y: number;
};

export type LogoGeometry = {
  canvasSize: number;
  safeArea: {
    inset: number;
  };
  ringCenter: Point;
  ringRadius: number;
  ringStrokeWidth: number;
  ringStartAngle: number;
  ringEndAngle: number;
  nodeCenter: Point;
  nodeRadius: number;
  stairOrigin: Point;
  stairStepWidth: number;
  stairStepHeight: number;
  stairStrokeWidth: number;
  stairCornerRadius: number;
  stairInitialRise: number;
  stairLevelCount: number;
  bookCenter: Point;
  bookWidth: number;
  bookHeight: number;
  bookPageGap: number;
  bookStrokeWidth: number;
  bookUpperInset: number;
  bookSpineUpperOffset: number;
  sparkCenter: Point;
  sparkWidth: number;
  sparkHeight: number;
};

/**
 * All production coordinates are expressed against a 1024 square canvas.
 * Four vertical rises with three equal treads match the reference staircase.
 */
export const primaryGeometry: LogoGeometry = {
  canvasSize: 1024,
  safeArea: {
    inset: 176
  },
  ringCenter: { x: 512, y: 494 },
  ringRadius: 276,
  ringStrokeWidth: 26,
  ringStartAngle: 138,
  ringEndAngle: 437,
  nodeCenter: { x: 342, y: 720 },
  nodeRadius: 32,
  stairOrigin: { x: 410, y: 586 },
  stairStepWidth: 66,
  stairStepHeight: 42,
  stairStrokeWidth: 26,
  stairCornerRadius: 13,
  stairInitialRise: 28,
  stairLevelCount: 4,
  bookCenter: { x: 512, y: 666 },
  bookWidth: 244,
  bookHeight: 96,
  bookPageGap: 54,
  bookStrokeWidth: 26,
  bookUpperInset: 10,
  bookSpineUpperOffset: 11,
  sparkCenter: { x: 613, y: 369 },
  sparkWidth: 88,
  sparkHeight: 80
};

/**
 * A deliberately bolder, simplified small-size geometry. The ring, node,
 * staircase, open-book cue, and four-point spark are still independent marks.
 */
export const faviconGeometry: LogoGeometry = {
  canvasSize: 1024,
  safeArea: {
    inset: 132
  },
  ringCenter: { x: 512, y: 494 },
  ringRadius: 300,
  ringStrokeWidth: 58,
  ringStartAngle: 138,
  ringEndAngle: 437,
  nodeCenter: { x: 350, y: 782 },
  nodeRadius: 58,
  stairOrigin: { x: 408, y: 590 },
  stairStepWidth: 68,
  stairStepHeight: 45,
  stairStrokeWidth: 54,
  stairCornerRadius: 27,
  stairInitialRise: 31,
  stairLevelCount: 4,
  bookCenter: { x: 512, y: 702 },
  bookWidth: 252,
  bookHeight: 76,
  bookPageGap: 0,
  bookStrokeWidth: 52,
  bookUpperInset: 0,
  bookSpineUpperOffset: 8,
  sparkCenter: { x: 622, y: 335 },
  sparkWidth: 116,
  sparkHeight: 106
};
