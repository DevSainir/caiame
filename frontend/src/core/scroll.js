import { useRoute, useRouter } from 'vue-router'

const DURATION_MS = 420

/**
 * easeInOutQuad: трогается и останавливается мягко, середину проходит быстро.
 *
 * Экспортируется ради теста: кривая обязана начинаться в нуле и заканчиваться единицей,
 * иначе прокрутка не доедет до цели или проскочит её.
 */
export function ease(progress) {
  return progress < 0.5 ? 2 * progress * progress : 1 - (-2 * progress + 2) ** 2 / 2
}

/**
 * Плавно прокрутить окно до этой позиции.
 *
 * Своя анимация, а не `window.scrollTo({ behavior: 'smooth' })`: этот режим выполняют не
 * все движки — встроенный браузер панели предпросмотра молча не делает ничего, и ссылка
 * перестаёт работать вовсе.
 */
function animateScrollTo(to) {
  const from = window.scrollY
  if (to === from) return

  // Прыжком, а не анимацией: в скрытой вкладке requestAnimationFrame не тикает — там
  // анимация всё равно никому не видна, а ссылка обязана работать. Системная просьба
  // убрать анимации значит ровно то же самое.
  if (document.hidden || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    window.scrollTo(0, to)
    return
  }

  const started = performance.now()
  const step = (now) => {
    const progress = Math.min(1, (now - started) / DURATION_MS)
    window.scrollTo(0, Math.round(from + (to - from) * ease(progress)))
    if (progress < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

/** Прокрутить к элементу с этим id. Нет такого элемента — ничего не делаем. */
export function scrollToAnchor(id) {
  const element = document.getElementById(id)
  if (!element) return
  animateScrollTo(Math.max(0, Math.round(window.scrollY + element.getBoundingClientRect().top)))
}

/** Прокрутить к началу страницы — так ведёт себя логотип на уже открытой главной. */
export function scrollToTop() {
  animateScrollTo(0)
}

/**
 * Переход на страницу с якорем — без решётки в адресе.
 *
 * Каталог живёт секцией главной, а не отдельной страницей, поэтому «Изучить курсы» — это
 * прокрутка, а не адрес. Ссылка при этом остаётся ссылкой: `href` на месте, и клик с Ctrl,
 * Cmd или средней кнопкой отдаётся браузеру, чтобы открылась новая вкладка.
 */
export function useAnchorNavigation() {
  const router = useRouter()
  const route = useRoute()

  return async function navigateToAnchor(event, { to = '/', anchor }) {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return
    event.preventDefault()
    if (route.path === to) {
      scrollToAnchor(anchor)
      return
    }
    // Якорь едет в состоянии перехода, а прокрутку делает `scrollBehavior` роутера. Сделать
    // её здесь нельзя: роутер прокручивает страницу сам уже после `push`, и наша прокрутка
    // была бы тут же отменена его же «в начало страницы».
    await router.push({ path: to, state: { anchor } })
  }
}
