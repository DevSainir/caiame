import { expect, test } from '@playwright/test'
import {
  ADMIN,
  OTHER_STUDENT,
  firstCourse,
  grantAccess,
  returnPendingWork,
  revokeAccessFor,
  signIn,
  tokenFor,
} from './support.js'

/**
 * Полный круг работы с ручной проверкой: студент сдал — преподаватель вернул — студент
 * увидел, что именно ему написали.
 *
 * Заслуживает end-to-end потому, что проходит через два экрана, две роли и правило, которое
 * не видно ни с одной стороны по отдельности: возврат на доработку не переписывает
 * присланное, а открывает следующую попытку. Отказ этого круга делает задания
 * неработоспособными — сдать будет некуда или проверить нечем.
 */
test.describe.configure({ mode: 'serial' })

test('работа проходит круг: сдана, возвращена, видна студенту', async ({ browser }) => {
  const admin = await tokenFor(ADMIN)
  const course = await firstCourse(admin)
  const assignment = course.tree.activities.find((item) => item.kind === 'assignment')
  await grantAccess(admin, course.id, OTHER_STUDENT.email)
  await returnPendingWork(admin, OTHER_STUDENT.email)

  const studentPage = await browser.newPage()
  await signIn(studentPage, OTHER_STUDENT)
  await studentPage.goto(`/assignments/${assignment.id}`)
  await studentPage
    .getByPlaceholder('Что вы сделали и на что обратить внимание')
    .fill('Разбор случая приложен текстом')
  await studentPage.getByRole('button', { name: 'Отправить на проверку' }).click()
  await expect(studentPage.getByText('На проверке')).toBeVisible()

  const reviewerPage = await browser.newPage()
  await signIn(reviewerPage, ADMIN)
  await reviewerPage.goto('/admin/submissions')
  await reviewerPage
    .getByRole('link', { name: /Проверить/ })
    .first()
    .click()
  await reviewerPage.getByRole('textbox').first().fill('Дополните раздел про дозировки')
  await reviewerPage.getByRole('button', { name: 'На доработку' }).click()
  // Уведомление в углу проверяем отдельно от самой панели: они говорят одно и то же, но
  // уведомление живёт пять секунд, а панель — состояние работы.
  await expect(reviewerPage.getByRole('status')).toContainText('на доработку')
  await expect(
    reviewerPage.getByRole('main').getByText('Работа отправлена на доработку'),
  ).toBeVisible()

  // Студент видит рецензию целиком и может прислать следующую попытку — прежняя остаётся.
  await studentPage.reload()
  // Первая из карточек: прошлые прогоны оставляют свои попытки, и это правильно —
  // возврат на доработку ничего не стирает.
  await expect(studentPage.getByText('Дополните раздел про дозировки').first()).toBeVisible()
  await expect(studentPage.getByText('Отправить доработку')).toBeVisible()

  await revokeAccessFor(admin, OTHER_STUDENT.email)
  await studentPage.close()
  await reviewerPage.close()
})
