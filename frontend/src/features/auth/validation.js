// One local part, one @, one domain with a dot and a sane tail. Deliberately strict about
// the shape and silent about the rest: the backend re-validates, and a regex that tries to
// implement RFC 5322 rejects real addresses.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
const MAX_EMAIL_LENGTH = 320
const MIN_PASSWORD_LENGTH = 8

/** Returns a message for the user, or an empty string when the address is fine. */
export function validateEmail(value) {
  const email = value.trim()
  if (email === '') return 'Укажите адрес электронной почты'
  if (email.length > MAX_EMAIL_LENGTH) return 'Адрес слишком длинный'
  if (!EMAIL_PATTERN.test(email)) return 'Похоже, в адресе опечатка'
  return ''
}

/** Returns a message for the user, or an empty string when the password is acceptable. */
export function validatePassword(value) {
  if (value === '') return 'Придумайте пароль'
  if (value.length < MIN_PASSWORD_LENGTH) return 'Пароль должен быть не короче 8 символов'
  return ''
}
