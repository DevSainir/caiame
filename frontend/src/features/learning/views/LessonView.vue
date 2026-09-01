<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseContainer from '@/core/components/BaseContainer.vue'
import IconFile from '@/core/components/icons/IconFile.vue'
import { describeError } from '@/core/api/messages'
import AccessNotice from '@/features/learning/components/AccessNotice.vue'
import LearningCrumbs from '@/features/learning/components/LearningCrumbs.vue'
import { completeLesson, fetchLesson } from '@/features/learning/api'

const route = useRoute()

const lesson = ref(null)
const isLoading = ref(true)
const isSaving = ref(false)
const error = ref(null)

const isDone = computed(() => lesson.value?.status === 'done')
// 402 — это не поломка, а закрытый доступ: экран для него отдельный.
const isLocked = computed(() => error.value?.status === 402)

async function load(id) {
  isLoading.value = true
  error.value = null
  try {
    lesson.value = await fetchLesson(id)
  } catch (failure) {
    error.value = failure
    lesson.value = null
  } finally {
    isLoading.value = false
  }
}

/**
 * Отметить лекцию пройденной.
 *
 * Отметка идемпотентна на сервере, поэтому повторное нажатие безопасно; кнопка всё равно
 * блокируется на время запроса, чтобы двойной клик не отправил два.
 */
async function markDone() {
  if (isSaving.value || isDone.value) return
  isSaving.value = true
  try {
    const result = await completeLesson(lesson.value.id)
    lesson.value = { ...lesson.value, status: result.status }
  } catch {
    // Материал уже открыт: оставляем кнопку, чтобы попробовать ещё раз.
  } finally {
    isSaving.value = false
  }
}

watch(() => route.params.id, load, { immediate: true })
</script>

<template>
  <div class="pb-14 pt-6 lg:pb-35 lg:pt-14">
    <BaseContainer>
      <p v-if="isLoading" class="py-24 text-center text-sm font-semibold text-subtle lg:text-lg">
        Загружаем лекцию…
      </p>

      <AccessNotice v-else-if="isLocked" />

      <div v-else-if="error" class="flex flex-col items-center gap-5 py-24">
        <p class="text-center text-sm font-semibold text-subtle lg:text-lg">
          {{
            error.status === 404
              ? 'Такой лекции нет'
              : describeError(error, 'Не удалось открыть лекцию')
          }}
        </p>
        <RouterLink class="text-base font-bold text-accent" to="/">Ко всем курсам</RouterLink>
      </div>

      <template v-else-if="lesson">
        <LearningCrumbs :course="lesson.course" :module="lesson.module" />

        <div class="mt-5 rounded-xl bg-page px-4 py-5 lg:mt-8 lg:px-15 lg:py-14">
          <h1 class="max-w-xl text-xl font-bold text-ink lg:text-3xl">{{ lesson.title }}</h1>
          <p class="max-w-xl pt-4 text-sm font-medium leading-relaxed text-muted lg:pt-6">
            {{ lesson.description }}
          </p>

          <hr class="mt-6 border-subtle lg:mt-10" />

          <!-- Обычный <video> с родными кнопками браузера: библиотека-плеер весит больше
               всего остального кода вместе взятого, а даёт здесь только скорость
               воспроизведения. Ссылка приходит с сервера и живёт ограниченное время. -->
          <div
            v-if="lesson.kind === 'video'"
            class="flex flex-col items-center gap-6 pt-6 lg:pt-14"
          >
            <video
              v-if="lesson.material_url"
              class="aspect-video w-full rounded-md bg-neutral-900"
              controls
              controlsList="nodownload"
              preload="metadata"
              :src="lesson.material_url"
            ></video>
            <div
              v-else
              class="flex aspect-video w-full items-center justify-center rounded-md bg-neutral-100"
            >
              <p class="text-sm font-medium text-subtle">Видео пока не загружено</p>
            </div>
            <BaseButton :disabled="isDone || isSaving" size="sm" @click="markDone">
              {{ isDone ? 'Выполнено' : 'Пометить, как выполненное' }}
            </BaseButton>
          </div>

          <!-- Файл. Ссылка на материал приходит с сервера; когда её ещё нет, кнопка
               выключена, а не ведёт в никуда. -->
          <div
            v-else
            class="mt-6 flex flex-col gap-5 rounded-lg border border-subtle p-4 lg:mt-14 lg:flex-row lg:items-center lg:justify-between lg:gap-8 lg:p-6"
          >
            <div class="flex items-center gap-4">
              <IconFile class="w-6 shrink-0 text-disabled" />
              <div class="flex flex-col gap-2">
                <p class="text-sm font-medium text-ink lg:text-base">{{ lesson.title }}</p>
                <p class="text-xs font-medium text-subtle">PDF</p>
              </div>
            </div>

            <div class="flex flex-col gap-3 lg:flex-row lg:gap-4">
              <a
                v-if="lesson.material_url"
                class="inline-flex items-center justify-center rounded-sm bg-accent px-10 py-2 text-xs font-bold text-inverse"
                :href="lesson.material_url"
                rel="noopener"
                target="_blank"
              >
                Открыть материал
              </a>
              <BaseButton v-else disabled size="sm">Материал пока не загружен</BaseButton>
              <BaseButton :disabled="isDone || isSaving" size="sm" @click="markDone">
                {{ isDone ? 'Выполнено' : 'Пометить, как выполненное' }}
              </BaseButton>
            </div>
          </div>
        </div>
      </template>
    </BaseContainer>
  </div>
</template>
