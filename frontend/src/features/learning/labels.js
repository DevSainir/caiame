// Бэкенд отдаёт машинные значения; русские подписи живут здесь и только здесь — их
// показывают и страница курса, и страница модуля.
export const STATUS_LABELS = {
  not_started: 'Не начат',
  in_progress: 'В процессе',
  done: 'Завершено',
}

export const STATUS_TONE = {
  not_started: 'text-disabled',
  in_progress: 'text-ink',
  done: 'text-accent',
}

export const LESSON_KIND_LABELS = {
  video: 'Видео-лекция',
  pdf: 'PDF-файл',
}

export function statusLabel(value) {
  return STATUS_LABELS[value] ?? value
}

export function lessonKindLabel(value) {
  return LESSON_KIND_LABELS[value] ?? value
}
