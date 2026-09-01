// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { pageTitle, setNoIndex, setPageTitle } from '@/core/page'

afterEach(() => setNoIndex(false))

describe('заголовок страницы', () => {
  it('добавляет к названию страницы имя института', () => {
    expect(pageTitle('Программа курса')).toBe('Программа курса — ЦАИДМО')
  })

  it('на главной оставляет полное имя', () => {
    // Одинаковый заголовок на всех вкладках бесполезен, а главная — единственное место,
    // где полное название работает.
    expect(pageTitle('')).toContain('Центрально-Азиатский')
  })

  it('ставит заголовок в документ', () => {
    setPageTitle('Лекция')

    expect(document.title).toBe('Лекция — ЦАИДМО')
  })
})

describe('закрытие от поисковых роботов', () => {
  it('добавляет метку и убирает её обратно', () => {
    setNoIndex(true)
    expect(document.querySelector('meta[name="robots"]').content).toBe('noindex')

    setNoIndex(false)
    expect(document.querySelector('meta[name="robots"]')).toBeNull()
  })

  it('не плодит метки при повторном вызове', () => {
    setNoIndex(true)
    setNoIndex(true)

    expect(document.querySelectorAll('meta[name="robots"]')).toHaveLength(1)
  })
})
