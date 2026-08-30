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
