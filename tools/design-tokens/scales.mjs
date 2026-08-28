const GRID = 4
const JUNK_COUNT = 2
const RADIUS_LADDER = [2, 4, 8, 12, 20]
// Above this a distance describes the page layout, not the space between two elements.
const SPACING_CEILING = 160
/**
 * Values agreed during layout that the audit could not see, because they describe the
 * height of an element rather than the distance between two. Every entry needs a reason.
 */
const MANUAL_SPACING = [{ value: 80, reason: 'высота шапки и строки фильтров на главной' }]

/** Everything that measures a distance, snapped to the 4px grid with the drift recorded. */
export function buildSpacing(spacing) {
  const merged = new Map()
  const sources = [
    ['padding', spacing.padding],
    ['gap', spacing.gap],
    ['gap', spacing.gapVertical],
    ['gap', spacing.gapHorizontal],
    ['inset', spacing.insets],
  ]
  for (const [origin, entries] of sources) {
    for (const entry of entries ?? []) {
      const value = Number(entry.value)
      let record = merged.get(value)
      if (!record) {
        record = { value, count: 0, origins: {}, samples: [] }
        merged.set(value, record)
      }
      record.count += entry.count
      record.origins[origin] = (record.origins[origin] ?? 0) + entry.count
      if (record.samples.length < 3) record.samples.push(...entry.samples.slice(0, 1))
    }
  }

  const all = [...merged.values()].sort((a, b) => b.count - a.count)
  const frequent = all.filter((entry) => entry.count > JUNK_COUNT)
  const kept = frequent.filter((entry) => entry.value <= SPACING_CEILING)
  const layout = frequent.filter((entry) => entry.value > SPACING_CEILING)
  const junk = all.filter((entry) => entry.count <= JUNK_COUNT)

  const snapped = kept.map((entry) => {
    const target = Math.max(GRID, Math.round(entry.value / GRID) * GRID)
    return { ...entry, target, drift: round(target - entry.value, 2) }
  })

  const scale = new Map()
  for (const manual of MANUAL_SPACING) {
    scale.set(manual.value, { px: manual.value, count: 0, from: [], manual: manual.reason })
  }
  for (const entry of snapped.sort((a, b) => a.target - b.target)) {
    const step = scale.get(entry.target) ?? { px: entry.target, count: 0, from: [] }
    step.count += entry.count
    step.from.push({ value: entry.value, count: entry.count, drift: entry.drift })
    scale.set(entry.target, step)
  }

  return {
    scale: [...scale.values()].sort((a, b) => a.px - b.px),
    manual: MANUAL_SPACING,
    offGrid: snapped.filter((entry) => entry.drift !== 0).sort((a, b) => b.count - a.count),
    layout,
    junk,
  }
}

export function buildRadii(entries) {
  const kept = entries.filter((entry) => entry.count > JUNK_COUNT)
  const junk = entries.filter((entry) => entry.count <= JUNK_COUNT)
  const steps = new Map(RADIUS_LADDER.map((px) => [px, { px, count: 0, from: [] }]))

  for (const entry of kept) {
    const value = Number(entry.value)
    const target = RADIUS_LADDER.reduce((best, candidate) =>
      Math.abs(candidate - value) < Math.abs(best - value) ? candidate : best,
    )
    const step = steps.get(target)
    step.count += entry.count
    step.from.push({ value, count: entry.count, drift: target - value })
  }

  return { steps: [...steps.values()].filter((step) => step.count > 0), junk }
}

export function buildStrokes(entries) {
  const kept = entries.filter((entry) => entry.count > JUNK_COUNT)
  return kept.map((entry) => ({ px: Number(entry.value), count: entry.count }))
}

function round(value, digits) {
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}
