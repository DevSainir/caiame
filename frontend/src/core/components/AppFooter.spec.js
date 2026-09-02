// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import AppFooter from '@/core/components/AppFooter.vue'
import { useAuthStore } from '@/core/session/store'

const global = {
  components: {
    RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
  },
}

function footerFor({ signedIn }) {
  const auth = useAuthStore()
  auth.isReady = true
  if (signedIn) {
    auth.applyUser({ id: '1', email: 'student@example.org', full_name: '', role: 'student' })
  }
  return mount(AppFooter, { global })
}

describe('подвал', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('гостю предлагает вход и регистрацию', () => {
    const footer = footerFor({ signedIn: false })

    expect(footer.text()).toContain('Войти')
    expect(footer.text()).toContain('Регистрация')
  })

  it('вошедшему их не показывает', () => {
    // Обе ссылки развернул бы охранник роутера обратно на эту же страницу. Указатель,
    // который возвращает туда, откуда по нему пошли, — это не указатель.
    const footer = footerFor({ signedIn: true })

    expect(footer.text()).toContain('Личный кабинет')
    expect(footer.text()).not.toContain('Регистрация')
  })
})
