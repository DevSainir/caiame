// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseInput from '@/core/components/BaseInput.vue'

describe('поле ввода', () => {
  it('связывает текст ошибки с самим полем', () => {
    // Показать ошибку рядом мало: без связи экранный диктор прочитает поле и промолчит о
    // том, что с ним не так.
    const field = mount(BaseInput, { props: { placeholder: 'Почта*', error: 'Проверьте адрес' } })
    const input = field.get('input')

    expect(input.attributes('aria-invalid')).toBe('true')
    expect(input.attributes('aria-describedby')).toBe(field.get('p').attributes('id'))
  })

  it('без ошибки ничего не обещает', () => {
    const input = mount(BaseInput, { props: { placeholder: 'Почта*' } }).get('input')

    expect(input.attributes('aria-invalid')).toBeUndefined()
    expect(input.attributes('aria-describedby')).toBeUndefined()
  })
})
