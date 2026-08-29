// Money arrives from the API in minor units and never as a float; the same rule as on the
// backend, and the reason the conversion lives in one place instead of in every template.
const CURRENCY_LABELS = {
  KGS: 'сом',
}

const HOUR_FORMS = ['час', 'часа', 'часов']
const REVIEW_FORMS = ['отзыв', 'отзыва', 'отзывов']

/**
 * Русское склонение после числа: 1 час, 72 часа, 5 часов.
 *
 * Правило одно на весь интерфейс и живёт здесь, а не в шаблоне: «72 час» на странице
 * читается как ошибка в данных, а не в вёрстке.
 */
function plural(count, forms) {
  const teens = Math.abs(count) % 100
  const last = teens % 10
  if (teens > 10 && teens < 20) return forms[2]
  if (last === 1) return forms[0]
  if (last >= 2 && last <= 4) return forms[1]
  return forms[2]
}

/**
 * Цена курса как её видит студент: «9 000 сом».
 *
 * Копейки не показываем: у всех цен каталога они нулевые, а «9 000,00 сом» на карточке
 * читается как цена с точностью до копейки там, где её нет.
 */
export function formatPrice(minor, currency = 'KGS') {
  const major = Math.round(minor / 100)
  return `${major.toLocaleString('ru-RU')} ${CURRENCY_LABELS[currency] ?? currency}`
}

/** Длительность обучения: «72 часа». */
export function formatHours(hours) {
  return `${hours} ${plural(hours, HOUR_FORMS)}`
}

/** Счётчик под оценкой: «69 отзывов». */
export function formatReviews(count) {
  return `${count} ${plural(count, REVIEW_FORMS)}`
}

/** Дата отзыва по-русски: «21 августа 2022». Без «г.» — в макете его нет. */
export function formatDate(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date
    .toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
    .replace(/\s*г\.$/, '')
}
