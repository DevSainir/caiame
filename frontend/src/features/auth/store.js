import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as authApi from '@/features/auth/api'
import { configureAuth, refreshOnce, setAccessToken } from '@/core/api/client'
import { hasSessionHint } from '@/features/auth/session-hint'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const isReady = ref(false)
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
   * Two things guard this call, and both matter. A visitor without the session hint never
   * asks at all — no wasted round-trip and no 401 in everyone's console. And the request
   * itself goes through the shared queue, because two simultaneous refreshes would send the
   * same cookie twice, the second one already rotated, and the backend would read that as a
   * stolen token and end the session.
   */
  async function restore() {
    if (!hasSessionHint()) {
      isReady.value = true
      return
    }
    await refreshOnce()
    isReady.value = true
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
