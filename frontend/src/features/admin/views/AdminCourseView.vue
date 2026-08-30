<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseContainer from '@/core/components/BaseContainer.vue'
import AdminUnitRow from '@/features/admin/components/AdminUnitRow.vue'
import {
  addLesson,
  addUnit,
  deleteLesson,
  deleteUnit,
  fetchCourse,
  moveLesson,
  moveUnit,
  setCourseStatus,
  updateLesson,
  updateUnit,
} from '@/features/admin/api'

const route = useRoute()

const course = ref(null)
const isLoading = ref(true)
const isBusy = ref(false)
const error = ref(null)
const notice = ref('')

const courseId = computed(() => route.params.id)
const isPublished = computed(() => course.value?.status === 'published')

async function load() {
  isLoading.value = true
  error.value = null
  try {
    course.value = await fetchCourse(courseId.value)
  } catch (failure) {
    error.value = failure
  } finally {
    isLoading.value = false
  }
}

/**
 * Один шаг редактирования.
 *
 * После любой правки программа перечитывается целиком: позиции и статусы считает сервер,
 * и собирать их второй раз на клиенте — верный способ показать не то, что в базе.
 */
async function step(action, message = '') {
  if (isBusy.value) return
  isBusy.value = true
  notice.value = ''
  try {
    await action()
    course.value = await fetchCourse(courseId.value)
    notice.value = message
  } catch (failure) {
    notice.value =
      failure.status === 409
        ? 'Сначала уберите из модуля лекции — вместе с ним они бы исчезли'
        : 'Не удалось сохранить. Проверьте соединение и попробуйте ещё раз'
  } finally {
    isBusy.value = false
  }
}

const ask = (question, fallback) => window.prompt(question, fallback)?.trim()

function createUnit(kind) {
  const title = ask(`Название (${kind === 'module' ? 'модуль' : 'работа'})`, '')
  if (!title) return
  step(() => addUnit(courseId.value, { title, summary: '', kind }), 'Добавлено')
}

function renameUnit(unit) {
  const title = ask('Название', unit.title)
  if (!title) return
  const summary = ask('Короткое описание', unit.summary) ?? unit.summary
  step(() => updateUnit(courseId.value, unit.id, { title, summary }), 'Сохранено')
}

function createLesson(unit) {
  const title = ask('Название лекции', '')
  if (!title) return
  const kind = ask('Тип: video или pdf', 'video')
  step(
    () =>
      addLesson(courseId.value, unit.id, {
        title,
        description: '',
        kind: kind === 'pdf' ? 'pdf' : 'video',
        duration_minutes: 0,
        is_required: true,
      }),
    'Лекция добавлена',
  )
}

function editLesson(lesson) {
  const title = ask('Название лекции', lesson.title)
  if (!title) return
  const minutes = Number(ask('Длительность, мин', String(lesson.duration_minutes)) ?? 0)
  step(
    () =>
      updateLesson(courseId.value, lesson.id, {
        title,
        description: '',
        kind: lesson.kind,
        duration_minutes: Number.isFinite(minutes) ? minutes : 0,
        is_required: lesson.is_required,
      }),
    'Сохранено',
  )
}

function removeLesson(lesson) {
  if (!window.confirm(`Убрать лекцию «${lesson.title}» из программы?`)) return
  step(() => deleteLesson(courseId.value, lesson.id), 'Лекция убрана из программы')
}

watch(courseId, load, { immediate: true })
</script>

