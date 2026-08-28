// The backend ships machine-readable values; Russian wording belongs here.
export const DIFFICULTY_LABELS = {
  beginner: 'Начальный',
  intermediate: 'Средний',
  advanced: 'Продвинутый',
}

export function difficultyLabel(value) {
  return DIFFICULTY_LABELS[value] ?? value
}
