// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import LessonRow from '@/features/learning/components/LessonRow.vue'

const LESSON = {
  id: 'b7f0f0a2-0000-7000-8000-000000000001',
  position: 1,
  title: 'Вводная лекция',
  kind: 'video',
  duration_minutes: 23,
  status: 'not_started',
}

// RouterLink здесь не настоящий: проверяем не роутер, а то, чем строка становится, когда
// доступа нет.
const global = { stubs: { RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } } }

describe('строка лекции', () => {
  it('ведёт на лекцию, когда доступ есть', () => {
    const row = mount(LessonRow, { props: { lesson: LESSON, hasAccess: true }, global })

    expect(row.find('a').attributes('href')).toBe(`/lessons/${LESSON.id}`)
  })

  it('перестаёт быть ссылкой, когда доступа нет', () => {
    // Пейволл на стороне сервера уже стоит; здесь закрепляется то, что строка не
    // приглашает в отказ — по ней некуда нажать.
    const row = mount(LessonRow, { props: { lesson: LESSON, hasAccess: false }, global })

    expect(row.find('a').exists()).toBe(false)
    expect(row.text()).toContain('Вводная лекция')
  })
})
