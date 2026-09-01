// Общая часть сценариев: аккаунты из сидов и выдача доступа через API.
//
// Доступ выдаётся тем же роутом, которым им пользуется администратор, а не подсовыванием
// строки в базу: сценарий должен ломаться, если сломается настоящий путь.

// Разные сценарии входят разными студентами. Вход ограничен по числу попыток на аккаунт,
// и это правильно; три файла, входящие одним и тем же человеком, на втором прогоне подряд
// упираются в ограничитель и падают не потому, что что-то сломано.
//
// Сессию между тестами не переносим тем более: refresh-токен ротируется, и повторное
// предъявление сохранённого убивает всю цепочку — ровно так, как задумано против кражи.
export const STUDENT = {
  email: 'student@caiame.kg',
  password: 'caiame-dev-2026',
}
export const OTHER_STUDENT = {
  email: 'timur.sadykov@example.kg',
  password: 'caiame-dev-2026',
}
export const ADMIN = { email: 'admin@caiame.kg', password: 'caiame-dev-2026' }

const API = process.env.E2E_API_URL || 'http://localhost:8001/api/v1'

async function json(path, { method = 'GET', token, body } = {}) {
  const response = await fetch(`${API}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (response.status === 429) {
    throw new Error(
      'Вход отказал по числу попыток. Это защита от подбора, а не поломка: сценарии ' +
        'входят по-настоящему, и четвёртый прогон подряд за пятнадцать минут в неё ' +
        'упирается. Подождите или очистите счётчики: docker exec caiame-redis-1 redis-cli FLUSHALL',
    )
  }
  if (!response.ok) {
    throw new Error(`${method} ${path} → ${response.status}. Поднят ли API на ${API}?`)
  }
  return response.status === 204 ? null : response.json()
}

// Токен на аккаунт кешируется на весь прогон. Вход ограничен по числу попыток — и это
// правильная защита, — а сценарии, каждый из которых логинится заново, упираются в неё на
// втором прогоне подряд и падают не потому, что что-то сломано.
const tokens = new Map()

export async function tokenFor(account) {
  const cached = tokens.get(account.email)
  if (cached) return cached
  const session = await json('/auth/login', { method: 'POST', body: account })
  tokens.set(account.email, session.access_token)
  return session.access_token
}

/** Первый опубликованный курс с программой — на нём и идут сценарии. */
export async function firstCourse(adminToken) {
  const courses = await json('/admin/courses', { token: adminToken })
  const published = courses.find((course) => course.status === 'published')
  const tree = await json(`/admin/courses/${published.id}`, {
    token: adminToken,
  })
  return { ...published, tree }
}

export async function grantAccess(adminToken, courseId, email) {
  await json('/admin/access', {
    method: 'POST',
    token: adminToken,
    body: { email, course_id: courseId, reason: 'end-to-end' },
  })
}

export async function revokeAccessFor(adminToken, email) {
  const page = await json('/admin/access?limit=100', { token: adminToken })
  for (const grant of page.items) {
    if (grant.student_email === email && !grant.revoked_at) {
      await json(`/admin/access/${grant.id}`, {
        method: 'DELETE',
        token: adminToken,
      })
    }
  }
}

/** Вход через форму, а не подстановкой токена: это и есть проверяемый сценарий. */
export async function signIn(page, account) {
  await page.goto('/login')
  await page.getByPlaceholder('Почта*').fill(account.email)
  await page.getByPlaceholder('Пароль*').fill(account.password)
  await page.getByRole('button', { name: 'Продолжить' }).click()
  await page.waitForURL('**/')
}

/**
 * Вернуть студенту всё, что висит у него на проверке.
 *
 * Сценарий не может начинаться с «а вдруг база чистая»: прошлый прогон или ручная проверка
 * оставляют незакрытую работу, а пока она висит, сдать новую нельзя — и тест падает на
 * форме, которой правильно нет. Разгребается это тем же путём, что и у человека: работа
 * возвращается на доработку.
 */
export async function returnPendingWork(adminToken, email) {
  const queue = await json('/admin/submissions?limit=100', {
    token: adminToken,
  })
  for (const row of queue.items) {
    if (row.student_email !== email) continue
    await json(`/admin/submissions/${row.id}/review`, {
      method: 'POST',
      token: adminToken,
      body: {
        score: 0,
        comment: 'Возврат перед прогоном сценария',
        decision: 'needs_revision',
      },
    })
  }
}
