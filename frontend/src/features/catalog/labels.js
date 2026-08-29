// The backend ships machine-readable values; Russian wording belongs here.
export const AUDIENCE_LABELS = {
  doctor: 'Для врачей',
  nurse: 'Для медсестёр',
}

export function audienceLabel(value) {
  return AUDIENCE_LABELS[value] ?? value
}
