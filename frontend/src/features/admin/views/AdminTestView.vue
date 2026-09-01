<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { describeError } from '@/core/api/messages'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseField from '@/core/components/BaseField.vue'
import { formatPoints } from '@/core/format'
import { useNotificationStore } from '@/core/notifications/store'
import AdminQuestionForm from '@/features/admin/components/AdminQuestionForm.vue'
import AdminShell from '@/features/admin/components/AdminShell.vue'
import {
  addQuestion,
  deleteQuestion,
  fetchTest,
  replaceQuestion,
  updateQuestion,
  updateTest,
} from '@/features/admin/api'

const route = useRoute()
const notifications = useNotificationStore()

const INPUT =
  'rounded-lg border border-neutral-400 bg-page px-5 py-4 text-sm font-medium text-ink outline-none'

const test = ref(null)
const settings = ref({ passing_score: 0, max_attempts: null })
const isLoading = ref(true)
const isBusy = ref(false)
const loadError = ref('')
const formError = ref('')
const dialog = ref(null)

const courseId = computed(() => route.params.courseId)
const unitId = computed(() => route.params.unitId)
const subtitle = computed(() =>
  test.value ? `${test.value.questions.length} вопросов, всего ${test.value.max_score} баллов` : '',
)

function apply(data) {
  test.value = data
  settings.value = { passing_score: data.passing_score, max_attempts: data.max_attempts }
}

async function load() {
  isLoading.value = true
  loadError.value = ''
  try {
    apply(await fetchTest(courseId.value, unitId.value))
  } catch (failure) {
    loadError.value = describeError(failure, 'Не удалось открыть тестирование')
  } finally {
    isLoading.value = false
  }
}

async function step(action, message) {
  if (isBusy.value) return
  isBusy.value = true
  formError.value = ''
  try {
    apply(await action())
    dialog.value = null
    if (message) notifications.notify(message)
  } catch (failure) {
    formError.value = describeError(failure, 'Не удалось сохранить')
    if (!dialog.value) notifications.notify(formError.value, 'error')
  } finally {
    isBusy.value = false
  }
}

function saveSettings() {
  step(
    () =>
      updateTest(courseId.value, unitId.value, {
        passing_score: Number(settings.value.passing_score) || 0,
        max_attempts: settings.value.max_attempts ? Number(settings.value.max_attempts) : null,
      }),
    'Настройки сохранены',
  )
}

function saveQuestion(payload) {
  const { question, isReplacement } = dialog.value
  if (!question) {
    step(() => addQuestion(courseId.value, unitId.value, payload), 'Вопрос добавлен')
    return
  }
  if (isReplacement) {
    step(
      () => replaceQuestion(courseId.value, unitId.value, question.id, payload),
      'Вопрос заменён новым',
    )
    return
  }
  step(() => updateQuestion(courseId.value, unitId.value, question.id, payload), 'Вопрос сохранён')
}

function removeQuestion(question) {
  if (!window.confirm('Убрать вопрос из тестирования?')) return
  step(() => deleteQuestion(courseId.value, unitId.value, question.id), 'Вопрос убран')
}

watch([courseId, unitId], load, { immediate: true })
</script>

<template>
  <AdminShell :subtitle="subtitle" :title="test?.title ?? 'Тестирование'">
    <template #breadcrumb>
      <RouterLink class="text-2xs font-medium text-subtle" :to="`/admin/courses/${courseId}`">
        ← Программа курса
      </RouterLink>
    </template>

    <template #actions>
      <BaseButton
        :disabled="isBusy || isLoading"
        size="sm"
        @click="dialog = { question: null, isReplacement: false }"
      >
        Новый вопрос
      </BaseButton>
    </template>

    <p v-if="isLoading" class="py-24 text-center text-sm font-semibold text-subtle">
      Загружаем тестирование…
    </p>

    <p v-else-if="loadError" class="py-24 text-center text-sm font-semibold text-subtle">
      {{ loadError }}
    </p>

    <template v-else-if="test">
      <div class="flex flex-wrap items-end gap-4 border-b border-subtle p-5">
        <BaseField label="Проходной балл">
          <input v-model="settings.passing_score" :class="INPUT" min="0" type="number" />
        </BaseField>
        <BaseField hint="Пусто — попытки не ограничены" label="Попыток">
          <input v-model="settings.max_attempts" :class="INPUT" min="1" type="number" />
        </BaseField>
        <button
          class="pb-4 text-sm font-semibold text-accent disabled:opacity-50"
          :disabled="isBusy"
          type="button"
          @click="saveSettings"
        >
          Сохранить настройки
        </button>
      </div>

      <ol class="flex flex-col">
        <li
          v-for="question in test.questions"
          :key="question.id"
          class="border-b border-subtle p-5"
        >
          <div class="flex flex-wrap items-start justify-between gap-4">
            <p class="min-w-0 flex-1 text-sm font-bold text-ink">
              {{ question.position }}. {{ question.text }}
            </p>
            <div class="flex shrink-0 items-center gap-4">
              <span class="text-2xs font-medium text-subtle">
                {{ formatPoints(question.points) }} ·
                {{ question.kind === 'single' ? 'один ответ' : 'несколько ответов' }}
              </span>
              <button
                class="text-sm font-semibold text-accent disabled:opacity-50"
                :disabled="isBusy"
                type="button"
                @click="dialog = { question, isReplacement: question.is_answered }"
              >
                {{ question.is_answered ? 'Заменить новым' : 'Изменить' }}
              </button>
              <button
                class="text-sm font-semibold text-danger-500 disabled:opacity-50"
                :disabled="isBusy"
                type="button"
                @click="removeQuestion(question)"
              >
                Убрать
              </button>
            </div>
          </div>

          <ul class="flex flex-col gap-2 pt-4">
            <li
              v-for="option in question.options"
              :key="option.id"
              class="flex items-center gap-3 text-sm font-medium"
              :class="option.is_correct ? 'text-ink' : 'text-muted'"
            >
              <span
                class="h-4 w-4 shrink-0 rounded-xs border"
                :class="
                  option.is_correct ? 'border-success-600 bg-success-500' : 'border-neutral-400'
                "
              ></span>
              {{ option.text }}
            </li>
          </ul>

          <p v-if="question.is_answered" class="pt-3 text-2xs font-medium text-subtle">
            На этот вопрос уже отвечали: его можно заменить новым, но не переписать — иначе
            выставленные баллы перестанут сходиться с тем, что видел студент.
          </p>
        </li>
      </ol>

      <p
        v-if="test.questions.length === 0"
        class="py-16 text-center text-sm font-medium text-subtle"
      >
        В тестировании пока нет вопросов
      </p>
    </template>

    <AdminQuestionForm
      v-if="dialog"
      :error="formError"
      :is-busy="isBusy"
      :is-replacement="dialog.isReplacement"
      :question="dialog.question"
      @close="dialog = null"
      @submit="saveQuestion"
    />
  </AdminShell>
</template>
