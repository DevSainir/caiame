// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import AdminReviewers from '@/features/admin/components/AdminReviewers.vue'
import * as api from '@/features/admin/api'

vi.mock('@/features/admin/api')

const COURSE_ID = '01a052c4-bc06-76d9-9cdd-7334f8e2e966'

describe('кто проверяет работы курса', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(api.fetchReviewers).mockResolvedValue([])
    vi.mocked(api.addReviewer).mockReset()
  })

  it('пустой список объясняет, что это значит', async () => {
    // Пустая таблица здесь — не «ещё не загрузилось», а состояние с последствием:
    // работы курса видят только администраторы.
    const block = mount(AdminReviewers, { props: { courseId: COURSE_ID } })
    await flushPromises()

    expect(block.text()).toContain('только администраторы')
  })

  it('называет причину, когда почта принадлежит студенту', async () => {
    vi.mocked(api.addReviewer).mockRejectedValue({ status: 409, code: 'not_a_member_of_staff' })
    const block = mount(AdminReviewers, { props: { courseId: COURSE_ID } })
    await flushPromises()

    await block.find('input[type=email]').setValue('student@example.org')
    await block.find('form').trigger('submit')
    await flushPromises()

    expect(block.text()).toContain('не сотрудник академии')
  })

  it('не отправляет запрос без похожей на почту строки', async () => {
    const block = mount(AdminReviewers, { props: { courseId: COURSE_ID } })
    await flushPromises()

    await block.find('input[type=email]').setValue('иванов')
    await block.find('form').trigger('submit')
    await flushPromises()

    expect(api.addReviewer).not.toHaveBeenCalled()
  })

  it('показывает назначенных с их почтой', async () => {
    vi.mocked(api.fetchReviewers).mockResolvedValue([
      {
        id: 'a1',
        user_id: 'u1',
        name: 'Марат Осмонов',
        email: 'instructor@caiame.kg',
        role: 'instructor',
      },
    ])
    const block = mount(AdminReviewers, { props: { courseId: COURSE_ID } })
    await flushPromises()

    expect(block.text()).toContain('Марат Осмонов')
    expect(block.text()).toContain('instructor@caiame.kg')
  })
})
