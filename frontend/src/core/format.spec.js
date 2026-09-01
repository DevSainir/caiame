import { describe, expect, it } from 'vitest'
import {
  formatDate,
  formatHours,
  formatMinutes,
  formatPrice,
  formatReviews,
  formatPoints,
  formatWorks,
} from '@/core/format'

describe('formatPrice', () => {
  it('переводит копейки в сомы и группирует тысячи', () => {
    // Разряды в ru-RU разделяет неразрывный пробел — иначе цена переносится посреди числа.
    expect(formatPrice(900000)).toBe('9\u00a0000 сом')
  })

  it('не показывает копейки у круглой цены', () => {
    expect(formatPrice(45000)).toBe('450 сом')
  })

  it('незнакомую валюту показывает кодом, а не молчит', () => {
    expect(formatPrice(100000, 'USD')).toBe('1\u00a0000 USD')
  })
})

describe('formatHours', () => {
  it('склоняет по последней цифре', () => {
    expect(formatHours(1)).toBe('1 час')
    expect(formatHours(72)).toBe('72 часа')
    expect(formatHours(36)).toBe('36 часов')
  })

  it('одиннадцать и дальше до двадцати — исключение', () => {
    expect(formatHours(11)).toBe('11 часов')
    expect(formatHours(14)).toBe('14 часов')
  })
})

describe('formatReviews', () => {
  it('склоняет счётчик отзывов', () => {
    expect(formatReviews(1)).toBe('1 отзыв')
    expect(formatReviews(22)).toBe('22 отзыва')
    expect(formatReviews(69)).toBe('69 отзывов')
    expect(formatReviews(0)).toBe('0 отзывов')
  })
})

describe('formatDate', () => {
  it('показывает дату по-русски и без «г.»', () => {
    expect(formatDate('2022-08-21T10:00:00Z')).toBe('21 августа 2022')
  })

  it('на мусоре возвращает пустую строку, а не «Invalid Date»', () => {
    expect(formatDate('не дата')).toBe('')
  })
})

describe('formatMinutes', () => {
  it('склоняет минуты', () => {
    expect(formatMinutes(1)).toBe('1 минута')
    expect(formatMinutes(23)).toBe('23 минуты')
    expect(formatMinutes(12)).toBe('12 минут')
  })
})

describe('formatWorks', () => {
  it('склоняет слово «работа» по числу', () => {
    // Очередь проверки показывает это число каждый день, и «1 работ» читается как ошибка
    // в данных, а не в вёрстке.
    expect(formatWorks(1)).toBe('1 работа')
    expect(formatWorks(3)).toBe('3 работы')
    expect(formatWorks(11)).toBe('11 работ')
    expect(formatWorks(22)).toBe('22 работы')
  })
})

describe('formatPoints', () => {
  it('склоняет «балл» по числу', () => {
    expect(formatPoints(1)).toBe('1 балл')
    expect(formatPoints(2)).toBe('2 балла')
    expect(formatPoints(5)).toBe('5 баллов')
  })
})
