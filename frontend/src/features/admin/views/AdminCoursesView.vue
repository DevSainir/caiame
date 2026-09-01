<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { describeError } from '@/core/api/messages'
import BaseButton from '@/core/components/BaseButton.vue'
import { useNotificationStore } from '@/core/notifications/store'
import AdminCourseForm from '@/features/admin/components/AdminCourseForm.vue'
import AdminShell from '@/features/admin/components/AdminShell.vue'
import { createCourse, fetchCourses, fetchTaxonomies } from '@/features/admin/api'

const router = useRouter()
const notifications = useNotificationStore()

const STATUS_LABELS = { draft: 'Черновик', published: 'Опубликован', archived: 'В архиве' }

const courses = ref([])
const specializations = ref([])
const accreditations = ref([])
const isLoading = ref(true)
const isBusy = ref(false)
const loadError = ref('')
const formError = ref('')
const isFormOpen = ref(false)

const drafts = computed(() => courses.value.filter((course) => course.status !== 'published'))
const subtitle = computed(
  () => `${courses.value.length} курсов, из них черновиков: ${drafts.value.length}`,
)

async function load() {
  isLoading.value = true
  loadError.value = ''
  try {
    courses.value = await fetchCourses()
  } catch (failure) {
    loadError.value = describeError(failure, 'Не удалось загрузить курсы')
  } finally {
    isLoading.value = false
  }
}

async function create(payload) {
  isBusy.value = true
  formError.value = ''
  try {
    const course = await createCourse(payload)
    notifications.notify('Курс создан. Он останется черновиком, пока вы его не опубликуете')
    router.push(`/admin/courses/${course.id}`)
  } catch (failure) {
    formError.value = describeError(failure, 'Не удалось создать курс')
  } finally {
    isBusy.value = false
  }
}

/**
 * Открыть форму нового курса.
 *
 * Справочники грузятся до открытия, а не после: форма подставляет первое направление в
 * момент появления, и с пустым списком поле остаётся незаполненным, а сохранение молча
 * не проходит.
 */
async function openForm() {
  try {
    if (!specializations.value.length) {
      const filters = await fetchTaxonomies()
      specializations.value = filters.specializations
      accreditations.value = filters.accreditations
    }
    isFormOpen.value = true
  } catch (failure) {
    notifications.notify(describeError(failure, 'Не удалось открыть форму'), 'error')
  }
}

onMounted(load)
</script>

<template>
  <AdminShell :subtitle="subtitle" title="Курсы">
    <template #actions>
      <BaseButton :disabled="isBusy" size="sm" @click="openForm">Новый курс</BaseButton>
    </template>

    <p v-if="isLoading" class="py-24 text-center text-sm font-semibold text-subtle">
      Загружаем курсы…
    </p>

    <div v-else-if="loadError" class="flex flex-col items-center gap-5 py-24">
      <p class="text-sm font-semibold text-subtle">{{ loadError }}</p>
      <button class="text-base font-bold text-accent" type="button" @click="load">
        Попробовать ещё раз
      </button>
    </div>

    <!-- Телефон: карточки. Десктоп: таблица. -->
    <template v-else>
      <ul class="flex flex-col gap-3 p-4 lg:hidden">
        <li v-for="course in courses" :key="course.id">
          <RouterLink
            class="flex flex-col gap-2 rounded-lg border border-subtle p-4"
            :to="`/admin/courses/${course.id}`"
          >
            <span class="text-sm font-bold text-ink">{{ course.title }}</span>
            <span class="text-2xs font-medium text-subtle">
              {{ course.specialization }} · {{ course.credit_hours }} ч ·
              {{ course.modules }} модулей, {{ course.lessons }} лекций
            </span>
            <span
              class="self-start rounded-sm px-3 py-2 text-2xs font-semibold"
              :class="
                course.status === 'published'
                  ? 'bg-success-500 text-inverse'
                  : 'border border-neutral-400 text-subtle'
              "
            >
              {{ STATUS_LABELS[course.status] }}
            </span>
          </RouterLink>
        </li>
      </ul>

      <table class="hidden w-full text-left lg:table">
        <thead>
          <tr class="border-b border-subtle bg-subtle">
            <th class="px-5 py-3 text-2xs font-semibold uppercase text-subtle">Курс</th>
            <th class="px-4 py-3 text-2xs font-semibold uppercase text-subtle">Часы</th>
            <th class="px-4 py-3 text-2xs font-semibold uppercase text-subtle">Программа</th>
            <th class="px-4 py-3 text-2xs font-semibold uppercase text-subtle">Статус</th>
            <th class="px-5 py-3"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="course in courses" :key="course.id" class="border-b border-subtle">
            <td class="px-5 py-5">
              <p class="text-sm font-bold text-ink">{{ course.title }}</p>
              <p class="pt-2 text-2xs font-medium text-subtle">{{ course.specialization }}</p>
            </td>
            <td class="px-4 py-5 text-sm font-medium text-muted">{{ course.credit_hours }}</td>
            <td class="px-4 py-5 text-sm font-medium text-muted">
              {{ course.modules }} модулей · {{ course.lessons }} лекций
            </td>
            <td class="px-4 py-5">
              <span
                class="rounded-sm px-3 py-2 text-2xs font-semibold"
                :class="
                  course.status === 'published'
                    ? 'bg-success-500 text-inverse'
                    : 'border border-neutral-400 text-subtle'
                "
              >
                {{ STATUS_LABELS[course.status] }}
              </span>
            </td>
            <td class="px-5 py-5 text-right">
              <RouterLink
                class="text-sm font-semibold text-accent"
                :to="`/admin/courses/${course.id}`"
              >
                Открыть
              </RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </template>

    <p class="border-t border-subtle px-5 py-4 text-xs font-medium leading-relaxed text-subtle">
      Черновик виден только здесь: в каталоге и по прямой ссылке студенты его не найдут.
    </p>

    <AdminCourseForm
      v-if="isFormOpen"
      :accreditations="accreditations"
      :error="formError"
      :is-busy="isBusy"
      :specializations="specializations"
      @close="isFormOpen = false"
      @submit="create"
    />
  </AdminShell>
</template>
