import { describe, expect, it } from 'vitest'
import { describeError } from '@/core/api/messages'

describe('describeError', () => {
  it('называет причину, когда сервер её назвал', () => {
    expect(describeError({ status: 402, code: 'access_required' })).toContain('не открыт')
  })

  it('сводит любую поломку на нашей стороне к одной фразе', () => {
    // Ни номера, ни имени функции: посетителю от них нет пользы, а разработчику они
    // приходят в логи, а не через экран человека.
    const message = describeError({ status: 500, code: 'ValueError in get_course' })

    expect(message).toBe('На нашей стороне неполадки. Мы уже разбираемся — попробуйте позже')
    expect(message).not.toContain('500')
    expect(message).not.toContain('ValueError')
  })

  it('отличает обрыв связи от отказа сервера', () => {
    expect(describeError({ status: 0, code: 'ERR_NETWORK' })).toContain('подключение')
  })

  it('возвращает свою формулировку, когда код неизвестен', () => {
    expect(describeError({ status: 418, code: 'teapot' }, 'Не получилось')).toBe('Не получилось')
  })
})

describe('слишком много попыток', () => {
  it('говорит, через сколько пробовать снова', () => {
    // Ограничитель отвечает заголовком; без него фраза превращается в «подождите
    // неизвестно сколько».
    const failure = { status: 429, original: { response: { headers: { 'retry-after': '300' } } } }

    expect(describeError(failure)).toContain('через 5 мин')
  })

  it('на короткой паузе говорит «через минуту», а не «через 0 мин»', () => {
    const failure = { status: 429, original: { response: { headers: { 'retry-after': '20' } } } }

    expect(describeError(failure)).toContain('через минуту')
  })
})

describe('неверный адрес', () => {
  it('на открытии страницы не отправляет проверять поля, которых нет', () => {
    // Адрес с чужим или устаревшим идентификатором сервер отвергает разбором пути. Для
    // читающей страницы это то же самое, что «не нашли»: заполнять там нечего.
    expect(describeError({ status: 422, method: 'get' })).toBe('Мы не нашли то, что вы открыли')
  })

  it('в форме по-прежнему просит проверить поля', () => {
    expect(describeError({ status: 422, method: 'post' })).toBe('Проверьте заполненные поля')
  })
})
