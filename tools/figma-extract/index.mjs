#!/usr/bin/env node
import { mkdirSync, readFileSync, writeFileSync, statSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { loadEnv } from './env.mjs'
import { createCollector, walk, collectFrameSizes } from './walk.mjs'

const ROOT = resolve(import.meta.dirname, '../..')
const CACHE_PATH = resolve(ROOT, '.cache/figma-raw.json')
const DEFAULT_OUT = resolve(ROOT, 'design-audit.json')
const API = 'https://api.figma.com/v1/files'

main().catch((error) => {
  console.error(`\nfigma-extract failed: ${error.message}`)
  process.exit(1)
})

async function main() {
  const options = parseArgs(process.argv.slice(2))
  const env = loadEnv(resolve(ROOT, '.env'))
  const token = env.FIGMA_TOKEN
  const fileKey = options.file ?? env.FIGMA_FILE_KEY
  if (!token) throw new Error('FIGMA_TOKEN is missing in .env')
  if (!fileKey) throw new Error('FIGMA_FILE_KEY is missing in .env')

  const file = await loadFile(fileKey, token, options.refresh)
  const pages = (file.document.children ?? []).filter((page) => page.type === 'CANVAS')

  if (options.listPages) {
    console.log(`\n${file.name} — ${pages.length} page(s):`)
    for (const page of pages) {
      const hidden = page.visible === false ? ' (hidden)' : ''
      console.log(`  ${page.name}${hidden} — ${(page.children ?? []).length} top-level node(s)`)
    }
    return
  }

  const selected = selectPages(pages, options.pages)
  const collector = createCollector()
  for (const page of selected) {
    const roots = selectRoots(page, options.rootWidths)
    collectFrameSizes({ name: page.name, children: roots }, collector)
    for (const root of roots) walk(root, collector, [page.name])
  }

  const audit = buildAudit({ file, fileKey, selected, pages, collector, options })
  writeFileSync(options.out, `${JSON.stringify(audit, null, 2)}\n`)
  report(audit, collector, options.out)
}

function parseArgs(argv) {
  const options = {
    pages: [],
    rootWidths: [],
    refresh: false,
    listPages: false,
    out: DEFAULT_OUT,
    file: null,
  }
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]
    if (arg === '--page') options.pages.push(requireValue(argv, ++index, '--page'))
    else if (arg === '--root-width') {
      options.rootWidths.push(Number(requireValue(argv, ++index, '--root-width')))
    }
    else if (arg === '--out') options.out = resolve(ROOT, requireValue(argv, ++index, '--out'))
    else if (arg === '--file') options.file = requireValue(argv, ++index, '--file')
    else if (arg === '--refresh') options.refresh = true
    else if (arg === '--list-pages') options.listPages = true
    else if (arg === '--help' || arg === '-h') {
      console.log(USAGE)
      process.exit(0)
    } else throw new Error(`unknown argument: ${arg}`)
  }
  return options
}

const USAGE = `Usage: node tools/figma-extract [options]

  --page "<name>"   restrict the audit to this page (repeatable)
  --root-width <n>  keep only top-level frames this wide, rounded to 1px (repeatable);
                    mockups scaled to another artboard size pollute every scale
  --list-pages      print page names from the cached file and exit
  --refresh         ignore .cache/figma-raw.json and re-download
  --file <key>      override FIGMA_FILE_KEY
  --out <path>      output path (default design-audit.json)`

function requireValue(argv, index, flag) {
  const value = argv[index]
  if (value === undefined) throw new Error(`${flag} needs a value`)
  return value
}

async function loadFile(fileKey, token, refresh) {
  if (!refresh) {
    try {
      const cached = JSON.parse(readFileSync(CACHE_PATH, 'utf8'))
      const age = Math.round((Date.now() - statSync(CACHE_PATH).mtimeMs) / 60000)
      console.log(`cache: ${CACHE_PATH} (${age} min old, --refresh to re-download)`)
      return cached
    } catch (error) {
      if (error.code !== 'ENOENT') console.warn(`cache unreadable (${error.message}), downloading`)
    }
  }

  console.log(`GET ${API}/${fileKey}`)
  const started = Date.now()
  const response = await fetch(`${API}/${fileKey}`, { headers: { 'X-Figma-Token': token } })
  const body = await response.text()
  if (!response.ok) {
    throw new Error(`Figma API ${response.status} ${response.statusText}: ${body.slice(0, 500)}`)
  }
  mkdirSync(dirname(CACHE_PATH), { recursive: true })
  writeFileSync(CACHE_PATH, body)
  const mb = (body.length / 1024 / 1024).toFixed(1)
  console.log(`downloaded ${mb} MB in ${((Date.now() - started) / 1000).toFixed(1)}s -> ${CACHE_PATH}`)
  return JSON.parse(body)
}

function selectPages(pages, wanted) {
  if (wanted.length === 0) return pages
  const selected = []
  for (const name of wanted) {
    const page = pages.find((candidate) => candidate.name === name)
    if (!page) {
      const known = pages.map((candidate) => `"${candidate.name}"`).join(', ')
      throw new Error(`page "${name}" not found. Available: ${known}`)
    }
    selected.push(page)
  }
  return selected
}

