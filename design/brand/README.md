# Anshu Zhiti Brand Assets

This directory contains the production-ready, native-SVG reconstruction of the Anshu Zhiti symbol. The supplied PNG is retained only as a traceable reference in `reference/`; no final SVG embeds it or relies on raster data.

## Source and color normalization

The reference is a 1254 by 1254 RGB PNG. Direct interior samples were approximately `#0E1B2B` for the ink and `#003AFC` for the spark. The master uses the documented flat tokens in `src/brand-tokens.json`:

| Token | Production value | Rationale |
| --- | --- | --- |
| `primaryColor` | `#0B1B2D` | Stable near-black ink after removing source antialiasing and shadow variation. |
| `accentColor` | `#174BFF` | Flat, repeatable brand blue used for the four-point spark. |

## Geometry

All master symbols use `viewBox="0 0 1024 1024"`. All coordinates live in `src/logo-geometry.ts`; `src/logo-renderer.ts` derives the native SVG paths from those parameters. The generator applies a conservative whitespace-only normalization pass after generation, leaving the direct-path geometry unchanged.

The primary geometry preserves the supplied composition: a 299-degree open ring, a separated lower-left circular node, a two-layer open book, three equal staircase treads plus its fourth terminal rise, and a four-point spark. The book was narrowed slightly relative to the ring's inner diameter so it remains light at small sizes. The favicon has intentionally bolder strokes and one open-book cue, rather than a mechanical scale-down of the master.

## Commands

Run these commands from `frontend/`, which is the repository's existing Node workspace:

```powershell
npm run brand:generate
npm run brand:validate
npm run brand:preview
```

`brand:generate` compiles the local TypeScript, writes the master SVGs, and invokes the included Pillow-based SVG subset renderer for the PNG exports. It reads the generated native SVG paths rather than the source PNG, then writes transparent PNG masters, review previews, and the clear-space guide. No package is added to the repository.

`brand:validate` checks expected files, XML parsing, forbidden SVG constructs, exact viewBox values, token-only primary colors, PNG dimensions, alpha channels, transparent corners, reasonable file sizes, and the 16px dark/blue visual signals.

## Deliverables

| Location | Contents |
| --- | --- |
| `dist/svg/` | Primary, black, white, grayscale, favicon, and app-icon SVG exports. |
| `dist/png/` | Transparent primary-symbol PNGs from 16px through 1024px. |
| `dist/preview/` | Comparison sheet, light/dark size test, and clear-space guide. |

The primary symbol is recommended from 32px upward. Use `favicon.svg` for 16px browser/icon contexts. The clear-space guide uses `1N`, where `N` equals the lower-left node diameter.
