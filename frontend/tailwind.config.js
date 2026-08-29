/**
 * GENERATED from tokens.json by `node tools/design-tokens/tailwind.mjs`.
 * Do not edit by hand: change tokens.json (or the extractor) and regenerate.
 *
 * Every scale below REPLACES the Tailwind default instead of extending it — a value
 * that is not in the mockup must not be reachable by accident. Arbitrary values
 * (`p-[7px]`, `bg-[#123123]`) are rejected by `scripts/lint-design-tokens.mjs`.
 */

/** @type {Record<string, string | Record<string, string>>} */
const palette = {
  white: '#ffffff',
  primary: {
    50: '#eff6ff',
    100: '#cbdefd',
    200: '#a4c7fe',
    300: '#7faefc',
    400: '#5495fe',
    500: '#2178ff',
    600: '#0362e4',
    700: '#0d52b9',
    800: '#084095',
    900: '#042f72',
    950: '#002051'
  },
  neutral: {
    50: '#f3f7fa',
    100: '#e7e7e7',
    200: '#d9d9d9',
    300: '#cbcbcb',
    400: '#bebebe',
    500: '#999999',
    600: '#838383',
    700: '#6a6a6a',
    800: '#535353',
    900: '#3c3c3c',
    950: '#262626'
  },
  success: {
    50: '#eef9e8',
    100: '#d7eccd',
    200: '#bce2aa',
    300: '#9ed87f',
    400: '#7dcd4d',
    500: '#61c000',
    600: '#539f18',
    700: '#3f8000',
    800: '#31620b',
    900: '#204601',
    950: '#112c00'
  },
  danger: {
    50: '#fff2f0',
    100: '#fed7d3',
    200: '#febab3',
    300: '#fb9d95',
    400: '#fb7c74',
    500: '#ff4a4a',
    600: '#df2c33',
    700: '#ba1a24',
    800: '#930e19',
    900: '#6e040e',
    950: '#490307'
  }
}

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
      sans: ['Manrope', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
    },
    fontSize: {
      '2xs': ['10px', { lineHeight: '1.5', letterSpacing: '-0.03em' }],
      'xs': ['12px', { lineHeight: '1.5', letterSpacing: '-0.03em' }],
      'sm': ['14px', { lineHeight: '1.6', letterSpacing: '-0.03em' }],
      'base': ['16px', { lineHeight: '1.6', letterSpacing: '-0.03em' }],
      'lg': ['18px', { lineHeight: '1.6', letterSpacing: '-0.03em' }],
      'xl': ['20px', { lineHeight: '1.6', letterSpacing: '-0.03em' }],
      '2xl': ['24px', { lineHeight: '1.3', letterSpacing: '-0.03em' }],
      '3xl': ['28px', { lineHeight: '1.3', letterSpacing: '-0.03em' }],
      '4xl': ['32px', { lineHeight: '1.3', letterSpacing: '-0.03em' }],
      '5xl': ['38px', { lineHeight: '1.3', letterSpacing: '-0.03em' }],
    },
    fontWeight: {
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.3,
      snug: 1.5,
      normal: 1.6,
      relaxed: 1.8,
    },
    letterSpacing: {
      tight: '-0.03em',
      normal: '0em',
    },
    spacing: {
      '0': '0px',
      '2': '8px',
      '3': '12px',
      '4': '16px',
      '5': '20px',
      '6': '24px',
      '7': '28px',
      '8': '32px',
      '10': '40px',
      '12': '48px',
      '14': '56px',
      '15': '60px',
      '18': '72px',
      '20': '80px',
      '24': '96px',
      '25': '100px',
      '28': '112px',
      '35': '140px',
      '0.25': '1px',
      '3.5': '14px',
    },
    borderRadius: {
      none: '0px',
      xs: '2px',
      sm: '4px',
      md: '8px',
      lg: '12px',
      xl: '20px',
      full: '9999px',
    },
    borderWidth: {
      '0': '0px',
      '2': '2px',
      'DEFAULT': '1px',
    },
    extend: {
      // Semantic roles. Names never collide with a ramp name, so `text-muted`
      // and `text-neutral-500` both keep working.
      textColor: {
        ink: palette.neutral[900],
        muted: palette.neutral[700],
        subtle: palette.neutral[600],
        disabled: palette.neutral[400],
        inverse: palette.white,
        accent: palette.primary[600],
      },
      backgroundColor: {
        page: palette.white,
        subtle: palette.neutral[50],
        accent: palette.primary[500],
        inverse: palette.primary[950],
      },
      borderColor: {
        DEFAULT: palette.neutral[400],
        subtle: palette.neutral[100],
        accent: palette.primary[500],
      },
      maxWidth: {
        container: '1240px',
        card: '466px',
      },
      // Breakpoints stay at the Tailwind defaults: the file has exactly one
      // artboard width (1440px), so there is nothing to derive a ladder from.
    },
  },
  plugins: [],
}
