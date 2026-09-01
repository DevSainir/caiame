<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { describeError } from '@/core/api/messages'
import BaseButton from '@/core/components/BaseButton.vue'
import { useNotificationStore } from '@/core/notifications/store'
import AdminCourseForm from '@/features/admin/components/AdminCourseForm.vue'
import AdminFaqSection from '@/features/admin/components/AdminFaqSection.vue'
import AdminLessonForm from '@/features/admin/components/AdminLessonForm.vue'
import AdminProgramme from '@/features/admin/components/AdminProgramme.vue'
import AdminShell from '@/features/admin/components/AdminShell.vue'
import AdminUnitForm from '@/features/admin/components/AdminUnitForm.vue'
import {
  addLesson,
  addUnit,
  deleteCourse,
  deleteLesson,
  deleteUnit,
  fetchCourse,
  fetchCourseCard,
  fetchTaxonomies,
  moveLesson,
  moveUnit,
  setCourseStatus,
  updateCourse,
  updateUnit,
} from '@/features/admin/api'

const route = useRoute()
const router = useRouter()
const notifications = useNotificationStore()

const course = ref(null)
const card = ref(null)
const taxonomies = ref({ specializations: [], accreditations: [] })
const isLoading = ref(true)
const isBusy = ref(false)
const loadError = ref('')
const formError = ref('')

// Одна форма на экране за раз: {kind: 'course' | 'unit' | 'lesson', ...}
const dialog = ref(null)

const courseId = computed(() => route.params.id)
const isPublished = computed(() => course.value?.status === 'published')

async function load() {
  isLoading.value = true
  loadError.value = ''
  try {
    course.value = await fetchCourse(courseId.value)
  } catch (failure) {
    loadError.value = describeError(failure, 'Не удалось открыть курс')
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
  try {
    await action()
    course.value = await fetchCourse(courseId.value)
    dialog.value = null
    if (message) notifications.notify(message)
  } catch (failure) {
    formError.value = describeError(failure, 'Не удалось сохранить')
    if (!dialog.value) notifications.notify(formError.value, 'error')
  } finally {
    isBusy.value = false
  }
}

async function openCourseForm() {
  formError.value = ''
  try {
    card.value = await fetchCourseCard(courseId.value)
    if (!taxonomies.value.specializations.length) taxonomies.value = await fetchTaxonomies()
    dialog.value = { kind: 'course' }
  } catch (failure) {
    notifications.notify(describeError(failure, 'Не удалось открыть карточку курса'), 'error')
  }
}

function openUnitForm(unit, kind) {
  formError.value = ''
  dialog.value = { kind: 'unit', unit, unitKind: kind }
}

function openLessonForm(unit) {
  formError.value = ''
  dialog.value = { kind: 'lesson', unit }
}

function saveUnit(payload) {
  const { unit, unitKind } = dialog.value
  if (unit) {
    step(() => updateUnit(courseId.value, unit.id, payload), 'Сохранено')
    return
  }
  step(() => addUnit(courseId.value, { ...payload, kind: unitKind }), 'Добавлено')
}

function saveLesson(payload) {
  const { unit } = dialog.value
  step(() => addLesson(courseId.value, unit.id, payload), 'Лекция добавлена')
}

function saveCourse(payload) {
  step(() => updateCourse(courseId.value, payload), 'Курс сохранён')
}

function removeLesson(lesson) {
  if (!window.confirm(`Убрать лекцию «${lesson.title}» из программы?`)) return
  step(() => deleteLesson(courseId.value, lesson.id), 'Лекция убрана из программы')
}

async function removeCourse() {
  if (!window.confirm('Удалить курс целиком? Это нельзя отменить')) return
  isBusy.value = true
  try {
    await deleteCourse(courseId.value)
    notifications.notify('Курс удалён')
    router.push('/admin')
  } catch (failure) {
    notifications.notify(describeError(failure, 'Не удалось удалить курс'), 'error')
  } finally {
    isBusy.value = false
  }
}

watch(courseId, load, { immediate: true })
</script>

<template>
  <AdminShell
    :subtitle="isPublished ? 'Опубликован — правки видны студентам сразу' : 'Черновик'"
    :title="course?.title ?? 'Курс'"
  >
    <template #breadcrumb>
      <RouterLink class="text-2xs font-medium text-subtle" to="/admin">← Курсы</RouterLink>
    </template>

    <template #actions>
      <button
        class="text-sm font-semibold text-accent disabled:opacity-50"
        :disabled="isBusy || isLoading"
        type="button"
        @click="openCourseForm"
      >
        Карточка курса
      </button>
      <button
        v-if="!isPublished"
        class="text-sm font-semibold text-danger-500 disabled:opacity-50"
        :disabled="isBusy || isLoading"
        type="button"
        @click="removeCourse"
      >
        Удалить
      </button>
      <BaseButton
        :disabled="isBusy || isLoading"
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
    </template>

    <p v-if="isLoading" class="py-24 text-center text-sm font-semibold text-subtle">
      Загружаем программу…
    </p>

    <div v-else-if="loadError" class="flex flex-col items-center gap-5 py-24">
      <p class="text-sm font-semibold text-subtle">{{ loadError }}</p>
      <RouterLink class="text-base font-bold text-accent" to="/admin">К списку курсов</RouterLink>
    </div>

    <AdminProgramme
      v-else-if="course"
      :course="course"
      :course-id="courseId"
      :is-busy="isBusy"
      @add-lesson="openLessonForm"
      @add-unit="openUnitForm(null, $event)"
      @edit-unit="openUnitForm"
      @move-lesson="(lesson, direction) => step(() => moveLesson(courseId, lesson.id, direction))"
      @move-unit="(unit, direction) => step(() => moveUnit(courseId, unit.id, direction))"
      @remove-lesson="removeLesson"
      @remove-unit="
        (unit) =>
          step(
            () => deleteUnit(courseId, unit.id),
            unit.kind === 'module' ? 'Модуль удалён' : 'Работа удалена',
          )
      "
    />

    <AdminFaqSection v-if="course" :course-id="courseId" />

    <p class="border-t border-subtle px-5 py-4 text-xs font-medium leading-relaxed text-subtle">
      Убранная лекция исчезает из программы и из подсчёта процента, но остаётся у тех, кто её уже
      прошёл: их прогресс не откатится.
    </p>

    <AdminCourseForm
      v-if="dialog?.kind === 'course'"
      :accreditations="taxonomies.accreditations"
      :course="card"
      :error="formError"
      :is-busy="isBusy"
      :specializations="taxonomies.specializations"
      @close="dialog = null"
      @submit="saveCourse"
    />
    <AdminUnitForm
      v-else-if="dialog?.kind === 'unit'"
      :is-busy="isBusy"
      :kind="dialog.unitKind"
      :unit="dialog.unit"
      @close="dialog = null"
      @submit="saveUnit"
    />
    <AdminLessonForm
      v-else-if="dialog?.kind === 'lesson'"
      :is-busy="isBusy"
      @close="dialog = null"
      @submit="saveLesson"
    />
  </AdminShell>
</template>
