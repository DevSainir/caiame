#!/usr/bin/env node
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { clusterColors, classify, buildRamp, splitJunk, MERGE_THRESHOLD } from './colors.mjs'
import { buildTypography } from './typography.mjs'
import { buildSpacing, buildRadii, buildStrokes } from './scales.mjs'
import { contrastRatio } from './oklab.mjs'
import { renderMapping } from './report.mjs'

const ROOT = resolve(import.meta.dirname, '../..')
const AUDIT = resolve(ROOT, 'design-audit.json')
const TOKENS = resolve(ROOT, 'tokens.json')
const MAPPING = resolve(ROOT, 'docs/tokens-mapping.md')

const FONT_STACK = "'Manrope', ui-sans-serif, system-ui, 'Segoe UI', Roboto, sans-serif"

/**
 * Roles that carry text are one step darker than the mockup: the greys the designer
 * used for text reach 2.85:1 and 3.79:1 on white, and WCAG AA asks for 4.5:1.
 * The palette itself is untouched — only what each role points at.
 */
const SEMANTIC = {
  text: {
    primary: '#3c3c3c',
    secondary: '#6a6a6a',
    muted: '#838383',
    disabled: '#bebebe',
    inverse: '#ffffff',
    accent: '#0362e4',
    danger: '#df2c33',
  },
  surface: {
    page: '#ffffff',
    subtle: '#f3f7fa',
    accent: '#2178ff',
    inverse: '#002051',
    success: '#61c000',
  },
  border: {
    subtle: '#e7e7e7',
    default: '#bebebe',
    accent: '#2178ff',
    danger: '#ff4a4a',
  },
}

main()

function main() {
  const audit = JSON.parse(readFileSync(AUDIT, 'utf8'))
  const opaque = audit.colors.filter((entry) => entry.alpha === 1)
  const translucent = audit.colors.filter((entry) => entry.alpha !== 1)

  const { kept, junk: colorJunk } = splitJunk(opaque)
  const clusters = clusterColors(kept)
  const byGroup = new Map()
  for (const cluster of clusters) {
    const group = classify(cluster)
    byGroup.set(group, [...(byGroup.get(group) ?? []), cluster])
  }

  const ramps = {}
  const mergedAway = []
  for (const group of ['primary', 'neutral', 'success', 'danger']) {
    const source = byGroup.get(group) ?? []
    if (source.length === 0) continue
    const { ramp, merged, violations } = buildRamp(group, source)
    ramps[group] = ramp
    for (const item of merged) mergedAway.push({ group, ...item })
    for (const violation of violations) console.warn(`WARNING: ${violation}`)
  }
  ramps.warning = warningRamp()

  const typography = buildTypography(audit.typography)
  const spacing = buildSpacing(audit.spacing)
  const radii = buildRadii(audit.radii)
  const strokes = buildStrokes(audit.strokeWeights)
  const semantic = resolveSemantic(ramps)

  writeFileSync(TOKENS, `${JSON.stringify(
    buildTokens({ ramps, semantic, typography, spacing, radii, strokes }),
    null,
    2,
  )}\n`)

  mkdirSync(dirname(MAPPING), { recursive: true })
  writeFileSync(
    MAPPING,
    // Файл проходит те же хуки, что и рукописные: без завершающего перевода строки
    // end-of-file-fixer будет чинить его после каждой пересборки.
    ensureTrailingNewline(renderMapping({
      audit,
      clusters,
      byGroup,
      ramps,
      mergedAway,
      colorJunk,
      translucent,
      typography,
      spacing,
      radii,
      strokes,
      semantic,
      threshold: MERGE_THRESHOLD,
      contrast: contrastReport(ramps),
    })),
  )

  console.log(`tokens:  ${TOKENS}`)
  console.log(`mapping: ${MAPPING}`)
  console.log(
    `colors: ${audit.colors.length} raw -> ${clusters.length} clusters -> ` +
      `${Object.keys(ramps).length} ramps; ${colorJunk.length} discarded as noise`,
  )
  console.log(
    `type: ${audit.typography.length} combinations -> ${typography.steps.length} steps; ` +
      `spacing: ${spacing.scale.length} steps, ${spacing.offGrid.length} values off the 4px grid; ` +
      `radii: ${radii.steps.length} steps`,
  )
}

/** No amber, orange or yellow exists anywhere in the mockup — this ramp is invented. */
function warningRamp() {
  const scale = {
    50: '#fffaeb', 100: '#fef0c7', 200: '#fedf89', 300: '#fec84b', 400: '#fdb022',
    500: '#f79009', 600: '#dc6803', 700: '#b54708', 800: '#93370d', 900: '#7a2e0e',
    950: '#4e1d09',
  }
  return Object.fromEntries(
    Object.entries(scale).map(([step, hex]) => [step, { hex, source: 'invented', count: 0 }]),
  )
}

