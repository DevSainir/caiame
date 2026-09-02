// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import AppToaster from '@/core/components/AppToaster.vue'
import { useNotificationStore } from '@/core/notifications/store'

describe('сообщения в углу', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('живая область стоит на контейнере, а не появляется вместе с текстом', () => {
    // Диктор читает то, что меняется внутри уже существующей области; область, возникшую
    // одновременно с сообщением, он может и не заметить.
    const toaster = mount(AppToaster)

    expect(toaster.element.getAttribute('aria-live')).toBe('polite')
  })

  it('удачу произносит спокойно, а неудачу — сразу', async () => {
    const toaster = mount(AppToaster)
    const notifications = useNotificationStore()

    notifications.notify('Материал загружен')
    notifications.notify('Не удалось загрузить файл', 'danger')
    await toaster.vm.$nextTick()

    const roles = toaster.findAll('[role]').map((node) => node.attributes('role'))
    expect(roles).toContain('status')
    expect(roles).toContain('alert')
  })
})
