#!/usr/bin/env node
/**
 * Branded placeholder covers for the catalogue.
 *
 * Free-licence medical stock at marketing quality does not exist in the open image banks;
 * everything on offer looks amateur next to the rest of the page. A deliberate branded card
 * beats a bad photograph, and swapping real photography in later is one field on the course.
 *
 * Colours come from tokens.json, so these covers cannot drift away from the palette.
 * Each slug gets a fixed motif and scheme, so a course never changes its face between builds.
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

const ROOT = resolve(import.meta.dirname, '../..')
const TOKENS = JSON.parse(readFileSync(resolve(ROOT, 'tokens.json'), 'utf8'))
const OUT = resolve(ROOT, 'frontend/public/covers')

const W = 800
const H = 450
const color = (group, step) => TOKENS.color[group][step].$value

// Light, bright and deep, so neighbouring tiles in a row never read as the same card.
const SCHEMES = [
  { from: color('primary', 50), to: color('primary', 200), ink: color('primary', 500), alpha: 0.5 },
  { from: color('primary', 500), to: color('primary', 800), ink: '#ffffff', alpha: 0.18 },
  { from: color('primary', 900), to: color('primary', 950), ink: color('primary', 400), alpha: 0.3 },
  { from: color('primary', 400), to: color('primary', 600), ink: '#ffffff', alpha: 0.2 },
  { from: color('primary', 950), to: color('primary', 700), ink: color('success', 500), alpha: 0.35 },
]

const SPARKLE =
  'M9 0L10.0182 7.98177L18 9L10.0182 10.0182L9 18L7.98177 10.0182L0 9L7.98177 7.98177L9 0Z'

const COVERS = [
  { slug: 'cardiology', motif: 'rings', scheme: 1 },
  { slug: 'neurology', motif: 'hexes', scheme: 2 },
  { slug: 'pediatrics', motif: 'dots', scheme: 0 },
  { slug: 'surgery', motif: 'stripes', scheme: 3 },
  { slug: 'intensive-care', motif: 'triangle', scheme: 3 },
  { slug: 'radiology', motif: 'rings', scheme: 4 },
  { slug: 'endocrinology', motif: 'dots', scheme: 3 },
  { slug: 'infectious', motif: 'stripes', scheme: 0 },
  { slug: 'ultrasound', motif: 'hexes', scheme: 1 },
]

/** Deterministic pseudo-random, so a slug always produces the same cover. */
function seeded(slug) {
  let hash = 2166136261
  for (const char of slug) {
    hash ^= char.charCodeAt(0)
    hash = Math.imul(hash, 16777619)
  }
  return () => {
    hash = Math.imul(hash ^ (hash >>> 15), 2246822507)
    hash = Math.imul(hash ^ (hash >>> 13), 3266489909)
    return ((hash ^= hash >>> 16) >>> 0) / 4294967296
  }
}

function hexPoints(cx, cy, radius) {
  return Array.from({ length: 6 }, (_, index) => {
    const angle = (Math.PI / 3) * index - Math.PI / 2
    return `${(cx + radius * Math.cos(angle)).toFixed(1)},${(cy + radius * Math.sin(angle)).toFixed(1)}`
  }).join(' ')
}

