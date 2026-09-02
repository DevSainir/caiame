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

  it('область одна: у самих сообщений роли нет', async () => {
    // Вложенная живая область спорит с внешней, и что из них прочитают — зависит от
    // диктора. Текст сообщений при этом попадает внутрь той, что объявлена.
    const toaster = mount(AppToaster)
    const notifications = useNotificationStore()

    notifications.notify('Материал загружен')
    notifications.notify('Не удалось загрузить файл', 'danger')
    await toaster.vm.$nextTick()

    expect(toaster.findAll('[role]')).toHaveLength(1)
    expect(toaster.text()).toContain('Материал загружен')
    expect(toaster.text()).toContain('Не удалось загрузить файл')
  })
})
