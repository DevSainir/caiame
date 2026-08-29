import { describe, expect, it } from 'vitest'
import { initialsFor } from '@/features/profile/initials'

describe('initialsFor', () => {
  it('берёт первые буквы имени и фамилии', () => {
    expect(initialsFor({ fullName: 'Айгуль Садыкова' })).toBe('АС')
  })

  it('обрезает до двух букв на длинном имени', () => {
    expect(initialsFor({ fullName: 'Асель Мураталиевна Турганбаева' })).toBe('АМ')
  })

  it('справляется с одним словом', () => {
    expect(initialsFor({ fullName: 'Марат' })).toBe('М')
  })

  it('не спотыкается о лишние пробелы', () => {
    expect(initialsFor({ fullName: '  Марат   Осмонов  ' })).toBe('МО')
  })

  // Имя при регистрации не спрашивается, поэтому у нового аккаунта его нет,
  // а пустой кружок читается как поломка вёрстки.
  it('без имени берёт первую букву адреса', () => {
    expect(initialsFor({ fullName: '', email: 'student@caiame.kg' })).toBe('S')
  })

  it('переживает полное отсутствие данных', () => {
    expect(initialsFor()).toBe('?')
    expect(initialsFor({})).toBe('?')
  })
})
