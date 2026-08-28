import { readFileSync } from 'node:fs'

/** Minimal .env reader: no deps, no interpolation, last definition wins. */
export function loadEnv(path) {
  let raw
  try {
    raw = readFileSync(path, 'utf8')
  } catch (error) {
    throw new Error(`cannot read ${path}: ${error.message}`)
  }
  const env = {}
  for (const line of raw.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq === -1) continue
    const key = trimmed.slice(0, eq).trim()
    let value = trimmed.slice(eq + 1).trim()
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1)
    }
    env[key] = value
  }
  return env
}
