<script setup>
import { computed, onMounted, ref } from 'vue'
import BaseContainer from '@/core/components/BaseContainer.vue'
import { fetchCourses } from '@/features/admin/api'

const STATUS_LABELS = { draft: 'Черновик', published: 'Опубликован', archived: 'В архиве' }

const courses = ref([])
const isLoading = ref(true)
const error = ref(null)

const drafts = computed(() => courses.value.filter((course) => course.status !== 'published'))

async function load() {
  isLoading.value = true
  error.value = null
  try {
    courses.value = await fetchCourses()
  } catch (failure) {
    error.value = failure
  } finally {
    isLoading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="py-8 lg:py-14">
    <BaseContainer>
      <div class="overflow-hidden rounded-xl border border-subtle bg-page">
        <header class="flex items-center justify-between gap-4 border-b border-subtle px-5 py-5">
          <div>
            <h1 class="text-2xl font-bold text-ink">Курсы</h1>
            <p class="pt-2 text-xs font-medium text-subtle">
              {{ courses.length }} курсов, из них черновиков: {{ drafts.length }}
            </p>
          </div>
        </header>

        <p v-if="isLoading" class="py-24 text-center text-sm font-semibold text-subtle">
          Загружаем курсы…
        </p>

        <div v-else-if="error" class="flex flex-col items-center gap-5 py-24">
          <p class="text-sm font-semibold text-subtle">Не удалось загрузить курсы</p>
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
      </div>

      <p class="max-w-xl pt-4 text-xs font-medium leading-relaxed text-subtle">
        Черновик виден только здесь: на его адресе студент получает 404, а не «нет доступа», — так
        адрес курса не сообщает, что курс существует.
      </p>
    </BaseContainer>
  </div>
</template>
