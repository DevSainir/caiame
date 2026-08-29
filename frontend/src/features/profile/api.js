import client from '@/core/api/client'

/** Изменить отображаемое имя своего аккаунта. */
export async function updateProfile(payload) {
  const { data } = await client.patch('/users/me', payload)
  return data
}
