/**
 * Инициалы для аватара — в core/, потому что их показывают и профиль, и отзывы.
 *
 * Имя при регистрации не спрашивается, поэтому у нового аккаунта его нет — тогда берём
 * первую букву адреса. Пустой кружок выглядит как поломка вёрстки, а не как «имя не задано».
 */
export function initialsFor({ fullName = '', email = '' } = {}) {
  const words = fullName.trim().split(/\s+/).filter(Boolean)
  if (words.length > 0) {
    return words
      .slice(0, 2)
      .map((word) => word[0])
      .join('')
      .toUpperCase()
  }
  return (email.trim()[0] ?? '?').toUpperCase()
}
