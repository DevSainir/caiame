<script setup>
import { onMounted, ref } from 'vue'
import { describeError } from '@/core/api/messages'
import { fetchMyCourses } from '@/features/profile/api'

const courses = ref([])
const isLoading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    courses.value = await fetchMyCourses()
  } catch (failure) {
    error.value = describeError(failure, 'Не удалось загрузить ваши курсы')
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <section class="flex w-full flex-col gap-5">
    <h2 class="text-xl font-semibold text-ink lg:text-2xl">Мои курсы</h2>

    <p v-if="isLoading" class="text-sm font-medium text-subtle">Загружаем…</p>

    <p v-else-if="error" class="text-sm font-medium text-subtle">{{ error }}</p>

    <div v-else-if="courses.length === 0" class="flex flex-col gap-3">
      <p class="text-sm font-medium leading-relaxed text-muted">
        Вы ещё не начали ни одного курса. Как только учебная часть откроет вам цикл, он появится
        здесь.
      </p>
      <RouterLink class="text-base font-bold text-accent" to="/">Посмотреть курсы</RouterLink>
    </div>

    <ul v-else class="flex flex-col gap-4">
      <li
        v-for="course in courses"
        :key="course.id"
        class="flex flex-col gap-4 rounded-lg border border-subtle p-4 lg:flex-row lg:items-center lg:gap-6 lg:p-5"
      >
        <img
          v-if="course.cover_url"
          alt=""
          class="h-20 w-full rounded-md object-cover lg:w-35"
          :src="course.cover_url"
        />

        <div class="min-w-0 flex-1">
          <p class="text-sm font-bold text-ink lg:text-base">{{ course.title }}</p>

          <div class="flex items-center gap-3 pt-3">
            <span class="h-2 w-full max-w-25 rounded-full bg-neutral-100">
              <span
                class="block h-full rounded-full"
                :class="course.is_completed ? 'bg-success-500' : 'bg-accent'"
                :style="{ width: `${course.progress_percent}%` }"
              ></span>
            </span>
            <span class="text-xs font-medium text-muted">{{ course.progress_percent }} %</span>
            <span v-if="course.is_completed" class="text-xs font-semibold text-success-600">
              пройден
            </span>
          </div>

          <p v-if="!course.has_access" class="pt-3 text-2xs font-medium text-subtle">
            Доступ к материалам сейчас закрыт. Всё пройденное сохранено — если доступ вернут, вы
            продолжите с того же места.
          </p>
        </div>

        <div class="flex shrink-0 gap-4">
          <RouterLink
            v-if="course.has_access && course.continue_lesson_id"
            class="text-sm font-semibold text-accent"
            :to="`/lessons/${course.continue_lesson_id}`"
          >
            Продолжить
          </RouterLink>
          <RouterLink class="text-sm font-semibold text-muted" :to="`/courses/${course.slug}`">
            О курсе
          </RouterLink>
        </div>
      </li>
    </ul>
  </section>
</template>
