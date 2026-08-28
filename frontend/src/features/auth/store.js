import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as authApi from '@/features/auth/api'
import { configureAuth, setAccessToken } from '@/core/api/client'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const isReady = ref(false)
  let restoring = null
  const isAuthenticated = computed(() => user.value !== null)

  /** Hold the token in memory only; a reload restores the session from the cookie instead. */
  function adopt(session) {
    user.value = session.user
    setAccessToken(session.access_token)
    return session
  }

  function forget() {
    user.value = null
    setAccessToken(null)
  }

  async function register(payload) {
    return adopt(await authApi.register(payload))
  }

  async function signIn(payload) {
    return adopt(await authApi.login(payload))
  }

  async function signOut() {
    try {
      await authApi.logout()
    } finally {
      forget()
    }
  }

  /**
   * Restore a session on page load.
   *
   * A failure here is the normal case for a visitor who is not signed in, so it is not an
   * error state — it just means the app starts anonymous.
   */
  async function restore() {
    // Cached, so a route guard and a component asking at the same time produce one request.
    restoring ??= (async () => {
      try {
        adopt(await authApi.refresh())
      } catch {
        forget()
      } finally {
        isReady.value = true
      }
    })()
    return restoring
  }

  configureAuth({
    refresh: async () => {
      try {
        return adopt(await authApi.refresh()).access_token
      } catch {
        forget()
        return null
      }
    },
    sessionLost: forget,
  })

  return { user, isReady, isAuthenticated, register, signIn, signOut, restore }
})