<template>
  <div class="py-8 lg:py-14">
    <BaseContainer>
      <p v-if="isLoading" class="py-24 text-center text-sm font-semibold text-subtle">
        Загружаем программу…
      </p>

      <div v-else-if="error" class="flex flex-col items-center gap-5 py-24">
        <p class="text-sm font-semibold text-subtle">
          {{ error.status === 404 ? 'Такого курса нет' : 'Не удалось загрузить курс' }}
        </p>
        <RouterLink class="text-base font-bold text-accent" to="/admin">К списку курсов</RouterLink>
      </div>

      <div v-else-if="course" class="overflow-hidden rounded-xl border border-subtle bg-page">
        <header class="border-b border-subtle px-5 py-5">
          <RouterLink class="text-2xs font-medium text-subtle" to="/admin">← Курсы</RouterLink>
          <div class="flex flex-wrap items-center justify-between gap-4 pt-2">
            <h1 class="text-2xl font-bold text-ink">{{ course.title }}</h1>
            <BaseButton
              :disabled="isBusy"
              size="sm"
              :variant="isPublished ? 'dark' : 'primary'"
              @click="
                step(
                  () => setCourseStatus(courseId, isPublished ? 'draft' : 'published'),
                  isPublished ? 'Курс убран из каталога' : 'Курс опубликован',
                )
              "
            >
              {{ isPublished ? 'Снять с публикации' : 'Опубликовать' }}
            </BaseButton>
          </div>
          <p class="pt-3 text-xs font-medium text-subtle">
            {{ isPublished ? 'Опубликован — правки видны студентам сразу' : 'Черновик' }}
          </p>
        </header>

        <p
          v-if="notice"
          class="border-b border-subtle bg-subtle px-5 py-3 text-xs font-semibold text-ink"
        >
          {{ notice }}
        </p>

        <section class="p-4 lg:p-5">
          <div class="flex items-center justify-between gap-4 pb-4">
            <h2 class="text-lg font-bold text-ink">Модули</h2>
            <button
              class="text-sm font-semibold text-accent disabled:opacity-50"
              :disabled="isBusy"
              type="button"
              @click="createUnit('module')"
            >
              + Модуль
            </button>
          </div>

          <div class="rounded-lg border border-subtle">
            <AdminUnitRow
              v-for="unit in course.modules"
              :key="unit.id"
              :is-busy="isBusy"
              :unit="unit"
              @add-lesson="createLesson(unit)"
              @edit-lesson="editLesson"
              @move="step(() => moveUnit(courseId, unit.id, $event))"
              @move-lesson="
                (lesson, direction) => step(() => moveLesson(courseId, lesson.id, direction))
              "
              @remove="step(() => deleteUnit(courseId, unit.id), 'Модуль удалён')"
              @remove-lesson="removeLesson"
              @rename="renameUnit(unit)"
            />
            <p
              v-if="course.modules.length === 0"
              class="px-5 py-8 text-center text-sm font-medium text-subtle"
            >
              В курсе пока нет модулей
            </p>
          </div>

          <div class="flex items-center justify-between gap-4 pb-4 pt-8">
            <h2 class="text-lg font-bold text-ink">Работы курса</h2>
            <div class="flex gap-4">
              <button
                class="text-sm font-semibold text-accent disabled:opacity-50"
                :disabled="isBusy"
                type="button"
                @click="createUnit('assignment')"
              >
                + Задание
              </button>
              <button
                class="text-sm font-semibold text-accent disabled:opacity-50"
                :disabled="isBusy"
                type="button"
                @click="createUnit('test')"
              >
                + Тестирование
              </button>
            </div>
          </div>

          <div class="rounded-lg border border-subtle">
            <AdminUnitRow
              v-for="unit in course.activities"
              :key="unit.id"
              :is-busy="isBusy"
              :unit="unit"
              @move="step(() => moveUnit(courseId, unit.id, $event))"
              @remove="step(() => deleteUnit(courseId, unit.id), 'Работа удалена')"
              @rename="renameUnit(unit)"
            />
            <p
              v-if="course.activities.length === 0"
              class="px-5 py-8 text-center text-sm font-medium text-subtle"
            >
              В курсе пока нет работ
            </p>
          </div>
        </section>
      </div>

      <p class="max-w-xl pt-4 text-xs font-medium leading-relaxed text-subtle">
        Убранная лекция исчезает из программы и из знаменателя процента, но остаётся в истории тех,
        кто её прошёл: их прогресс не откатится.
      </p>
    </BaseContainer>
  </div>
</template>
