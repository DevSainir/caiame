import { describe, expect, it } from 'vitest'
import { validateEmail, validatePassword } from '@/features/auth/validation'

describe('validateEmail', () => {
  it('accepts an ordinary address', () => {
    expect(validateEmail('aigul.sadykova@example.org')).toBe('')
  })

  it('accepts a plus tag and a subdomain', () => {
    expect(validateEmail('a.b+tag@mail.example.co.uk')).toBe('')
  })

  it('trims surrounding spaces before judging', () => {
    expect(validateEmail('  doctor@example.org  ')).toBe('')
  })

  it.each([
    ['empty', ''],
    ['no at sign', 'doctor.example.org'],
    ['no domain', 'doctor@'],
    ['no local part', '@example.org'],
    ['no dot in domain', 'doctor@example'],
    ['single letter tail', 'doctor@example.o'],
    ['inner space', 'doc tor@example.org'],
    ['two at signs', 'doctor@@example.org'],
  ])('rejects an address with %s', (_case, value) => {
    expect(validateEmail(value)).not.toBe('')
  })

  it('rejects an address longer than the column allows', () => {
    expect(validateEmail(`${'a'.repeat(320)}@example.org`)).not.toBe('')
  })
})

describe('validatePassword', () => {
  it('accepts eight characters', () => {
    expect(validatePassword('12345678')).toBe('')
  })

  it('rejects seven', () => {
    expect(validatePassword('1234567')).not.toBe('')
  })

  it('rejects an empty password with its own message', () => {
    expect(validatePassword('')).not.toBe(validatePassword('1234567'))
  })
})
