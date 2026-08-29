import { createRouter, createWebHistory } from 'vue-router'
import authRoutes from '@/features/auth/routes'
import catalogRoutes from '@/features/catalog/routes'
import profileRoutes from '@/features/profile/routes'
import homeRoutes from '@/features/home/routes'
import { scrollToAnchor } from '@/core/scroll'
import { useAuthStore } from '@/core/session/store'

// Screens that are drawn but not built yet. Each one moves into its own feature as soon as
// that feature exists; until then the links must not break the app.
const stubRoutes = ['/support'].map((path) => ({
  path,
  name: path.slice(1),
  component: () => import('@/core/views/StubView.vue'),
}))

const RESTORE_TIMEOUT_MS = 1500
const RESTORE_STEP_MS = 50

/**
 * Дождаться, пока страница станет достаточно высокой для сохранённой позиции.
 *
 * Содержимое приходит запросом уже после перехода: в момент восстановления страница ещё
 * показывает «Загружаем курс…» и прокручивать её некуда. Ждём роста высоты, но не дольше
 * полутора секунд — если данные не пришли, лучше открыть страницу сверху, чем висеть.
 */
function waitForHeight(position) {
  return new Promise((resolve) => {
    const deadline = Date.now() + RESTORE_TIMEOUT_MS
    const check = () => {
      const reachable = document.documentElement.scrollHeight >= position.top + window.innerHeight
      if (reachable || Date.now() > deadline) resolve(position)
      else setTimeout(check, RESTORE_STEP_MS)
    }
    check()
  })
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...homeRoutes,
    ...authRoutes,
    ...catalogRoutes,
    ...profileRoutes,
    ...stubRoutes,
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  /**
   * There is no catalogue page in the design: «Изучить курсы» is an anchor to the listing
   * on the main page. The target rides in the navigation state rather than in a hash, so
   * the address stays clean, and an old link with `#courses` still works.
   *
   * The scroll itself is ours (see `core/scroll.js`) and the router is told `false`:
   * anything it returned would fight the animation and win.
   */
  scrollBehavior: (to, from, savedPosition) => {
    const anchor = to.hash ? to.hash.slice(1) : window.history.state?.anchor
    if (anchor) {
      // Якорь съедается сразу: он относится к одному переходу, а не к адресу. Оставленный
      // в состоянии, он уводил бы вниз при каждой перезагрузке этой же страницы.
      window.history.replaceState({ ...window.history.state, anchor: null }, '')
      scrollToAnchor(anchor)
      return false
    }
    // Возврат назад и перезагрузка оставляют человека там, где он был; новый переход
    // открывается сверху.
    return savedPosition ? waitForHeight(savedPosition) : { top: 0 }
  },
})

/**
 * Keep a signed-in visitor out of the sign-up screen.
 *
 * This is convenience, not protection: the real control is on the backend, and every route
 * hidden here still has to refuse on its own.
 */
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  // The first navigation restores the session from the refresh cookie. Doing it here rather
  // than before mount keeps first paint off the network round-trip.
  if (!auth.isReady) await auth.restore()
  if (to.meta.guestOnly && auth.isAuthenticated) return { path: '/' }
  if (to.meta.requiresAuth && !auth.isAuthenticated) return { path: '/login' }
  return true
})

/**
 * Запомнить позицию прокрутки перед уходом со страницы.
 *
 * `scrollBehavior` выключает восстановление прокрутки браузером, а сам роутер держит
 * позиции в памяти — перезагрузка их теряет. Без этой строки F5 всегда открывал бы
 * страницу сверху, хотя человек читал её середину.
 */
window.addEventListener('beforeunload', () => {
  const scroll = { left: window.scrollX, top: window.scrollY }
  window.history.replaceState({ ...window.history.state, scroll }, '')
})

export default router