/** Top-level frames of one page, optionally narrowed to given artboard widths. */
function selectRoots(page, rootWidths) {
  const roots = (page.children ?? []).filter((node) => node.visible !== false)
  if (rootWidths.length === 0) return roots
  const kept = roots.filter((node) => {
    const width = Math.round(node.absoluteBoundingBox?.width ?? 0)
    return rootWidths.includes(width)
  })
  if (kept.length === 0) {
    const widths = [...new Set(roots.map((n) => Math.round(n.absoluteBoundingBox?.width ?? 0)))]
    throw new Error(
      `page "${page.name}" has no top-level frame of width ${rootWidths.join('/')}. ` +
        `Widths present: ${widths.sort((a, b) => b - a).join(', ')}`,
    )
  }
  return kept
}

function buildAudit({ file, fileKey, selected, pages, collector, options }) {
  return {
    meta: {
      file: file.name,
      fileKey,
      lastModified: file.lastModified,
      version: file.version,
      extractedAt: new Date().toISOString(),
      pagesInFile: pages.map((page) => page.name),
      pagesAudited: selected.map((page) => page.name),
      rootWidthFilter: options.rootWidths.length ? options.rootWidths : null,
      stats: collector.stats,
    },
    colors: collector.colors.toJSON(),
    typography: collector.typography.toJSON(),
    spacing: {
      padding: collector.padding.toJSON(),
      gap: collector.gap.toJSON(),
      gapVertical: collector.gapVertical.toJSON(),
      gapHorizontal: collector.gapHorizontal.toJSON(),
      insets: collector.insets.toJSON(),
    },
    radii: collector.radii.toJSON(),
    pillRadii: collector.pillRadii.toJSON(),
    strokeWeights: collector.strokeWeights.toJSON(),
    shadows: collector.shadows.toJSON(),
    frameWidths: collector.frameWidths.toJSON(),
    frameHeights: collector.frameHeights.toJSON(),
    errors: collector.errors,
  }
}

function report(audit, collector, out) {
  const { stats } = audit.meta
  const spacingValues = new Set([
    ...audit.spacing.padding.map((entry) => entry.value),
    ...audit.spacing.gap.map((entry) => entry.value),
  ])

  console.log(`\nfile: ${audit.meta.file} (modified ${audit.meta.lastModified})`)
  console.log(`pages audited: ${audit.meta.pagesAudited.join(', ') || '(none)'}`)
  console.log(`nodes: ${stats.nodesVisited} visited, ${stats.nodesHidden} skipped as hidden\n`)

  const rows = [
    ['colors (hex+alpha)', collector.colors.size, collector.colors.total],
    ['type combinations', collector.typography.size, collector.typography.total],
    ['font sizes', new Set(audit.typography.map((entry) => entry.fontSize)).size, ''],
    ['spacing values', spacingValues.size, collector.padding.total + collector.gap.total],
    ['  padding', collector.padding.size, collector.padding.total],
    ['  gap (itemSpacing)', collector.gap.size, collector.gap.total],
    ['measured gap, vertical', collector.gapVertical.size, collector.gapVertical.total],
    ['measured gap, horizontal', collector.gapHorizontal.size, collector.gapHorizontal.total],
    ['measured container insets', collector.insets.size, collector.insets.total],
    ['corner radii', collector.radii.size, collector.radii.total],
    ['pill radii (-> rounded-full)', collector.pillRadii.size, collector.pillRadii.total],
    ['stroke weights', collector.strokeWeights.size, collector.strokeWeights.total],
    ['shadows', collector.shadows.size, collector.shadows.total],
    ['top-level frame widths', collector.frameWidths.size, collector.frameWidths.total],
  ]
  console.log('  unique  uses   category')
  for (const [label, unique, total] of rows) {
    console.log(`  ${String(unique).padStart(6)}  ${String(total).padStart(5)}  ${label}`)
  }

  console.log(`\ntext nodes: ${stats.textNodes}, inline style overrides: ${stats.textOverrides}`)
  console.log(`gradient fills: ${stats.gradientFills}, image fills: ${stats.imageFills}`)
  console.log(`zero padding sides: ${stats.zeroPadding}, zero gaps: ${stats.zeroGap}`)
  console.log(
    `measured zero distances: ${stats.zeroGeometry}, ` +
      `off-pixel by >0.25px: ${stats.fractionalGeometry}`,
  )

  if (audit.errors.length) {
    console.log(`\n${audit.errors.length} node(s) could not be read:`)
    for (const error of audit.errors.slice(0, 20)) {
      console.log(`  ${error.type} "${error.name}" (${error.path}) — ${error.reason}`)
    }
    if (audit.errors.length > 20) console.log(`  ... ${audit.errors.length - 20} more, see ${out}`)
  }
  console.log(`\nwritten: ${out}`)
}
