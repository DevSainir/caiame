import client from '@/core/api/client'

/** Create an account. The refresh token comes back as an HttpOnly cookie, not in the body. */
export async function register(payload) {
  const { data } = await client.post('/auth/register', payload)
  return data
}

/** Sign in with an address and a password. */
export async function login(payload) {
  const { data } = await client.post('/auth/login', payload)
  return data
}

/** Exchange the refresh cookie for a new pair. */
export async function refresh() {
  const { data } = await client.post('/auth/refresh')
  return data
}

/** End the session this browser holds. */
export async function logout() {
  await client.post('/auth/logout')
}

/**
 * Сменить пароль своей учётной записи.
 *
 * В ответ приходит новая сессия: смена пароля закрывает все сессии аккаунта, включая эту,
 * и без новой пары человек оказался бы выброшен собственным действием.
 */
export async function changePassword(payload) {
  const { data } = await client.put('/auth/password', payload)
  return data
}
