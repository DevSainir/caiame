// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import HomeHero from '@/features/home/components/HomeHero.vue'
import { useAuthStore } from '@/core/session/store'

const global = {
  components: {
    RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
  },
}

function heroFor({ signedIn }) {
  const auth = useAuthStore()
  auth.isReady = true
  if (signedIn) {
    auth.applyUser({ id: '1', email: 'student@example.org', full_name: '', role: 'student' })
  }
  return mount(HomeHero, { global })
}

describe('первый экран главной', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('гостя зовёт войти', () => {
    const hero = heroFor({ signedIn: false })

    expect(hero.text()).toContain('Войти')
    expect(hero.text()).toContain('Зарегистрируйтесь')
  })

  it('вошедшего ведёт в личный кабинет, а не на вход', () => {
    // «Войти» для вошедшего ведёт на эту же страницу: охранник разворачивает его обратно.
    const hero = heroFor({ signedIn: true })

    expect(hero.text()).toContain('Личный кабинет')
    expect(hero.text()).not.toContain('Зарегистрируйтесь')
  })
})
