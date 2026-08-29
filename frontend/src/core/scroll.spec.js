import { describe, expect, it } from 'vitest'
import { ease } from '@/core/scroll'

describe('ease', () => {
  it('начинается в нуле и заканчивается единицей', () => {
    expect(ease(0)).toBe(0)
    expect(ease(1)).toBe(1)
  })

  it('на середине пути проходит половину', () => {
    expect(ease(0.5)).toBeCloseTo(0.5, 5)
  })

  it('не поворачивает назад', () => {
    const points = Array.from({ length: 21 }, (_, index) => ease(index / 20))
    const sorted = [...points].sort((a, b) => a - b)
    expect(points).toEqual(sorted)
  })
})
