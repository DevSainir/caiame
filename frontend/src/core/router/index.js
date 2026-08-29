import { createRouter, createWebHistory } from 'vue-router'
import authRoutes from '@/features/auth/routes'
import homeRoutes from '@/features/home/routes'
import { useAuthStore } from '@/core/session/store'

// Screens that are drawn but not built yet. Each one moves into its own feature as soon as
// that feature exists; until then the links must not break the app.
const stubRoutes = ['/courses', '/courses/:slug', '/profile', '/support'].map((path) => ({
  path,
  name: path.slice(1),
  component: () => import('@/core/views/StubView.vue'),
}))

const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...homeRoutes,
    ...authRoutes,
    ...stubRoutes,
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
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
  return true
})

export default router
