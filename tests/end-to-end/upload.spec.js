import { expect, test } from '@playwright/test'
import { ADMIN, STUDENT, firstCourse, grantAccess, signIn, tokenFor } from './support.js'

/**
 * Загрузка материала лекции целиком: браузер, подпись, хранилище, подтверждение, студент.
 *
 * Этот путь заслуживает end-to-end больше любого другого, потому что он единственный, где
 * файл идёт мимо приложения. Приложение только подписывает ссылку, а дальше договариваются
 * браузер и хранилище — и ни один юнит-тест не увидит, что подпись разошлась с тем, что
 * шлёт страница: размер, тип, заголовки. Проверка заканчивается там, где ей и место, — на
 * студенте, который открывает лекцию и получает работающую ссылку.
 *
 * Файл — настоящий PDF в несколько байт: формат проверяется по первым байтам, а не по
 * имени, поэтому «просто текст с расширением .pdf» здесь не пройдёт, и это правильно.
 */
const PDF = Buffer.from('%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n', 'utf8')

// Лекция всегда одна и та же, а файл на каждом прогоне новый: иначе прогоны заполняют
// программу курса мусорными файлами, которых потом никто не уберёт.
const fileName = `rekomendacii-${Date.now()}.pdf`

test.describe.configure({ mode: 'serial' })

test.describe('материал лекции', () => {
  let admin
  let course
  let lesson
  let page

  test.beforeAll(async ({ browser }) => {
    admin = await tokenFor(ADMIN)
    course = await firstCourse(admin)
    // Раздатка, а не видео: длительность видео читает браузер из файла, и на выдуманном
    // файле она честно не читается — проверять здесь надо не это.
    lesson = course.tree.modules.flatMap((unit) => unit.lessons).find((row) => row.kind === 'pdf')
    page = await browser.newPage()
    await signIn(page, ADMIN)
  })

  test.afterAll(async () => {
    await page.close()
  })

  test('администратор загружает файл, и лекция перестаёт быть пустой', async () => {
    test.skip(!lesson, 'В программе курса нет лекции-раздатки')

    await page.goto(`/admin/courses/${course.id}/lessons/${lesson.id}`)
    await page.setInputFiles('input[type=file]', {
      name: fileName,
      mimeType: 'application/pdf',
      buffer: PDF,
    })

    // Имя своё на каждый прогон: одно и то же имя на месте означало бы «файл когда-то
    // загрузили», а проверяется «загрузился этот».
    await expect(page.getByText(fileName)).toBeVisible({ timeout: 30_000 })
  })

  test('студент с доступом получает ссылку на этот файл', async ({ browser }) => {
    test.skip(!lesson, 'В программе курса нет лекции-раздатки')

    await grantAccess(admin, course.id, STUDENT.email)
    const studentPage = await browser.newPage()
    await signIn(studentPage, STUDENT)

    await studentPage.goto(`/lessons/${lesson.id}`)

    const link = studentPage.getByRole('link', { name: 'Открыть материал' })
    await expect(link).toBeVisible()
    // Ссылка подписана и живёт ограниченное время — проверяем, что по ней действительно
    // отдаётся файл, а не что она просто есть.
    const href = await link.getAttribute('href')
    const response = await studentPage.request.get(href)
    expect(response.status()).toBe(200)
    expect((await response.body()).subarray(0, 4).toString()).toBe('%PDF')
    await studentPage.close()
  })
})