function resolveSemantic(ramps) {
  const resolved = {}
  for (const [role, values] of Object.entries(SEMANTIC)) {
    resolved[role] = {}
    for (const [name, hex] of Object.entries(values)) {
      resolved[role][name] = { hex, reference: findStep(ramps, hex) }
    }
  }
  return resolved
}

function findStep(ramps, hex) {
  if (hex === '#ffffff') return 'color.white'
  for (const [group, ramp] of Object.entries(ramps)) {
    for (const [step, value] of Object.entries(ramp)) {
      if (value.hex === hex) return `color.${group}.${step}`
    }
  }
  return null
}

function ensureTrailingNewline(text) {
  return text.endsWith('\n') ? text : `${text}\n`
}

function contrastReport(ramps) {
  const foregrounds = ['#3c3c3c', '#838383', '#999999', '#bebebe', '#2178ff', '#ff4a4a', '#61c000']
  return foregrounds.map((hex) => {
    const onWhite = contrastRatio(hex, '#ffffff')
    return {
      hex,
      onWhite,
      onSubtle: contrastRatio(hex, '#f3f7fa'),
      fix: onWhite >= 4.5 ? null : darkestPassing(ramps, hex),
    }
  })
}

/** The lightest step of the same ramp that still reaches AA on white. */
function darkestPassing(ramps, hex) {
  for (const [group, ramp] of Object.entries(ramps)) {
    const steps = Object.entries(ramp)
    if (!steps.some(([, value]) => value.hex === hex)) continue
    const passing = steps.find(([, value]) => contrastRatio(value.hex, '#ffffff') >= 4.5)
    if (passing) return `${group}-${passing[0]} (${passing[1].hex}, ${contrastRatio(passing[1].hex, '#ffffff')})`
  }
  return null
}

function buildTokens({ ramps, semantic, typography, spacing, radii, strokes }) {
  return {
    $schema: 'https://tr.designtokens.org/format/',
    $description: 'Caiame design tokens, reconstructed from the Figma file (page "profile", 1440px frames).',
    color: {
      $type: 'color',
      white: { $value: '#ffffff' },
      ...Object.fromEntries(
        Object.entries(ramps).map(([group, ramp]) => [
          group,
          Object.fromEntries(
            Object.entries(ramp).map(([step, value]) => [
              step,
              {
                $value: value.hex,
                $extensions: { 'app.caiame.source': value.source, 'app.caiame.uses': value.count },
              },
            ]),
          ),
        ]),
      ),
      ...Object.fromEntries(
        Object.entries(semantic).map(([role, values]) => [
          role,
          Object.fromEntries(
            Object.entries(values).map(([name, value]) => [
              name,
              { $value: value.reference ? `{color.${value.reference.replace('color.', '')}}` : value.hex },
            ]),
          ),
        ]),
      ),
    },
    fontFamily: { $type: 'fontFamily', sans: { $value: FONT_STACK } },
    fontWeight: {
      $type: 'fontWeight',
      regular: { $value: 400 },
      medium: { $value: 500 },
      semibold: { $value: 600 },
      bold: { $value: 700 },
    },
    fontSize: {
      $type: 'dimension',
      ...Object.fromEntries(
        typography.steps.map((step) => [
          step.name,
          {
            $value: `${step.fontSize}px`,
            $extensions: {
              'app.caiame.lineHeight': step.lineHeight,
              'app.caiame.uses': step.count,
            },
          },
        ]),
      ),
    },
    lineHeight: {
      $type: 'number',
      tight: { $value: 1.3 },
      snug: { $value: 1.5 },
      normal: { $value: 1.6 },
      relaxed: { $value: 1.8 },
    },
    letterSpacing: {
      $type: 'dimension',
      tight: { $value: '-0.03em' },
      normal: { $value: '0em' },
    },
    spacing: {
      $type: 'dimension',
      0: { $value: '0px' },
      ...Object.fromEntries(
        spacing.scale.map((step) => [
          step.px / 4,
          { $value: `${step.px}px`, $extensions: { 'app.caiame.uses': step.count } },
        ]),
      ),
    },
    borderRadius: {
      $type: 'dimension',
      none: { $value: '0px' },
      ...Object.fromEntries(
        radii.steps.map((step, index) => [
          ['xs', 'sm', 'md', 'lg', 'xl', '2xl'][index] ?? `step-${index}`,
          { $value: `${step.px}px`, $extensions: { 'app.caiame.uses': step.count } },
        ]),
      ),
      full: { $value: '9999px' },
    },
    borderWidth: {
      $type: 'dimension',
      0: { $value: '0px' },
      ...Object.fromEntries(
        strokes.map((stroke) => [
          stroke.px === 1 ? 'DEFAULT' : String(stroke.px),
          { $value: `${stroke.px}px`, $extensions: { 'app.caiame.uses': stroke.count } },
        ]),
      ),
    },
  }
}
