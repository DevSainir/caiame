<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import BaseContainer from '@/core/components/BaseContainer.vue'
import { describeError } from '@/core/api/messages'
import { setPageTitle } from '@/core/page'
import LearningCrumbs from '@/features/learning/components/LearningCrumbs.vue'
import LessonRow from '@/features/learning/components/LessonRow.vue'
import { fetchModule } from '@/features/learning/api'

const route = useRoute()

const module = ref(null)
const isLoading = ref(true)
const error = ref(null)

async function load(id) {
  isLoading.value = true
  error.value = null
  try {
    module.value = await fetchModule(id)
    setPageTitle(module.value.title)
  } catch (failure) {
    error.value = failure
    module.value = null
  } finally {
    isLoading.value = false
  }
}

watch(() => route.params.id, load, { immediate: true })
</script>

<template>
  <div class="pb-14 pt-6 lg:pb-35 lg:pt-14">
    <BaseContainer>
      <p v-if="isLoading" class="py-24 text-center text-sm font-semibold text-subtle lg:text-lg">
        Загружаем модуль…
      </p>

      <div v-else-if="error" class="flex flex-col items-center gap-5 py-24">
        <p class="text-center text-sm font-semibold text-subtle lg:text-lg">
          {{
            error.status === 404
              ? 'Такого модуля нет'
              : describeError(error, 'Не удалось открыть модуль')
          }}
        </p>
        <RouterLink class="text-base font-bold text-accent" to="/">Ко всем курсам</RouterLink>
      </div>

      <template v-else-if="module">
        <!-- Курс над карточкой — как в мобильном макете; на десктопе он же служит
             единственным путём назад. -->
        <div class="lg:hidden">
          <LearningCrumbs :course="module.course" />
        </div>
        <RouterLink
          class="hidden text-base font-medium text-muted lg:block"
          :to="`/courses/${module.course.slug}`"
        >
          ← {{ module.course.title }}
        </RouterLink>

        <div class="mt-5 rounded-xl bg-page px-4 py-5 lg:mt-8 lg:px-15 lg:py-14">
          <h1 class="text-2xl font-bold text-primary-500 lg:text-3xl lg:text-ink">
            {{ module.title }}
          </h1>
          <p class="pt-3 text-sm font-medium text-subtle lg:pt-4">{{ module.summary }}</p>
          <p
            v-if="module.description !== module.summary"
            class="max-w-xl pt-5 text-sm font-medium leading-relaxed text-muted lg:pt-8 lg:text-base"
          >
            {{ module.description }}
          </p>
        </div>

        <h2 class="pt-8 text-xl font-bold text-ink lg:pt-14 lg:text-2xl lg:text-accent">
          Лекции модуля:
        </h2>

        <!-- Список лекций открыт всем: это часть того, что курс предлагает. Закрыт сам
             материал, и строка говорит об этом прямо, а не ведёт в отказ. -->
        <p
          v-if="!module.has_access"
          class="mt-4 rounded-lg bg-page px-4 py-4 text-sm font-medium leading-relaxed text-muted lg:mt-6 lg:px-15 lg:py-6"
        >
          Лекции откроются, когда учебная часть запишет вас на цикл.
        </p>

        <p
          v-if="module.lessons.length === 0"
          class="py-12 text-center text-sm font-semibold text-subtle"
        >
          В этом модуле пока нет лекций
        </p>

        <!-- Телефон: карточка на лекцию. Десктоп: одна карточка со строками. -->
        <ul
          v-else
          class="mt-4 flex flex-col gap-3 lg:mt-6 lg:gap-0 lg:rounded-xl lg:bg-page lg:px-15 lg:py-4"
        >
          <li
            v-for="(lesson, index) in module.lessons"
            :key="lesson.id"
            :class="index > 0 ? 'lg:border-t lg:border-subtle' : ''"
          >
            <LessonRow :has-access="module.has_access" :lesson="lesson" />
          </li>
        </ul>
      </template>
    </BaseContainer>
  </div>
</template>