const MOTIFS = {
  /** Concentric rings drifting off the right edge. */
  rings(random, { ink, alpha }) {
    const cx = 600 + Math.round(random() * 90)
    const cy = 120 + Math.round(random() * 180)
    return Array.from({ length: 5 }, (_, index) => {
      const radius = 70 + index * 62
      return `<circle cx="${cx}" cy="${cy}" r="${radius}" fill="none" stroke="${ink}" stroke-opacity="${(alpha * (1 - index * 0.13)).toFixed(3)}" stroke-width="${18 - index * 2}"/>`
    }).join('\n  ')
  },

  /** Two overlapping hexagons, the motif from the illustration in the About block. */
  hexes(random, { ink, alpha }) {
    const cx = 560 + Math.round(random() * 120)
    const cy = 190 + Math.round(random() * 80)
    return [
      `<polygon points="${hexPoints(cx, cy, 210)}" fill="${ink}" opacity="${(alpha * 0.35).toFixed(3)}"/>`,
      `<polygon points="${hexPoints(cx - 150, cy + 60, 260)}" fill="none" stroke="${ink}" stroke-opacity="${alpha}" stroke-width="3"/>`,
      `<polygon points="${hexPoints(cx + 90, cy - 130, 120)}" fill="none" stroke="${ink}" stroke-opacity="${(alpha * 0.7).toFixed(3)}" stroke-width="3"/>`,
    ].join('\n  ')
  },

  /** A grid of dots fading towards one corner. */
  dots(random, { ink, alpha }) {
    const step = 46
    const cells = []
    for (let row = 0; row < 10; row += 1) {
      for (let column = 0; column < 18; column += 1) {
        const x = 20 + column * step
        const y = 20 + row * step
        const fade = 1 - (column / 18) * 0.75
        const radius = 3 + random() * 7 * fade
        cells.push(
          `<circle cx="${x}" cy="${y}" r="${radius.toFixed(1)}" fill="${ink}" opacity="${(alpha * fade).toFixed(3)}"/>`,
        )
      }
    }
    return cells.join('')
  },

  /** Wide diagonal bands. */
  stripes(random, { ink, alpha }) {
    const offset = Math.round(random() * 120)
    return Array.from({ length: 6 }, (_, index) => {
      const x = -200 + offset + index * 190
      return `<polygon points="${x},${H} ${x + 110},${H} ${x + 420},0 ${x + 310},0" fill="${ink}" opacity="${(alpha * (0.35 + (index % 3) * 0.22)).toFixed(3)}"/>`
    }).join('\n  ')
  },

  /** One large triangle with a hexagon outline behind it. */
  triangle(random, { ink, alpha }) {
    const x = 420 + Math.round(random() * 140)
    return [
      `<polygon points="${hexPoints(x - 40, 200, 250)}" fill="none" stroke="${ink}" stroke-opacity="${(alpha * 0.55).toFixed(3)}" stroke-width="3"/>`,
      `<polygon points="${x},40 ${x + 330},${H - 30} ${x - 310},${H - 30}" fill="${ink}" opacity="${(alpha * 0.5).toFixed(3)}"/>`,
    ].join('\n  ')
  },
}

function cover({ slug, motif, scheme }) {
  const random = seeded(slug)
  const palette = SCHEMES[scheme]
  const angle = Math.round(random() * 50) - 25

  const sparkles = Array.from({ length: 4 }, () => {
    const scale = (0.6 + random() * 1.4).toFixed(2)
    const x = Math.round(40 + random() * 700)
    const y = Math.round(30 + random() * 380)
    return `<g transform="translate(${x} ${y}) scale(${scale})" opacity="${(palette.alpha * 1.6).toFixed(2)}"><path d="${SPARKLE}" fill="${palette.ink}"/></g>`
  }).join('\n  ')

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1" gradientTransform="rotate(${angle} 0.5 0.5)">
      <stop offset="0" stop-color="${palette.from}"/>
      <stop offset="1" stop-color="${palette.to}"/>
    </linearGradient>
    <clipPath id="frame"><rect width="${W}" height="${H}"/></clipPath>
  </defs>
  <rect width="${W}" height="${H}" fill="url(#bg)"/>
  <g clip-path="url(#frame)">
  ${MOTIFS[motif](random, palette)}
  ${sparkles}
  </g>
</svg>
`
}

mkdirSync(OUT, { recursive: true })
for (const item of COVERS) {
  writeFileSync(resolve(OUT, `${item.slug}.svg`), cover(item))
}
console.log(`written ${COVERS.length} covers -> ${OUT}`)
