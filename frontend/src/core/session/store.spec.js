import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/core/session/api', () => ({
  register: vi.fn(),
  login: vi.fn(),
  refresh: vi.fn(),
  logout: vi.fn(),
}))

const { setAccessToken } = vi.hoisted(() => ({ setAccessToken: vi.fn() }))
vi.mock('@/core/api/client', () => ({
  setAccessToken,
  refreshOnce: vi.fn(),
  configureAuth: vi.fn(),
  default: {},
}))

const authApi = await import('@/core/session/api')
const { useAuthStore } = await import('@/core/session/store')

describe('выход из аккаунта', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('забывает пользователя и токен', async () => {
    const auth = useAuthStore()
    authApi.login.mockResolvedValue({ access_token: 'token', user: { email: 'a@b.c' } })
    await auth.signIn({ email: 'a@b.c', password: 'correct-horse-battery' })

    await auth.signOut()

    expect(auth.isAuthenticated).toBe(false)
    expect(auth.user).toBeNull()
    expect(setAccessToken).toHaveBeenLastCalledWith(null)
  })

  it('не считает выход состоявшимся, если сервер его не подтвердил', async () => {
    const auth = useAuthStore()
    authApi.login.mockResolvedValue({ access_token: 'token', user: { email: 'a@b.c' } })
    await auth.signIn({ email: 'a@b.c', password: 'correct-horse-battery' })
    authApi.logout.mockRejectedValue({ status: 500 })

    await expect(auth.signOut()).rejects.toBeTruthy()

    // Забыть пользователя здесь — соврать ему: refresh-токен остался в cookie, которую
    // страница не видит, и перезагрузка вернула бы сессию. На общем компьютере это ровно
    // тот исход, ради которого нажимают «Выйти».
    expect(auth.isAuthenticated).toBe(true)
  })
})
