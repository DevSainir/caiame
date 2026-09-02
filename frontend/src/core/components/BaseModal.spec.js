// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseModal from '@/core/components/BaseModal.vue'

function open(slot = '<input class="field" /><button class="save">Сохранить</button>') {
  const host = document.createElement('div')
  document.body.appendChild(host)
  return mount(BaseModal, {
    props: { title: 'Переименовать модуль' },
    slots: { default: slot },
    attachTo: host,
  })
}

describe('окно', () => {
  it('ставит фокус в первое поле, а не оставляет его на странице', async () => {
    // Окно почти всегда форма: человек открыл его, чтобы печатать.
    const modal = open()

    expect(document.activeElement).toBe(modal.find('.field').element)

    modal.unmount()
  })

  it('возвращает фокус туда, откуда его открыли', async () => {
    const opener = document.createElement('button')
    document.body.appendChild(opener)
    opener.focus()

    const modal = open()
    modal.unmount()

    expect(document.activeElement).toBe(opener)
    opener.remove()
  })

  it('закрывается по Escape', async () => {
    const modal = open()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))

    expect(modal.emitted('close')).toHaveLength(1)
    modal.unmount()
  })

  it('не выпускает Tab за затемнение', async () => {
    // Иначе фокус уходит на страницу, которой в этот момент как бы нет: человек жмёт
    // Enter и попадает в кнопку, которой не видит.
    const modal = open()
    const save = modal.find('.save').element
    save.focus()

    const event = new KeyboardEvent('keydown', { key: 'Tab', cancelable: true })
    document.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    // По кругу — на первое, что в окне есть, а это крестик закрытия.
    expect(modal.element.contains(document.activeElement)).toBe(true)
    expect(document.activeElement.getAttribute('aria-label')).toBe('Закрыть')
    modal.unmount()
  })

  it('объявляет себя окном, а не куском страницы', () => {
    const modal = open()
    const dialog = modal.find('[role="dialog"]')

    expect(dialog.attributes('aria-modal')).toBe('true')
    expect(dialog.attributes('aria-label')).toBe('Переименовать модуль')
    modal.unmount()
  })
})
