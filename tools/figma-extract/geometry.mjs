// Auto-layout is used in 18 frames out of a thousand: this file is where the real
// spacing scale comes from. Distances between neighbours are measured from geometry.

const MAX_GAP = 400
const MIN_SIDE = 4
const OVERLAP_RATIO = 0.5
const VECTOR_TYPES = new Set([
  'VECTOR',
  'ELLIPSE',
  'STAR',
  'LINE',
  'POLYGON',
  'BOOLEAN_OPERATION',
])

export function collectGeometry(node, collector, sample) {
  const children = (node.children ?? []).filter(isMeasurable)
  if (children.length === 0) return
  collectGaps(children, collector, sample)
  collectInsets(node, children, collector, sample)
}

function collectGaps(children, collector, sample) {
  measureAxis(children, collector, sample, {
    main: 'y',
    mainSize: 'height',
    cross: 'x',
    crossSize: 'width',
    histogram: 'gapVertical',
  })
  measureAxis(children, collector, sample, {
    main: 'x',
    mainSize: 'width',
    cross: 'y',
    crossSize: 'height',
    histogram: 'gapHorizontal',
  })
}

/** Neighbours count only when they actually line up on the perpendicular axis. */
function measureAxis(children, collector, sample, axis) {
  const sorted = [...children].sort(
    (a, b) => a.absoluteBoundingBox[axis.main] - b.absoluteBoundingBox[axis.main],
  )
  for (let index = 0; index + 1 < sorted.length; index += 1) {
    const first = sorted[index].absoluteBoundingBox
    const second = sorted[index + 1].absoluteBoundingBox
    if (!alignedOnCross(first, second, axis)) continue
    const gap = second[axis.main] - (first[axis.main] + first[axis.mainSize])
    record(collector, axis.histogram, gap, sample)
  }
}

function alignedOnCross(first, second, axis) {
  const start = Math.max(first[axis.cross], second[axis.cross])
  const end = Math.min(
    first[axis.cross] + first[axis.crossSize],
    second[axis.cross] + second[axis.crossSize],
  )
  const overlap = end - start
  if (overlap <= 0) return false
  const smaller = Math.min(first[axis.crossSize], second[axis.crossSize])
  return smaller > 0 && overlap / smaller >= OVERLAP_RATIO
}

/** Distance from a container's own edges to the block its children occupy. */
function collectInsets(node, children, collector, sample) {
  const box = node.absoluteBoundingBox
  if (!box || !hasVisibleSurface(node)) return
  // Auto-layout frames already reported their padding; measuring it again doubles the count.
  if (node.layoutMode && node.layoutMode !== 'NONE') return

  const boxes = children.map((child) => child.absoluteBoundingBox)
  const left = Math.min(...boxes.map((child) => child.x)) - box.x
  const top = Math.min(...boxes.map((child) => child.y)) - box.y
  const right = box.x + box.width - Math.max(...boxes.map((child) => child.x + child.width))
  const bottom = box.y + box.height - Math.max(...boxes.map((child) => child.y + child.height))

  for (const [side, value] of [
    ['left', left],
    ['top', top],
    ['right', right],
    ['bottom', bottom],
  ]) {
    record(collector, 'insets', value, sample, [side])
  }
}

function record(collector, histogram, raw, sample, tags = []) {
  if (!Number.isFinite(raw) || raw < 0 || raw > MAX_GAP) return
  const rounded = Math.round(raw)
  if (rounded === 0) {
    collector.stats.zeroGeometry += 1
    return
  }
  if (Math.abs(raw - rounded) > 0.25) collector.stats.fractionalGeometry += 1
  collector[histogram].add(rounded, { sample, tags })
}

function isMeasurable(node) {
  if (!node || node.visible === false) return false
  if (VECTOR_TYPES.has(node.type)) return false
  const box = node.absoluteBoundingBox
  if (!box) return false
  if (node.rotation) return false
  return box.width >= MIN_SIDE && box.height >= MIN_SIDE
}

function hasVisibleSurface(node) {
  const paints = [...(node.fills ?? []), ...(node.strokes ?? [])]
  return paints.some((paint) => paint.visible !== false)
}
