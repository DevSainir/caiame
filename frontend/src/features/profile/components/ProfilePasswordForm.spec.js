// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import ProfilePasswordForm from '@/features/profile/components/ProfilePasswordForm.vue'
import * as sessionApi from '@/core/session/api'

vi.mock('@/core/session/api')

async function fill(form, { current, next, repeat }) {
  const [currentField, nextField, repeatField] = form.findAll('input')
  await currentField.setValue(current)
  await nextField.setValue(next)
  await repeatField.setValue(repeat)
}

describe('смена пароля', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(sessionApi.changePassword).mockReset()
    vi.mocked(sessionApi.changePassword).mockResolvedValue({
      access_token: 'token',
      expires_in: 900,
      user: { id: '1', email: 'student@example.org', full_name: '', role: 'student' },
    })
  })

  it('не отправляет запрос, когда повтор не совпал', async () => {
    // Расхождение видно на клиенте, и запрос за ним не нужен: сервер ответил бы «пароль
    // изменён» на тот, который человек ввёл по ошибке дважды по-разному.
    const form = mount(ProfilePasswordForm)
    await fill(form, { current: 'старый', next: 'новый-пароль', repeat: 'другой-пароль' })

    await form.find('form').trigger('submit')

    expect(sessionApi.changePassword).not.toHaveBeenCalled()
    expect(form.text()).toContain('не совпадают')
  })

  it('отправляет текущий и новый пароль, когда всё заполнено', async () => {
    const form = mount(ProfilePasswordForm)
    await fill(form, { current: 'старый', next: 'новый-пароль', repeat: 'новый-пароль' })

    await form.find('form').trigger('submit')

    expect(sessionApi.changePassword).toHaveBeenCalledWith({
      current_password: 'старый',
      new_password: 'новый-пароль',
    })
  })

  it('говорит про текущий пароль, когда сервер его не принял', async () => {
    // Единственная ошибка, которую человек может исправить сам, поэтому она названа
    // отдельно, а не общей фразой про неудачу.
    vi.mocked(sessionApi.changePassword).mockRejectedValue({
      status: 401,
      code: 'invalid_credentials',
    })
    const form = mount(ProfilePasswordForm)
    await fill(form, { current: 'неверный', next: 'новый-пароль', repeat: 'новый-пароль' })

    await form.find('form').trigger('submit')
    await new Promise((resolve) => setTimeout(resolve))

    expect(form.text()).toContain('Текущий пароль введён неверно')
  })

  it('короткий пароль не даёт нажать кнопку', () => {
    const form = mount(ProfilePasswordForm)

    expect(form.find('button[type=submit]').attributes('disabled')).toBeDefined()
  })
})
