import { expect, test } from "@playwright/test";
import {
  ADMIN,
  OTHER_STUDENT,
  firstCourse,
  grantAccess,
  revokeAccessFor,
  signIn,
  tokenFor,
} from "./support.js";

/**
 * Прохождение тестирования от вопроса до результата.
 *
 * Заслуживает end-to-end потому, что оценивание идёт на сервере, а ответ студента
 * собирается на клиенте: расхождение между тем, что отправила страница, и тем, что ждёт
 * сервер, не видно ни с одной стороны по отдельности — а от него зависит отметка о
 * прохождении курса.
 */
test("студент проходит тестирование и видит результат", async ({ page }) => {
  const admin = await tokenFor(ADMIN);
  const course = await firstCourse(admin);
  const unit = course.tree.activities.find((item) => item.kind === "test");
  await grantAccess(admin, course.id, OTHER_STUDENT.email);

  await signIn(page, OTHER_STUDENT);
  await page.goto(`/tests/${unit.id}`);
  await expect(page.getByRole("heading").first()).toBeVisible();

  // Отвечаем первым вариантом в каждом вопросе: верность ответа здесь не проверяется —
  // проверяется, что попытка доходит до сервера и возвращается оценённой.
  const options = page.locator("input[type=radio], input[type=checkbox]");
  for (let index = 0; index < (await options.count()); index += 1) {
    await options.nth(index).check({ force: true });
  }
  await page.getByRole("button", { name: /Сдать тестирование/ }).click();

  await expect(page.getByText(/Тест сдан|Тест не сдан/)).toBeVisible();
  await revokeAccessFor(admin, OTHER_STUDENT.email);
});
