#!/usr/bin/env node
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

const ROOT = resolve(import.meta.dirname, '../..')
const TOKENS = resolve(ROOT, 'tokens.json')
const OUT = resolve(ROOT, 'frontend/tailwind.config.js')

// Measured on page "profile": content column and the auth card, in 1440px frames.
const LAYOUT = { container: '1240px', gutter: '100px', card: '466px' }
// Invented in tokens.json, so it stays out of the config until a real one is picked.
const EXCLUDED_RAMPS = ['warning']

main()

function main() {
  const tokens = JSON.parse(readFileSync(TOKENS, 'utf8'))
  const palette = readPalette(tokens)
  const config = render(tokens, palette)
  mkdirSync(dirname(OUT), { recursive: true })
  writeFileSync(OUT, config)
  console.log(`written: ${OUT}`)
  console.log(
    `palette: ${Object.keys(palette).join(', ')}; ` +
      `excluded: ${EXCLUDED_RAMPS.join(', ') || 'none'}`,
  )
}

function readPalette(tokens) {
  const palette = {}
  for (const [group, value] of Object.entries(tokens.color)) {
    if (group.startsWith('$') || EXCLUDED_RAMPS.includes(group)) continue
    if (value.$value) {
      palette[group] = value.$value
      continue
    }
    const steps = Object.entries(value).filter(([step]) => /^\d+$/.test(step))
    if (steps.length === 0) continue
    palette[group] = Object.fromEntries(steps.map(([step, item]) => [step, item.$value]))
  }
  return palette
}

/** `{color.neutral.900}` -> `palette.neutral[900]`, so the config keeps one source. */
function reference(tokens, role, name) {
  const raw = tokens.color[role]?.[name]?.$value
  if (!raw?.startsWith('{')) return raw ? `'${raw}'` : null
  const path = raw.slice(1, -1).split('.').slice(1)
  if (EXCLUDED_RAMPS.includes(path[0])) return null
  return path.length === 1 ? `palette.${path[0]}` : `palette.${path[0]}[${path[1]}]`
}

function render(tokens, palette) {
  const fontSizes = Object.entries(tokens.fontSize)
    .filter(([name]) => !name.startsWith('$'))
    .map(([name, token]) => {
      const lineHeight = token.$extensions['app.caiame.lineHeight']
      return `      '${name}': ['${token.$value}', { lineHeight: '${lineHeight}', letterSpacing: '-0.03em' }],`
    })
    .join('\n')

  const scale = (group, quote = true) =>
    Object.entries(tokens[group])
      .filter(([name]) => !name.startsWith('$'))
      .map(([name, token]) => {
        const value = quote ? `'${token.$value}'` : token.$value
        return `      ${/^[a-z][a-zA-Z]*$/.test(name) ? name : `'${name}'`}: ${value},`
      })
      .join('\n')

  return `/**
 * GENERATED from tokens.json by \`node tools/design-tokens/tailwind.mjs\`.
 * Do not edit by hand: change tokens.json (or the extractor) and regenerate.
 *
 * Every scale below REPLACES the Tailwind default instead of extending it — a value
 * that is not in the mockup must not be reachable by accident. Arbitrary values
 * (\`p-[7px]\`, \`bg-[#123123]\`) are rejected by \`scripts/lint-design-tokens.mjs\`.
 */

/** @type {Record<string, string | Record<string, string>>} */
const palette = ${JSON.stringify(palette, null, 2).replace(/"([\w$]+)":/g, '$1:').replace(/"/g, "'")}

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    // Tailwind's own palette is gone on purpose: only these colours exist.
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      inherit: 'inherit',
      ...palette,
    },
    fontFamily: {
      sans: [${tokens.fontFamily.sans.$value.split(', ').map((part) => `'${part.replace(/'/g, '')}'`).join(', ')}],
    },
    fontSize: {
${fontSizes}
    },
    fontWeight: {
${scale('fontWeight', false)}
    },
    lineHeight: {
${scale('lineHeight', false)}
    },
    letterSpacing: {
${scale('letterSpacing')}
    },
    spacing: {
${scale('spacing')}
    },
    borderRadius: {
${scale('borderRadius')}
    },
    borderWidth: {
${scale('borderWidth')}
    },
    // Слоёв ровно два, и порядок между ними — решение, а не случайность: сообщение о том,
    // что сохранить не удалось, должно быть видно поверх окна, в котором сохраняли.
    zIndex: {
      auto: 'auto',
      base: '0',
      overlay: '40',
      notice: '50',
    },
    extend: {
      // Semantic roles. Names never collide with a ramp name, so \`text-muted\`
      // and \`text-neutral-500\` both keep working.
      textColor: {
        ink: ${reference(tokens, 'text', 'primary')},
        muted: ${reference(tokens, 'text', 'secondary')},
        subtle: ${reference(tokens, 'text', 'muted')},
        disabled: ${reference(tokens, 'text', 'disabled')},
        inverse: ${reference(tokens, 'text', 'inverse')},
        accent: ${reference(tokens, 'text', 'accent')},
      },
      backgroundColor: {
        page: ${reference(tokens, 'surface', 'page')},
        subtle: ${reference(tokens, 'surface', 'subtle')},
        accent: ${reference(tokens, 'surface', 'accent')},
        inverse: ${reference(tokens, 'surface', 'inverse')},
      },
      borderColor: {
        DEFAULT: ${reference(tokens, 'border', 'default')},
        subtle: ${reference(tokens, 'border', 'subtle')},
        accent: ${reference(tokens, 'border', 'accent')},
      },
      maxWidth: {
        container: '${LAYOUT.container}',
        card: '${LAYOUT.card}',
      },
      // Breakpoints stay at the Tailwind defaults: the file has exactly one
      // artboard width (1440px), so there is nothing to derive a ladder from.
    },
  },
  plugins: [],
}
`
}
