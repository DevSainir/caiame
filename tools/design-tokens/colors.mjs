import { deltaE, hexToOklab, toPolar, toGamutHex } from './oklab.mjs'

export const MERGE_THRESHOLD = 0.025
const JUNK_COUNT = 2
const NEUTRAL_CHROMA = 0.03

const NEUTRAL_LIGHTNESS = {
  50: 0.975, 100: 0.94, 200: 0.9, 300: 0.845, 400: 0.78, 500: 0.7,
  600: 0.62, 700: 0.53, 800: 0.44, 900: 0.36, 950: 0.27,
}
const CHROMATIC_LIGHTNESS = {
  50: 0.97, 100: 0.93, 200: 0.87, 300: 0.79, 400: 0.71, 500: 0.62,
  600: 0.55, 700: 0.47, 800: 0.4, 900: 0.33, 950: 0.26,
}
/** Chroma relative to the anchor step, so generated tints stay in the same family. */
const CHROMA_CURVE = {
  50: 0.12, 100: 0.22, 200: 0.4, 300: 0.62, 400: 0.85, 500: 1,
  600: 0.98, 700: 0.88, 800: 0.75, 900: 0.62, 950: 0.5,
}
const HUE_GROUPS = [
  { group: 'danger', from: -30, to: 45 },
  { group: 'warning', from: 45, to: 110 },
  { group: 'success', from: 110, to: 190 },
]

/** Frequency-ordered greedy clustering: the most used colour wins its neighbourhood. */
export function clusterColors(entries, threshold = MERGE_THRESHOLD) {
  const clusters = []
  for (const entry of [...entries].sort((a, b) => b.count - a.count)) {
    const lab = hexToOklab(entry.hex)
    const home = clusters.find((cluster) => deltaE(cluster.lab, lab) <= threshold)
    if (home) {
      home.count += entry.count
      home.members.push({ ...entry, distance: round(deltaE(home.lab, lab), 4) })
    } else {
      clusters.push({
        hex: entry.hex,
        lab,
        polar: toPolar(lab),
        count: entry.count,
        members: [{ ...entry, distance: 0 }],
      })
    }
  }
  return clusters
}

export function classify(cluster) {
  if (cluster.hex === '#ffffff') return 'white'
  if (cluster.hex === '#000000') return 'black'
  if (cluster.polar.chroma < NEUTRAL_CHROMA) return 'neutral'
  const hue = normalizeHue(cluster.polar.hue)
  const match = HUE_GROUPS.find((range) => hue >= range.from && hue < range.to)
  return match ? match.group : 'primary'
}

/**
 * Anchors keep the designer's exact hex; every step they do not cover is interpolated
 * between them, so the ramp always gets lighter as the number gets smaller.
 */
export function buildRamp(group, clusters) {
  const targets = group === 'neutral' ? NEUTRAL_LIGHTNESS : CHROMATIC_LIGHTNESS
  const steps = Object.keys(targets).map(Number)
  const { anchors, merged } = placeAnchors(group, clusters, steps, targets)
  const base = anchors.get(500) ?? [...anchors.values()][0]
  const lightness = interpolate(steps, anchors, targets)
  const baseStep = [...anchors].find(([, cluster]) => cluster === base)?.[0] ?? 500

  const ramp = {}
  for (const step of steps) {
    const anchor = anchors.get(step)
    if (anchor) {
      ramp[step] = { hex: anchor.hex, source: 'figma', count: anchor.count, cluster: anchor }
      continue
    }
    const chroma =
      group === 'neutral' ? 0 : base.polar.chroma * (CHROMA_CURVE[step] / CHROMA_CURVE[baseStep])
    ramp[step] = {
      hex: toGamutHex({ L: lightness.get(step), chroma, hue: base.polar.hue }),
      source: 'generated',
      count: 0,
    }
  }
  return { ramp, merged, violations: checkMonotonic(group, ramp) }
}

/** One step, one colour: a collision is decided by usage, the loser is reported as absorbed. */
function placeAnchors(group, clusters, steps, targets) {
  const anchors = new Map()
  const merged = []
  const ordered = [...clusters].sort((a, b) => b.count - a.count)

  if (group !== 'neutral' && ordered.length > 0) anchors.set(500, ordered.shift())

  for (const cluster of ordered.sort((a, b) => b.polar.L - a.polar.L)) {
    const step = nearestStep(steps, targets, cluster.polar.L)
    const occupant = anchors.get(step)
    if (!occupant) {
      anchors.set(step, cluster)
    } else if (cluster.count > occupant.count) {
      anchors.set(step, cluster)
      merged.push({ cluster: occupant, step })
    } else {
      merged.push({ cluster, step })
    }
  }
  return { anchors, merged }
}

/** Piecewise-linear lightness through the anchors, with the ends pinned to the defaults. */
function interpolate(steps, anchors, targets) {
  const knots = steps
    .map((step, index) => ({ step, index, L: anchors.get(step)?.polar.L }))
    .filter((knot) => knot.L !== undefined)
  const first = { step: steps[0], index: 0, L: targets[steps[0]] }
  const last = { step: steps.at(-1), index: steps.length - 1, L: targets[steps.at(-1)] }
  if (!knots.some((knot) => knot.index === 0)) knots.unshift(first)
  if (!knots.some((knot) => knot.index === steps.length - 1)) knots.push(last)

  const lightness = new Map()
  for (const [index, step] of steps.entries()) {
    if (anchors.has(step)) {
      lightness.set(step, anchors.get(step).polar.L)
      continue
    }
    const before = [...knots].reverse().find((knot) => knot.index < index) ?? knots[0]
    const after = knots.find((knot) => knot.index > index) ?? knots.at(-1)
    const span = after.index - before.index
    const ratio = span === 0 ? 0 : (index - before.index) / span
    lightness.set(step, before.L + (after.L - before.L) * ratio)
  }
  return lightness
}

function checkMonotonic(group, ramp) {
  const violations = []
  const entries = Object.entries(ramp)
  for (let index = 0; index + 1 < entries.length; index += 1) {
    const [step, value] = entries[index]
    const [nextStep, nextValue] = entries[index + 1]
    if (toPolar(hexToOklab(value.hex)).L <= toPolar(hexToOklab(nextValue.hex)).L) {
      violations.push(`${group}-${step} is not lighter than ${group}-${nextStep}`)
    }
  }
  return violations
}

function nearestStep(steps, targets, lightness) {
  if (steps.length === 0) return null
  return steps.reduce((best, step) =>
    Math.abs(targets[step] - lightness) < Math.abs(targets[best] - lightness) ? step : best,
  )
}

export function splitJunk(entries) {
  return {
    kept: entries.filter((entry) => entry.count > JUNK_COUNT),
    junk: entries.filter((entry) => entry.count <= JUNK_COUNT),
  }
}

function normalizeHue(hue) {
  return hue < -30 ? hue + 360 : hue
}

function round(value, digits) {
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}
