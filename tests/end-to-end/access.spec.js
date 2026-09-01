import { expect, test } from "@playwright/test";
import {
  ADMIN,
  STUDENT,
  firstCourse,
  grantAccess,
  revokeAccessFor,
  signIn,
  tokenFor,
} from "./support.js";

/**
 * Платный доступ к материалам, целиком: браузер, приложение, API, база.
 *
 * Этот сценарий заслуживает end-to-end, потому что его отказ стоит денег в обе стороны.
 * Откроется лекция без доступа — курсы раздаются бесплатно; не откроется с доступом —
 * человек заплатил и не получил ничего. Ни одна из этих поломок не видна ни в юнит-тесте
 * сервиса, ни в компонентном тесте разметки: они складываются из пейволла на сервере,
 * охранника роутера и вида страницы.
 *
 * Вход один на файл: он и так проверяется отдельным сценарием, а лишние входы упираются в
 * ограничитель попыток.
 */
test.describe.configure({ mode: "serial" });

test.describe("доступ к материалам курса", () => {
  let admin;
  let course;
  let lessonId;
  let page;

  test.beforeAll(async ({ browser }) => {
    admin = await tokenFor(ADMIN);
    course = await firstCourse(admin);
    lessonId = course.tree.modules[0].lessons[0].id;
    await revokeAccessFor(admin, STUDENT.email);

    page = await browser.newPage();
    await signIn(page, STUDENT);
  });

  test.afterAll(async () => {
    await revokeAccessFor(admin, STUDENT.email);
    await page.close();
  });

  test("без доступа лекция не открывается, а объясняет почему", async () => {
    await page.goto(`/lessons/${lessonId}`);

    await expect(page.getByText("Материалы курса пока закрыты")).toBeVisible();
    await expect(page.locator("video")).toHaveCount(0);
  });

  test("после выдачи доступа та же лекция открывается", async () => {
    await grantAccess(admin, course.id, STUDENT.email);

    await page.goto(`/lessons/${lessonId}`);

    await expect(page.getByText("Материалы курса пока закрыты")).toHaveCount(0);
    await expect(page.getByRole("heading").first()).toBeVisible();
  });
});
