import { afterEach, describe, expect, it } from 'vitest'
import { hasSessionHint } from '@/core/session/session-hint'

function withCookies(value) {
  globalThis.document = { cookie: value }
}

afterEach(() => {
  delete globalThis.document
})

describe('hasSessionHint', () => {
  it('is false for a visitor who has never signed in', () => {
    withCookies('')

    expect(hasSessionHint()).toBe(false)
  })

  it('is true when the backend left the hint', () => {
    withCookies('has_session=1')

    expect(hasSessionHint()).toBe(true)
  })

  it('finds the hint among other cookies', () => {
    withCookies('lang=ru; has_session=1; theme=dark')

    expect(hasSessionHint()).toBe(true)
  })

  it('is not fooled by a cookie whose name merely ends with the hint', () => {
    withCookies('not_has_session=1')

    expect(hasSessionHint()).toBe(false)
  })
})
