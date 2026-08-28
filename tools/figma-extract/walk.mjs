import { Histogram } from './histogram.mjs'
import { collectGeometry } from './geometry.mjs'

const SHADOW_TYPES = new Set(['DROP_SHADOW', 'INNER_SHADOW'])
const PATH_DEPTH = 3
const PILL_TOLERANCE = 1.5

export function createCollector() {
  return {
    colors: new Histogram(),
    typography: new Histogram(),
    padding: new Histogram(),
    gap: new Histogram(),
    gapVertical: new Histogram(),
    gapHorizontal: new Histogram(),
    insets: new Histogram(),
    radii: new Histogram(),
    pillRadii: new Histogram(),
    strokeWeights: new Histogram(),
    shadows: new Histogram(),
    frameWidths: new Histogram(),
    frameHeights: new Histogram(),
    stats: {
      nodesVisited: 0,
      nodesHidden: 0,
      byType: {},
      gradientFills: 0,
      imageFills: 0,
      zeroPadding: 0,
      zeroGap: 0,
      zeroGeometry: 0,
      fractionalGeometry: 0,
      textNodes: 0,
      textOverrides: 0,
    },
    errors: [],
  }
}

/** Depth-first walk. Hidden nodes are skipped together with everything under them. */
export function walk(node, collector, ancestors = []) {
  if (!node || typeof node !== 'object') return
  if (node.visible === false) {
    collector.stats.nodesHidden += 1
    return
  }

  collector.stats.nodesVisited += 1
  collector.stats.byType[node.type] = (collector.stats.byType[node.type] ?? 0) + 1

  const sample = {
    name: node.name,
    type: node.type,
    path: ancestors.slice(-PATH_DEPTH).join(' / '),
  }

  try {
    collectPaints(node, collector, sample)
    collectText(node, collector, sample)
    collectLayout(node, collector, sample)
    collectRadii(node, collector, sample)
    collectStroke(node, collector, sample)
    collectShadows(node, collector, sample)
    collectGeometry(node, collector, sample)
  } catch (error) {
    collector.errors.push({
      id: node.id,
      name: node.name,
      type: node.type,
      path: sample.path,
      reason: error.message,
    })
  }

  const children = node.children
  if (!Array.isArray(children)) return
  const nextAncestors = [...ancestors, node.name]
  for (const child of children) walk(child, collector, nextAncestors)
}

/** Top-level frames of a page tell us which breakpoints the design actually uses. */
export function collectFrameSizes(page, collector) {
  for (const child of page.children ?? []) {
    if (child.visible === false) continue
    const box = child.absoluteBoundingBox
    if (!box) continue
    const sample = { name: child.name, type: child.type, path: page.name }
    collector.frameWidths.add(round(box.width), { sample })
    collector.frameHeights.add(round(box.height), { sample })
  }
}

function collectPaints(node, collector, sample) {
  const context = node.type === 'TEXT' ? 'text' : 'fill'
  for (const paint of node.fills ?? []) addPaint(paint, collector, sample, context)
  for (const paint of node.strokes ?? []) addPaint(paint, collector, sample, 'stroke')
}

function addPaint(paint, collector, sample, context) {
  if (!paint || paint.visible === false) return
  if (paint.type !== 'SOLID') {
    if (String(paint.type).startsWith('GRADIENT')) collector.stats.gradientFills += 1
    if (paint.type === 'IMAGE') collector.stats.imageFills += 1
    return
  }
  const { hex, alpha } = solidToHex(paint)
  const value = alpha === 1 ? hex : `${hex}/${alpha}`
  collector.colors.add(value, { fields: { hex, alpha }, sample, tags: [context] })
}

function collectText(node, collector, sample) {
  if (node.type !== 'TEXT' || !node.style) return
  collector.stats.textNodes += 1
  addTypography(node.style, collector, sample)

  // Inline per-character styling lives here, and in this file it carries real values.
  for (const override of Object.values(node.styleOverrideTable ?? {})) {
    if (!override || typeof override !== 'object') continue
    const touchesType = ['fontFamily', 'fontSize', 'fontWeight', 'lineHeightPx', 'letterSpacing']
      .some((key) => key in override)
    if (touchesType) {
      collector.stats.textOverrides += 1
      addTypography({ ...node.style, ...override }, collector, { ...sample, inline: true })
    }
    for (const paint of override.fills ?? []) addPaint(paint, collector, sample, 'text')
  }
}

