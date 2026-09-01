// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AdminQuestionForm from '@/features/admin/components/AdminQuestionForm.vue'

const ANSWERED_QUESTION = {
  id: 'q1',
  position: 1,
  text: 'Сколько часов занимает программа?',
  kind: 'single',
  points: 1,
  is_answered: true,
  options: [
    { id: 'o1', text: '72 часа', is_correct: true },
    { id: 'o2', text: '36 часов', is_correct: false },
  ],
}

// Кнопки-отметки вариантов: у модального окна есть своя кнопка с aria-label, и без
// фильтра нумерация уезжает на единицу.
const marks = (form) =>
  form
    .findAll('button[aria-label]')
    .filter((button) => button.attributes('aria-label') !== 'Закрыть')

describe('форма вопроса теста', () => {
  it('не отправляет вопрос, в котором не отмечен ни один верный вариант', async () => {
    // Достижимо только там, где ответов может быть несколько: в вопросе с одним ответом
    // отметка всегда на ком-то стоит. Такой вопрос не может пройти никто, и на экране это
    // ничем не выделено — поэтому отказ здесь, до сохранения.
    const form = mount(AdminQuestionForm)
    const [first, second] = form.findAll('input[type=text]')
    await first.setValue('Первый вариант')
    await second.setValue('Второй вариант')
    await form.find('textarea').setValue('Вопрос без верного ответа')
    await form.findAll('select')[0].setValue('multiple')
    await marks(form)[0].trigger('click')

    await form.find('form').trigger('submit')

    expect(form.emitted('submit')).toBeUndefined()
    expect(form.text()).toContain('Отметьте верный вариант')
  })

  it('в вопросе с одним ответом отметка переезжает, а не копится', async () => {
    // Иначе получается вопрос с двумя верными ответами и одним ожидаемым — балл
    // начисляется по правилу, которого никто не писал.
    const form = mount(AdminQuestionForm)

    await marks(form)[1].trigger('click')

    expect(marks(form)[0].attributes('aria-label')).toBe('Отметить верным')
    expect(marks(form)[1].attributes('aria-label')).toBe('Верный вариант')
  })

  it('замену отвеченного вопроса называет заменой, а не правкой', async () => {
    const form = mount(AdminQuestionForm, {
      props: { question: ANSWERED_QUESTION, isReplacement: true },
    })

    expect(form.text()).toContain('уже отвечали')
    expect(form.find('button[type=submit]').text()).toBe('Заменить')
  })
})
