// OKLab conversions after Björn Ottosson. Perceptual distance is the whole point:
// #bebebe and #c0c0c0 are two hex strings and one colour.

export function hexToRgb(hex) {
  const clean = hex.replace('#', '')
  return {
    r: parseInt(clean.slice(0, 2), 16) / 255,
    g: parseInt(clean.slice(2, 4), 16) / 255,
    b: parseInt(clean.slice(4, 6), 16) / 255,
  }
}

export function rgbToHex({ r, g, b }) {
  const channel = (value) =>
    Math.round(Math.min(1, Math.max(0, value)) * 255)
      .toString(16)
      .padStart(2, '0')
  return `#${channel(r)}${channel(g)}${channel(b)}`
}

function toLinear(value) {
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
}

function fromLinear(value) {
  return value <= 0.0031308 ? value * 12.92 : 1.055 * value ** (1 / 2.4) - 0.055
}

export function hexToOklab(hex) {
  const { r, g, b } = hexToRgb(hex)
  const lr = toLinear(r)
  const lg = toLinear(g)
  const lb = toLinear(b)

  const l = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb)
  const m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb)
  const s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb)

  return {
    L: 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    a: 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    b: 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  }
}

export function oklabToRgb({ L, a, b }) {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3

  return {
    r: fromLinear(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
    g: fromLinear(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
    b: fromLinear(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s),
  }
}

export function toPolar({ L, a, b }) {
  return {
    L,
    chroma: Math.hypot(a, b),
    hue: (Math.atan2(b, a) * 180) / Math.PI,
  }
}

export function fromPolar({ L, chroma, hue }) {
  const radians = (hue * Math.PI) / 180
  return { L, a: chroma * Math.cos(radians), b: chroma * Math.sin(radians) }
}

/** Euclidean distance in OKLab — close enough to CIEDE2000 for palette work. */
export function deltaE(first, second) {
  return Math.hypot(first.L - second.L, first.a - second.a, first.b - second.b)
}

/** Lower chroma until the colour fits in sRGB, so generated ramp steps stay real. */
export function toGamutHex(polar) {
  let chroma = polar.chroma
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const rgb = oklabToRgb(fromPolar({ ...polar, chroma }))
    const inGamut = [rgb.r, rgb.g, rgb.b].every((value) => value >= -0.001 && value <= 1.001)
    if (inGamut) return rgbToHex(rgb)
    chroma *= 0.92
  }
  return rgbToHex(oklabToRgb(fromPolar({ ...polar, chroma: 0 })))
}

export function contrastRatio(firstHex, secondHex) {
  const luminance = (hex) => {
    const { r, g, b } = hexToRgb(hex)
    return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b)
  }
  const first = luminance(firstHex)
  const second = luminance(secondHex)
  const lighter = Math.max(first, second)
  const darker = Math.min(first, second)
  return Math.round(((lighter + 0.05) / (darker + 0.05)) * 100) / 100
}
