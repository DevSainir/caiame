// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import BaseButton from '@/core/components/BaseButton.vue'
import CourseHero from '@/features/catalog/components/CourseHero.vue'
import { useAuthStore } from '@/core/session/store'

const COURSE = {
  slug: 'therapy',
  title: 'Повышение квалификации по терапии',
  summary: 'Кратко о курсе',
  description: 'Описание',
  cover_url: null,
  price_minor: 1800000,
  currency: 'KGS',
  duration_hours: 72,
  specialization: { name: 'Терапия', audience: 'doctor' },
  accreditation: { name: 'Сертифицированный, 72 часа', short_code: '72' },
}

// RouterLink подставляется компонентом, а не заглушкой: кнопка выбирает его по имени во
// время работы, и заглушка по такому имени не находится.
const global = {
  components: {
    RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
  },
}

function heroFor({ signedIn, access }) {
  const auth = useAuthStore()
  auth.isReady = true
  if (signedIn) auth.applyUser({ id: '1', email: 'student@example.org', role: 'student' })
  return mount(CourseHero, { props: { course: COURSE, access }, global })
}

describe('кнопка на странице курса', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('гостю предлагает зарегистрироваться', () => {
    const hero = heroFor({ signedIn: false, access: null })

    expect(hero.text()).toContain('Зарегистрироваться')
  })

  it('студенту с доступом даёт войти в обучение с первого модуля', () => {
    const hero = heroFor({
      signedIn: true,
      access: { has_access: true, modules: [{ id: 'm1' }] },
    })

    expect(hero.text()).toContain('Перейти к обучению')
    // Куда ведёт кнопка, спрашиваем у самой кнопки: подставлять сюда роутер значит
    // проверять роутер, а не то, что здесь решается.
    expect(hero.findComponent(BaseButton).props('to')).toBe('/modules/m1')
  })

  it('студенту без доступа объясняет, а не зовёт регистрироваться заново', () => {
    // Ссылки, которая записала бы на цикл, не существует: записывает учебная часть. Кнопка
    // здесь была бы обещанием, которого система не выполняет.
    const hero = heroFor({ signedIn: true, access: { has_access: false, modules: [] } })

    expect(hero.text()).toContain('учебная часть')
    expect(hero.text()).not.toContain('Зарегистрироваться')
  })

  it('пока про доступ ничего не известно, не показывает ничего', () => {
    // План курса грузится отдельным запросом. Мигнуть «зарегистрируйтесь» вошедшему
    // студенту хуже, чем подождать полсекунды.
    const hero = heroFor({ signedIn: true, access: null })

    expect(hero.text()).not.toContain('Зарегистрироваться')
    expect(hero.text()).not.toContain('Перейти к обучению')
  })
})
