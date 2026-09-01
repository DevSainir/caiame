import { expect, test } from '@playwright/test'
import { STUDENT, signIn } from './support.js'

/**
 * Вход и то, что он переживает перезагрузку.
 *
 * Отказ здесь делает продукт неработоспособным целиком, а ломается он тихо: токен живёт в
 * памяти страницы, сессия — в cookie, которую страница не видит, и любая ошибка в этой
 * связке проявляется только после перезагрузки, которой нет ни в одном другом тесте.
 */
test('вход переживает перезагрузку страницы', async ({ page }) => {
  await signIn(page, STUDENT)
  await expect(page.getByRole('button', { name: 'Выйти' })).toBeVisible()

  await page.reload()

  await expect(page.getByRole('button', { name: 'Выйти' })).toBeVisible()
})

test('выход завершает сессию, и она не возвращается после перезагрузки', async ({ page }) => {
  await signIn(page, STUDENT)

  await page.getByRole('button', { name: 'Выйти' }).click()
  await expect(page.getByRole('link', { name: 'Регистрация' }).first()).toBeVisible()
  await page.reload()

  await expect(page.getByRole('button', { name: 'Выйти' })).toHaveCount(0)
})
