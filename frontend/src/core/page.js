// Заголовок вкладки и метка «не индексировать» — то немногое в голове документа, что
// зависит от открытой страницы.
//
// Ставится приложением, а не сервером: SPA отдаёт один и тот же index.html на все адреса,
// и общее описание сайта лежит там же статически. Заголовок же читается человеком в списке
// вкладок и в истории браузера, и «ЦАИДМО» на всех страницах подряд там бесполезен.

const SITE = 'ЦАИДМО'
const DEFAULT_TITLE = `${SITE} — Центрально-Азиатский Институт Дополнительного Медицинского Образования`

/** Заголовок страницы: «Название — ЦАИДМО», либо полное имя института на главной. */
export function pageTitle(title) {
  return title ? `${title} — ${SITE}` : DEFAULT_TITLE
}

/** Поставить заголовок вкладки. */
export function setPageTitle(title) {
  document.title = pageTitle(title)
}

/**
 * Закрыть страницу от поисковых роботов.
 *
 * Нужно там, где адрес существует, но в выдаче ему делать нечего: страница «такой страницы
 * нет» отвечает двумястами, потому что её рисует приложение, и без этой метки поисковик
 * считает её обычной страницей и показывает в результатах.
 */
export function setNoIndex(enabled) {
  const existing = document.querySelector('meta[name="robots"]')
  if (!enabled) {
    existing?.remove()
    return
  }
  const tag = existing ?? document.createElement('meta')
  tag.setAttribute('name', 'robots')
  tag.setAttribute('content', 'noindex')
  if (!existing) document.head.appendChild(tag)
}
