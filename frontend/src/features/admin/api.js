import axios from 'axios'
import client from '@/core/api/client'

/** Все курсы академии, включая черновики. Роль проверяет сервер, не эта функция. */
export async function fetchCourses() {
  const { data } = await client.get('/admin/courses')
  return data
}

/** Программа одного курса: модули с лекциями и работы. */
export async function fetchCourse(courseId) {
  const { data } = await client.get(`/admin/courses/${courseId}`)
  return data
}

/** Опубликовать курс или убрать из каталога. */
export async function setCourseStatus(courseId, status) {
  const { data } = await client.put(`/admin/courses/${courseId}/status`, { status })
  return data
}

/** Добавить модуль, задание или тестирование. */
export async function addUnit(courseId, payload) {
  const { data } = await client.post(`/admin/courses/${courseId}/units`, payload)
  return data
}

/** Переименовать строку программы. */
export async function updateUnit(courseId, unitId, payload) {
  const { data } = await client.put(`/admin/courses/${courseId}/units/${unitId}`, payload)
  return data
}

/** Переставить строку на шаг вверх или вниз. */
export async function moveUnit(courseId, unitId, direction) {
  await client.post(`/admin/courses/${courseId}/units/${unitId}/move`, { direction })
}

/** Удалить пустую строку программы. Модуль с лекциями сервер не отдаст удалить. */
export async function deleteUnit(courseId, unitId) {
  await client.delete(`/admin/courses/${courseId}/units/${unitId}`)
}

/** Добавить лекцию в модуль. */
export async function addLesson(courseId, unitId, payload) {
  const { data } = await client.post(`/admin/courses/${courseId}/units/${unitId}/lessons`, payload)
  return data
}

/** Изменить лекцию. */
export async function updateLesson(courseId, lessonId, payload) {
  const { data } = await client.put(`/admin/courses/${courseId}/lessons/${lessonId}`, payload)
  return data
}

/** Переставить лекцию внутри модуля. */
export async function moveLesson(courseId, lessonId, direction) {
  await client.post(`/admin/courses/${courseId}/lessons/${lessonId}/move`, { direction })
}

/** Убрать лекцию из программы. Мягко: история тех, кто её прошёл, остаётся. */
export async function deleteLesson(courseId, lessonId) {
  await client.delete(`/admin/courses/${courseId}/lessons/${lessonId}`)
}

/** Завести новый курс. Он создаётся черновиком и в каталоге не появляется. */
export async function createCourse(payload) {
  const { data } = await client.post('/admin/courses', payload)
  return data
}

/** Карточка курса: название, описание, часы, цена. */
export async function fetchCourseCard(courseId) {
  const { data } = await client.get(`/admin/courses/${courseId}/card`)
  return data
}

/** Сохранить карточку курса. Адрес курса при этом не меняется. */
export async function updateCourse(courseId, payload) {
  const { data } = await client.put(`/admin/courses/${courseId}`, payload)
  return data
}

/** Удалить курс. Сервер разрешает это только для черновика без студентов. */
export async function deleteCourse(courseId) {
  await client.delete(`/admin/courses/${courseId}`)
}

/** Одна лекция со сведениями о её файле. */
export async function fetchLesson(courseId, lessonId) {
  const { data } = await client.get(`/admin/courses/${courseId}/lessons/${lessonId}`)
  return data
}

/**
 * Длительность видео, прочитанная из самого файла.
 *
 * Здесь это возможно и уместно: файл целиком лежит на машине преподавателя. У студента
 * длительность не спрашивают никогда — там от неё зависит, засчитана ли лекция.
 */
function readDuration(file) {
  return new Promise((resolve) => {
    const element = document.createElement('video')
    element.preload = 'metadata'
    element.onloadedmetadata = () => {
      URL.revokeObjectURL(element.src)
      resolve(Number.isFinite(element.duration) ? Math.round(element.duration) : 0)
    }
    element.onerror = () => resolve(0)
    element.src = URL.createObjectURL(file)
  })
}

// Отдельный экземпляр без наших перехватчиков и без куки: файл уходит в хранилище, а не
// к нам, и отправлять туда заголовок авторизации незачем.
const plain = axios.create()

/**
 * Загрузить материал лекции.
 *
 * Три шага: сервер выдаёт разрешение ровно на этот файл, браузер отправляет файл прямо в
 * хранилище, сервер подтверждает, что файл действительно дошёл. Через приложение файл не
 * идёт — на видео это не «медленнее», а вообще неработоспособно.
 */
export async function uploadMaterial(courseId, lessonId, file, kind, onProgress) {
  const { data: ticket } = await client.post('/admin/uploads', {
    file_name: file.name,
    size_bytes: file.size,
    kind,
  })

  await plain.put(ticket.url, file, {
    headers: { 'Content-Type': ticket.content_type },
    onUploadProgress: (event) => {
      if (onProgress && event.total) onProgress(Math.round((event.loaded * 100) / event.total))
    },
  })

  const duration = kind === 'video' ? await readDuration(file) : 0
  const { data } = await client.post(`/admin/courses/${courseId}/lessons/${lessonId}/material`, {
    media_id: ticket.media_id,
    duration_seconds: duration,
  })
  return data
}

/** Кому и на что выдан доступ. */
export async function fetchAccess({ courseId = null, limit = 20, offset = 0 } = {}) {
  const { data } = await client.get('/admin/access', {
    params: { course_id: courseId ?? undefined, limit, offset },
  })
  return data
}

/** Открыть курс студенту вручную. */
export async function grantAccess(payload) {
  await client.post('/admin/access', payload)
}

/** Закрыть курс. Прогресс студента при этом остаётся на месте. */
export async function revokeAccess(grantId) {
  await client.delete(`/admin/access/${grantId}`)
}

/**
 * Справочники для формы курса: направления и виды удостоверений.
 *
 * Тот же адрес, что у фильтров каталога, но вызов свой: области друг к другу не ходят,
 * и одна общая функция связала бы админку с каталогом на ровном месте.
 */
export async function fetchTaxonomies() {
  const { data } = await client.get('/catalog/filters')
  return data
}