function addTypography(style, collector, sample) {
  const fontFamily = style.fontFamily ?? 'unknown'
  const fontSize = round(style.fontSize ?? 0)
  const fontWeight = style.fontWeight ?? 400
  const lineHeightPx = round(style.lineHeightPx ?? 0)
  const letterSpacing = round(style.letterSpacing ?? 0)
  const value = `${fontFamily} ${fontSize}/${lineHeightPx} w${fontWeight} ls${letterSpacing}`
  collector.typography.add(value, {
    fields: { fontFamily, fontSize, fontWeight, lineHeightPx, letterSpacing },
    sample,
  })
}

function collectLayout(node, collector, sample) {
  if (!node.layoutMode || node.layoutMode === 'NONE') return
  for (const side of ['paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft']) {
    const value = round(node[side] ?? 0)
    if (value === 0) {
      collector.stats.zeroPadding += 1
      continue
    }
    collector.padding.add(value, { sample, tags: [side.replace('padding', '').toLowerCase()] })
  }
  const gap = round(node.itemSpacing ?? 0)
  if (gap === 0) collector.stats.zeroGap += 1
  else collector.gap.add(gap, { sample, tags: [node.layoutMode.toLowerCase()] })
}

function collectRadii(node, collector, sample) {
  if (Array.isArray(node.rectangleCornerRadii)) {
    // Four numbers describe one rectangle: counting each corner would triple its weight.
    for (const value of new Set(node.rectangleCornerRadii.map(round))) {
      if (value > 0) collector.radii.add(value, { sample, tags: ['perCorner'] })
    }
    return
  }
  const value = round(node.cornerRadius ?? 0)
  if (value === 0) return
  // A radius equal to half the short side is a pill, not a step on the radius scale.
  // Counting those as radii is what invents phantom steps like 22px.
  collector[isPill(node, value) ? 'pillRadii' : 'radii'].add(value, { sample })
}

function isPill(node, radius) {
  const box = node.absoluteBoundingBox
  if (!box) return false
  return radius * 2 >= Math.min(box.width, box.height) - PILL_TOLERANCE
}

function collectStroke(node, collector, sample) {
  const hasStroke = (node.strokes ?? []).some((paint) => paint.visible !== false)
  if (!hasStroke) return
  const value = round(node.strokeWeight ?? 0)
  if (value > 0) collector.strokeWeights.add(value, { sample })
}

function collectShadows(node, collector, sample) {
  for (const effect of node.effects ?? []) {
    if (effect.visible === false || !SHADOW_TYPES.has(effect.type)) continue
    const { hex, alpha } = solidToHex(effect)
    const offset = effect.offset ?? { x: 0, y: 0 }
    const value = [
      `${round(offset.x)}px`,
      `${round(offset.y)}px`,
      `${round(effect.radius ?? 0)}px`,
      `${round(effect.spread ?? 0)}px`,
      rgbaString(effect.color),
    ].join(' ')
    collector.shadows.add(effect.type === 'INNER_SHADOW' ? `inset ${value}` : value, {
      fields: { type: effect.type, hex, alpha },
      sample,
    })
  }
}

function solidToHex(paint) {
  const color = paint.color
  if (!color) throw new Error(`solid paint without color (${paint.type})`)
  const hex = `#${[color.r, color.g, color.b].map(channel).join('')}`
  const alpha = round((paint.opacity ?? 1) * (color.a ?? 1), 2)
  return { hex, alpha }
}

function rgbaString(color) {
  if (!color) return 'rgba(0, 0, 0, 0)'
  const [r, g, b] = [color.r, color.g, color.b].map((value) => Math.round(clamp(value) * 255))
  return `rgba(${r}, ${g}, ${b}, ${round(color.a ?? 1, 2)})`
}

function channel(value) {
  return Math.round(clamp(value) * 255).toString(16).padStart(2, '0')
}

function clamp(value) {
  return Math.min(1, Math.max(0, Number(value) || 0))
}

function round(value, digits = 2) {
  const factor = 10 ** digits
  return Math.round((Number(value) || 0) * factor) / factor
}
