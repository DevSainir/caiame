import { describe, expect, it } from 'vitest'
import { describeFailure } from '@/features/auth/failures'

const FALLBACK = 'Не получилось войти. Попробуйте ещё раз.'

describe('describeFailure', () => {
  it('names the two halves of a wrong sign-in with one message', () => {
    expect(describeFailure({ code: 'invalid_credentials' }, FALLBACK)).toBe(
      'Неверная почта или пароль',
    )
  })

  it('turns Retry-After seconds into whole minutes', () => {
    const failure = {
      code: 'too_many_attempts',
      original: { response: { headers: { 'retry-after': '620' } } },
    }

    expect(describeFailure(failure, FALLBACK)).toContain('11 мин')
  })

  it('rounds a short wait up to one minute instead of saying zero', () => {
    const failure = {
      code: 'too_many_attempts',
      original: { response: { headers: { 'retry-after': '12' } } },
    }

    expect(describeFailure(failure, FALLBACK)).toBe(
      'Слишком много попыток. Попробуйте через минуту.',
    )
  })

  it('survives a rate limit answer with no header at all', () => {
    expect(describeFailure({ code: 'too_many_attempts' }, FALLBACK)).toContain('Слишком много')
  })

  it('falls back for a code it has never seen', () => {
    expect(describeFailure({ code: 'teapot' }, FALLBACK)).toBe(FALLBACK)
  })

  it('falls back when there is no error object at all', () => {
    expect(describeFailure(undefined, FALLBACK)).toBe(FALLBACK)
  })
})
