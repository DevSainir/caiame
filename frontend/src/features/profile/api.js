import client from '@/core/api/client'

/** Изменить отображаемое имя своего аккаунта. */
export async function updateProfile(payload) {
  const { data } = await client.patch('/users/me', payload)
  return data
}

/** Курсы, которые студент уже начал, с процентом на момент запроса. */
export async function fetchMyCourses() {
  const { data } = await client.get('/users/me/courses')
  return data
}
