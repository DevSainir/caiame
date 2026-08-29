import { readdirSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'
import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import prettier from 'eslint-config-prettier'
import globals from 'globals'

const FEATURES_DIR = fileURLToPath(new URL('./src/features', import.meta.url))

/**
 * Области читаются с диска, а не перечисляются руками: новая папка в features/ сразу
 * получает свои границы, и никто не вспоминает про конфиг спустя неделю.
 */
const features = readdirSync(FEATURES_DIR, { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)

/** Запрет лезть во внутренности всех областей, кроме своей собственной. */
const foreignInternals = (self) =>
  features
    .filter((name) => name !== self)
    .flatMap((name) => [`@/features/${name}/views/*`, `@/features/${name}/components/*`])

export default [
  // Шаблоны files здесь считаются от каталога запуска, а не от конфига, поэтому
  // eslint обязан запускаться из frontend/. Хук pre-commit это и делает: запуск из
  // корня репозитория молча выключил бы все правила границ.
  { ignores: ['dist/**', 'node_modules/**', 'scripts/fixtures/**'] },

  js.configs.recommended,
  ...vue.configs['flat/recommended'],
  prettier,

  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.es2024 },
    },
    rules: {
      // Родительские относительные пути не переживают перенос файла и прячут,
      // из какого слоя пришёл импорт. Алиас @/ виден сразу.
      'no-restricted-imports': ['error', { patterns: ['../*', '../../*'] }],
    },
  },

  {
    // Вью переваливший за 250 строк — всегда смесь загрузки данных, бизнес-правил
    // и разметки. Считаем только сам файл, комментарии и пустые строки не в счёт.
    files: ['**/*.vue'],
    rules: {
      'max-lines': ['error', { max: 250, skipBlankLines: true, skipComments: true }],
    },
  },

  {
    // core/ — инфраструктура, она не знает про предметные области.
    files: ['src/core/**/*.{js,vue}'],
    ignores: ['src/core/router/**'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['../*', '../../*'],
              message: 'Используй алиас @/ вместо родительских путей.',
            },
            {
              group: ['@/features/*'],
              message:
                'core/ не знает про домен. Исключение — только главный роутер, собирающий ' +
                'массивы роутов. Понадобилось общее — оно переезжает в core/.',
            },
          ],
        },
      ],
    },
  },

  ...features.map((feature) => ({
    // Соседняя область — закрытая территория: её api.js и стор брать можно,
    // views/ и components/ нельзя. Понадобился общий компонент — он едет в core/.
    files: [`src/features/${feature}/**/*.{js,vue}`],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['../*', '../../*'],
              message: 'Используй алиас @/ вместо родительских путей.',
            },
            {
              group: foreignInternals(feature),
              message:
                'Внутренности чужой области закрыты. Её api.js и стор — можно, ' +
                'views/ и components/ — нет.',
            },
          ],
        },
      ],
    },
  })),

  {
    files: ['**/*.spec.js'],
    languageOptions: { globals: { ...globals.node } },
    rules: { 'max-lines': 'off' },
  },

  {
    files: ['*.config.js', 'scripts/**/*.mjs'],
    languageOptions: { globals: { ...globals.node } },
    rules: { 'no-restricted-imports': 'off' },
  },
]
