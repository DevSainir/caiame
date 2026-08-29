#!/usr/bin/env node
// The design system is only as strong as the check that enforces it.
// A value that is not in tailwind.config.js must not reach the page.
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { extname, join, relative, resolve } from 'node:path'

const ROOT = resolve(import.meta.dirname, '..')
const SOURCES = [resolve(ROOT, 'src'), resolve(ROOT, 'index.html')]
const EXTENSIONS = new Set(['.vue', '.js', '.ts', '.html'])

const ARBITRARY = /(?:^|[\s"'`:{])(-?[a-z][a-z0-9]*(?:-[a-z0-9]+)*)-\[([^\]]*)\]/g
const INLINE_STYLE = /\bstyle\s*=\s*(?:"([^"]*)"|'([^']*)')/g
const HEX = /#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3}(?:[0-9a-fA-F]{2})?)?\b/g
const COLOR_UTILITY =
  /(?:^|[\s"'`:])(bg|text|border|ring|fill|stroke|divide|outline|decoration|shadow|from|via|to)-([a-z][a-z0-9-]*)/g

// Keywords these prefixes accept that are not colours at all.
const NON_COLOR = new Set([
  'left',
  'right',
  'center',
  'justify',
  'start',
  'end',
  'top',
  'bottom',
  'middle',
  'balance',
  'pretty',
  'wrap',
  'nowrap',
  'ellipsis',
  'clip',
  'auto',
  'none',
  'full',
  'solid',
  'dashed',
  'dotted',
  'double',
  'hidden',
  'collapse',
  'separate',
  'fixed',
  'cover',
  'contain',
  'repeat',
  'no',
  'local',
  'scroll',
  'origin',
  'clone',
  'slice',
  'transparent',
  'current',
  'inherit',
  'x',
  'y',
  'opacity',
  'offset',
  'width',
  'size',
  'inset',
  'sm',
  'md',
  'lg',
  'xl',
  'xs',
  'base',
  'wide',
  'wider',
  'tighter',
  'gradient',
])

main()

const SELF_TEST = resolve(import.meta.dirname, 'fixtures/violations.vue.txt')
const SELF_TEST_EXPECTED = 5

async function main() {
  const config = (await import(resolve(ROOT, 'tailwind.config.js'))).default
  const colors = collectColorNames(config)
  if (process.argv.includes('--self-test')) return selfTest(colors)
  const files = SOURCES.flatMap(collectFiles)
  const problems = files.flatMap((file) => lintFile(file, colors))

  if (files.length === 0) {
    console.log('lint-design-tokens: no source files yet, nothing to check')
    return
  }
  for (const problem of problems) {
    console.error(`${problem.file}:${problem.line}  ${problem.rule}  ${problem.message}`)
  }
  console.log(
    `\nlint-design-tokens: ${files.length} file(s), ${problems.length} problem(s), ` +
      `${colors.size} colour name(s) in the theme`,
  )
  if (problems.length > 0) {
    console.error('\nA value outside the scale means the token is missing, not that the rule is.')
    console.error('Stop and agree on the token instead of inlining the value.')
    process.exit(1)
  }
}

/** Proves the gate still catches what it was written to catch. */
function selfTest(colors) {
  const problems = lintFile(SELF_TEST, colors)
  for (const problem of problems) console.log(`  caught ${problem.rule}: ${problem.message}`)
  if (problems.length !== SELF_TEST_EXPECTED) {
    console.error(
      `self-test FAILED: expected ${SELF_TEST_EXPECTED} problems in the fixture, got ${problems.length}`,
    )
    process.exit(1)
  }
  console.log(`self-test ok: ${problems.length} planted problems found`)
}

function collectColorNames(config) {
  const names = new Set()
  const add = (group) => {
    for (const [name, value] of Object.entries(group ?? {})) {
      names.add(name)
      if (value && typeof value === 'object') {
        for (const step of Object.keys(value)) names.add(`${name}-${step}`)
      }
    }
  }
  add(config.theme?.colors)
  for (const key of ['textColor', 'backgroundColor', 'borderColor'])
    add(config.theme?.extend?.[key])
  return names
}

function collectFiles(path) {
  let stats
  try {
    stats = statSync(path)
  } catch {
    return []
  }
  if (stats.isFile()) return EXTENSIONS.has(extname(path)) ? [path] : []
  return readdirSync(path).flatMap((entry) => collectFiles(join(path, entry)))
}

function lintFile(file, colors) {
  const source = readFileSync(file, 'utf8')
  const name = relative(ROOT, file)
  const problems = []

  source.split('\n').forEach((text, index) => {
    const line = index + 1
    const report = (rule, message) => problems.push({ file: name, line, rule, message })

    for (const [, prefix, value] of text.matchAll(ARBITRARY)) {
      report('arbitrary-value', `\`${prefix}-[${value}]\` — no arbitrary values, use a token`)
    }
    for (const [, doubleQuoted, singleQuoted] of text.matchAll(INLINE_STYLE)) {
      const value = doubleQuoted ?? singleQuoted ?? ''
      if (/\d\s*px|#[0-9a-fA-F]{3}|rgba?\(/.test(value)) {
        report(
          'inline-style',
          `\`style="${value.slice(0, 40)}"\` — hard-coded value in a style attribute`,
        )
      }
    }
    for (const [hex] of text.matchAll(HEX)) {
      report('raw-color', `\`${hex}\` — colours live in tailwind.config.js only`)
    }
    for (const [, prefix, suffix] of text.matchAll(COLOR_UTILITY)) {
      const head = suffix.split('-')[0]
      if (NON_COLOR.has(head) || NON_COLOR.has(suffix)) continue
      if (colors.has(suffix) || colors.has(head)) continue
      report(
        'unknown-color',
        `\`${prefix}-${suffix}\` — not in the theme, this class renders nothing`,
      )
    }
  })
  return problems
}
