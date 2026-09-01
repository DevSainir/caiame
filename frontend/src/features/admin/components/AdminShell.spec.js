// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import AdminShell from '@/features/admin/components/AdminShell.vue'
import { useAuthStore } from '@/core/session/store'

const global = {
  components: { RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } },
}

function shellFor(role) {
  const auth = useAuthStore()
  auth.isReady = true
  auth.applyUser({ id: '1', email: 'staff@example.org', full_name: '', role })
  return mount(AdminShell, { props: { title: 'Экран' }, global })
}

describe('меню администрирования', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('администратору показывает все разделы', () => {
    const shell = shellFor('admin')

    expect(shell.text()).toContain('Курсы')
    expect(shell.text()).toContain('Проверка работ')
    expect(shell.text()).toContain('Студенты и доступ')
  })

  it('преподавателю — только проверку работ', () => {
    // Остальные пункты вернул бы охранник роутера: предлагать дверь, которая не
    // откроется, хуже, чем не предлагать её вовсе.
    const shell = shellFor('instructor')

    expect(shell.text()).toContain('Проверка работ')
    expect(shell.text()).not.toContain('Студенты и доступ')
  })
})
