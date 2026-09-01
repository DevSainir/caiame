import { describeTooManyAttempts } from '@/core/api/messages'

// The backend answers with a code; the wording lives here. One place, so "неверная почта
// или пароль" cannot drift between the sign-in and the sign-up screen.
const MESSAGES = {
  invalid_credentials: 'Неверная почта или пароль',
  email_already_registered: 'Эта почта уже зарегистрирована. Войдите или укажите другую.',
  no_refresh_token: 'Сессия истекла. Войдите ещё раз.',
  invalid_refresh_token: 'Сессия истекла. Войдите ещё раз.',
  refresh_token_reused: 'Сессия завершена в целях безопасности. Войдите ещё раз.',
}

/** Turn a rejected request into a sentence for the person looking at the form. */
export function describeFailure(failure, fallback) {
  // «Слишком часто» звучит одинаково везде и живёт в общем словаре: в счётчик упирается не
  // только вход.
  if (failure?.code === 'too_many_attempts') return describeTooManyAttempts(failure)
  return MESSAGES[failure?.code] ?? fallback
}
