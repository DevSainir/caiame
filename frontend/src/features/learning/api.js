import client from '@/core/api/client'

/** Один модуль с его лекциями и прогрессом того, кто спрашивает. */
export async function fetchModule(id) {
  const { data } = await client.get(`/modules/${id}`)
  return data
}

/** Одна лекция: видео или файл. Гостю отвечают 401 — материал за сессией. */
export async function fetchLesson(id) {
  const { data } = await client.get(`/lessons/${id}`)
  return data
}

/** Отметить лекцию пройденной. Повтор ничего не меняет и не сдвигает дату. */
export async function completeLesson(id) {
  const { data } = await client.post(`/lessons/${id}/completion`)
  return data
}

/** Тест без ключа к ответам: правильных вариантов в ответе сервера нет. */
export async function fetchTest(unitId) {
  const { data } = await client.get(`/tests/${unitId}`)
  return data
}

/** Отправить попытку. Оценивает сервер: балл с клиента не принимается. */
export async function submitTest(unitId, answers) {
  const { data } = await client.post(`/tests/${unitId}/attempts`, { answers })
  return data
}
