import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as authApi from '@/core/session/api'
import { configureAuth, refreshOnce, setAccessToken } from '@/core/api/client'
import { hasSessionHint } from '@/core/session/session-hint'

/**
 * Состояние сессии.
 *
 * Живёт в core/, а не в features/auth, потому что о вошедшем пользователе спрашивают
 * три инфраструктурных места — HTTP-клиент, охранник роутера и шапка — и только одно
 * доменное: экраны входа. Область auth осталась тем, чем и должна быть: роуты, вью,
 * валидация и расшифровка отказов.
 */
export const useAuthStore = defineStore('session', () => {
  const user = ref(null)
  const isReady = ref(false)
  const isAuthenticated = computed(() => user.value !== null)

  /** Hold the token in memory only; a reload restores the session from the cookie instead. */
  function adopt(session) {
    user.value = session.user
    setAccessToken(session.access_token)
    return session
  }

  /** Обновить сведения о вошедшем пользователе, не трогая токен. */
  function applyUser(next) {
    user.value = next
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

  /**
   * Выход из аккаунта.
   *
   * Локальное состояние очищается только после того, как сервер подтвердил выход.
   * Забыть пользователя раньше — значит соврать: refresh-токен живёт в cookie, которую
   * страница не видит и не может стереть, поэтому перезагрузка вернула бы сессию.
   * На общем компьютере это ровно тот исход, ради которого нажимают «Выйти».
   */
  async function signOut() {
    await authApi.logout()
    forget()
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

  return { user, isReady, isAuthenticated, applyUser, register, signIn, signOut, restore }
})
