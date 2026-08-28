// The backend answers with a code; the wording lives here. One place, so "неверная почта
// или пароль" cannot drift between the sign-in and the sign-up screen.
const MESSAGES = {
  invalid_credentials: 'Неверная почта или пароль',
  email_already_registered: 'Эта почта уже зарегистрирована. Войдите или укажите другую.',
  no_refresh_token: 'Сессия истекла. Войдите ещё раз.',
  invalid_refresh_token: 'Сессия истекла. Войдите ещё раз.',
  refresh_token_reused: 'Сессия завершена в целях безопасности. Войдите ещё раз.',
}

const SECONDS_IN_MINUTE = 60

/** Turn a rejected request into a sentence for the person looking at the form. */
export function describeFailure(failure, fallback) {
  if (failure?.code === 'too_many_attempts') {
    const seconds = Number(failure.original?.response?.headers?.['retry-after'] ?? 0)
    const minutes = Math.ceil(seconds / SECONDS_IN_MINUTE)
    return minutes > 1
      ? `Слишком много попыток. Попробуйте через ${minutes} мин.`
      : 'Слишком много попыток. Попробуйте через минуту.'
  }
  return MESSAGES[failure?.code] ?? fallback
}
