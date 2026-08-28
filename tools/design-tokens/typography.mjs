// Figma's "Auto" line height for Manrope resolves to 136.6% — a default nobody chose,
// so it does not get a vote when picking the line height of a step.
const AUTO_RATIO = 1.366
const AUTO_TOLERANCE = 0.02
const ALLOWED_RATIOS = [1.2, 1.3, 1.5, 1.6, 1.8]
const LADDER = ['2xs', 'xs', 'sm', 'base', 'lg', 'xl', '2xl', '3xl', '4xl', '5xl', '6xl']
const JUNK_COUNT = 2
const WEIGHT_NAMES = { 400: 'regular', 500: 'medium', 600: 'semibold', 700: 'bold', 800: 'extrabold' }

export function buildTypography(entries) {
  const sizes = groupBySize(entries)
  const kept = sizes.filter((size) => size.count > JUNK_COUNT)
  const junk = sizes
    .filter((size) => size.count <= JUNK_COUNT)
    .map((size) => ({ ...size, snappedTo: nearest(kept, size.fontSize).fontSize }))

  kept.sort((a, b) => a.fontSize - b.fontSize)
  const steps = kept.map((size, index) => ({
    name: LADDER[index] ?? `step-${index}`,
    fontSize: size.fontSize,
    lineHeight: ruleRatio(size.fontSize),
    dataLineHeight: pickRatio(size),
    count: size.count,
    lineHeights: size.lineHeights,
    weights: size.weights,
    samples: size.samples,
  }))

  return { steps, junk, letterSpacing: letterSpacingReport(entries), weights: weightReport(entries) }
}

function groupBySize(entries) {
  const bySize = new Map()
  for (const entry of entries) {
    let size = bySize.get(entry.fontSize)
    if (!size) {
      size = {
        fontSize: entry.fontSize,
        count: 0,
        lineHeights: new Map(),
        weights: new Map(),
        samples: [],
      }
      bySize.set(entry.fontSize, size)
    }
    size.count += entry.count
    const ratio = round(entry.lineHeightPx / entry.fontSize, 3)
    size.lineHeights.set(ratio, (size.lineHeights.get(ratio) ?? 0) + entry.count)
    size.weights.set(entry.fontWeight, (size.weights.get(entry.fontWeight) ?? 0) + entry.count)
    if (entry.samples[0] && size.samples.length < 3) size.samples.push(entry.samples[0].name)
  }
  return [...bySize.values()].map((size) => ({
    ...size,
    lineHeights: [...size.lineHeights].sort((a, b) => b[1] - a[1]),
    weights: [...size.weights].sort((a, b) => b[1] - a[1]),
  }))
}

/**
 * The file has no line-height system: 1.8, 1.6, 1.5 and Figma's auto sit on the same size.
 * A rule by role beats a majority vote that would make 32px airier than 28px.
 */
function ruleRatio(fontSize) {
  if (fontSize <= 12) return 1.5
  if (fontSize <= 20) return 1.6
  return 1.3
}

function pickRatio(size) {
  const voted = size.lineHeights.filter(([ratio]) => Math.abs(ratio - AUTO_RATIO) > AUTO_TOLERANCE)
  const winner = voted[0] ?? size.lineHeights[0]
  const ratio = winner[0]
  return ALLOWED_RATIOS.reduce((best, candidate) =>
    Math.abs(candidate - ratio) < Math.abs(best - ratio) ? candidate : best,
  )
}

function letterSpacingReport(entries) {
  const percentages = new Map()
  for (const entry of entries) {
    if (entry.fontSize === 0) continue
    const percent = round((entry.letterSpacing / entry.fontSize) * 100, 1)
    percentages.set(percent, (percentages.get(percent) ?? 0) + entry.count)
  }
  const sorted = [...percentages].sort((a, b) => b[1] - a[1])
  return { dominant: sorted[0][0], distribution: sorted }
}

function weightReport(entries) {
  const weights = new Map()
  for (const entry of entries) {
    weights.set(entry.fontWeight, (weights.get(entry.fontWeight) ?? 0) + entry.count)
  }
  return [...weights]
    .sort((a, b) => b[1] - a[1])
    .map(([weight, count]) => ({
      weight,
      name: WEIGHT_NAMES[weight] ?? String(weight),
      count,
      junk: count <= JUNK_COUNT * 5,
    }))
}

function nearest(sizes, value) {
  return sizes.reduce((best, size) =>
    Math.abs(size.fontSize - value) < Math.abs(best.fontSize - value) ? size : best,
  )
}

function round(value, digits) {
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}
