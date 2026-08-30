<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseContainer from '@/core/components/BaseContainer.vue'
import LearningCrumbs from '@/features/learning/components/LearningCrumbs.vue'
import TestQuestion from '@/features/learning/components/TestQuestion.vue'
import { fetchTest, submitTest } from '@/features/learning/api'

const route = useRoute()

const test = ref(null)
const picks = ref({})
const result = ref(null)
const showResult = ref(false)
const isLoading = ref(true)
const isSending = ref(false)
const error = ref(null)
const sendError = ref(null)

const isAnswered = computed(() => Object.values(picks.value).some((ids) => ids.length > 0))
const noAttemptsLeft = computed(() => test.value?.attempts_left === 0)

async function load(id) {
  isLoading.value = true
  error.value = null
  picks.value = {}
  showResult.value = false
  try {
    test.value = await fetchTest(id)
    result.value = test.value.last_attempt
  } catch (failure) {
    error.value = failure
    test.value = null
  } finally {
    isLoading.value = false
  }
}

/**
 * Сдать попытку.
 *
 * Балл считает сервер: сюда возвращается уже проверенная попытка. Кнопка блокируется на
 * время запроса, чтобы двойной клик не потратил вторую попытку.
 */
async function send() {
  if (isSending.value || noAttemptsLeft.value) return
  isSending.value = true
  sendError.value = null
  try {
    result.value = await submitTest(route.params.id, formatAnswers())
    showResult.value = true
    test.value = await fetchTest(route.params.id)
  } catch (failure) {
    sendError.value =
      failure.status === 409 ? 'Попытки по этому тесту закончились' : 'Не удалось отправить ответы'
  } finally {
    isSending.value = false
  }
}

watch(() => route.params.id, load, { immediate: true })

function formatAnswers() {
  return Object.entries(picks.value).map(([question_id, option_ids]) => ({
    question_id,
    option_ids,
  }))
}
</script>

<template>
  <div class="pb-14 pt-6 lg:pb-35 lg:pt-14">
    <BaseContainer>
      <p v-if="isLoading" class="py-24 text-center text-sm font-semibold text-subtle lg:text-lg">
        Загружаем тестирование…
      </p>

      <div v-else-if="error" class="flex flex-col items-center gap-5 py-24">
        <p class="text-center text-sm font-semibold text-subtle lg:text-lg">
          {{ error.status === 404 ? 'Такого тестирования нет' : 'Не удалось загрузить тест' }}
        </p>
        <RouterLink class="text-base font-bold text-accent" to="/">Ко всем курсам</RouterLink>
      </div>

      <template v-else-if="test">
        <LearningCrumbs :course="test.course" :module="test.module" />

        <div class="mt-5 rounded-xl bg-page px-4 py-5 lg:mt-8 lg:px-15 lg:py-14">
          <div class="flex items-start justify-between gap-4">
            <h1 class="max-w-xl text-xl font-bold text-ink lg:text-3xl">{{ test.title }}</h1>
            <span
              class="shrink-0 rounded-sm bg-primary-50 px-3 py-2 text-2xs font-semibold uppercase text-accent lg:text-xs"
            >
              Тестирование
            </span>
          </div>
          <p class="max-w-xl pt-4 text-sm font-medium leading-relaxed text-muted lg:pt-6">
            {{ test.description }}
          </p>
          <p class="pt-3 text-xs font-medium text-subtle">
            Проходной балл: {{ test.passing_score }} из {{ test.max_score }}.
            <span v-if="test.attempts_left !== null"
              >Осталось попыток: {{ test.attempts_left }}.</span
            >
          </p>

          <hr class="mt-6 border-subtle lg:mt-10" />

          <div class="flex flex-col gap-8 pt-6 lg:gap-10 lg:pt-10">
            <TestQuestion
              v-for="question in test.questions"
              :key="question.id"
              :disabled="noAttemptsLeft"
              :question="question"
              :selected="picks[question.id] ?? []"
              @pick="picks = { ...picks, [question.id]: $event }"
            />
          </div>

          <p v-if="sendError" class="pt-6 text-sm font-semibold text-danger-500">
            {{ sendError }}
          </p>

          <div class="flex flex-col gap-3 pt-8 lg:flex-row lg:gap-4">
            <BaseButton
              :disabled="isSending || noAttemptsLeft || !isAnswered"
              size="sm"
              @click="send"
            >
              {{ isSending ? 'Отправляем…' : 'Сдать тестирование' }}
            </BaseButton>
            <BaseButton :disabled="!result" size="sm" variant="dark" @click="showResult = true">
              Показать результат
            </BaseButton>
          </div>

          <p
            v-if="showResult && result"
            class="pt-6 text-base font-bold"
            :class="result.passed ? 'text-success-600' : 'text-danger-500'"
          >
            {{ result.passed ? 'Тест сдан' : 'Тест не сдан' }}: {{ result.score }} из
            {{ result.max_score }} баллов, попытка №{{ result.number }}.
          </p>
        </div>
      </template>
    </BaseContainer>
  </div>
</template>
