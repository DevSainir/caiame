import axios from 'axios'
import client from '@/core/api/client'

// Отдельный экземпляр без наших перехватчиков: файл уходит в хранилище, а не к нам, и
// заголовок авторизации там не нужен.
const plainClient = axios.create()

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

/**
 * Сообщить, сколько видео проиграли.
 *
 * Позиция — чтобы вернуться туда же в следующий раз, дельта — чтобы засчитать просмотр.
 * Сервер режет дельту по потолку, поэтому отправка чаще нужного ничего не ломает.
 */
export async function reportPlayback(id, { positionSec, deltaSec }) {
  const { data } = await client.post(`/lessons/${id}/playback`, {
    position_sec: Math.round(positionSec),
    delta_sec: Math.round(deltaSec),
  })
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

/** Задание с ручной проверкой: условие и все сдачи этого студента. */
export async function fetchAssignment(unitId) {
  const { data } = await client.get(`/assignments/${unitId}`)
  return data
}

/** Отправить работу очередной попыткой. */
export async function submitWork(unitId, payload) {
  const { data } = await client.post(`/assignments/${unitId}/submissions`, payload)
  return data
}

/**
 * Загрузить файл к работе.
 *
 * Тот же путь, что и у материалов лекций: сервер выдаёт разрешение ровно на этот файл,
 * браузер отправляет его прямо в хранилище. К работе файл прикрепляется отдельно — при
 * отправке, по идентификатору.
 */
export async function uploadAttachment(file, onProgress) {
  const { data: ticket } = await client.post('/attachments', {
    file_name: file.name,
    size_bytes: file.size,
  })
  await plainClient.put(ticket.url, file, {
    headers: { 'Content-Type': ticket.content_type },
    onUploadProgress: (event) => {
      if (onProgress && event.total) onProgress(Math.round((event.loaded * 100) / event.total))
    },
  })
  return { id: ticket.media_id, name: file.name, size_bytes: file.size }
}
