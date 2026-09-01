<script setup>
import { onMounted, ref } from 'vue'
import { describeError } from '@/core/api/messages'
import { useNotificationStore } from '@/core/notifications/store'
import AdminFaqForm from '@/features/admin/components/AdminFaqForm.vue'
import { addFaq, deleteFaq, fetchFaq, updateFaq } from '@/features/admin/api'

const props = defineProps({
  courseId: { type: String, required: true },
})

const notifications = useNotificationStore()

const questions = ref([])
const isLoading = ref(true)
const isBusy = ref(false)
const formError = ref('')
const dialog = ref(null)

async function load() {
  isLoading.value = true
  try {
    questions.value = await fetchFaq(props.courseId)
  } catch (failure) {
    notifications.notify(describeError(failure, 'Не удалось загрузить вопросы'), 'error')
  } finally {
    isLoading.value = false
  }
}

async function step(action, message) {
  if (isBusy.value) return
  isBusy.value = true
  formError.value = ''
  try {
    questions.value = await action()
    dialog.value = null
    notifications.notify(message)
  } catch (failure) {
    formError.value = describeError(failure, 'Не удалось сохранить')
    if (!dialog.value) notifications.notify(formError.value, 'error')
  } finally {
    isBusy.value = false
  }
}

function save(payload) {
  const existing = dialog.value?.question
  if (existing) {
    step(() => updateFaq(props.courseId, existing.id, payload), 'Ответ сохранён')
    return
  }
  step(() => addFaq(props.courseId, payload), 'Вопрос добавлен')
}

function remove(question) {
  if (!window.confirm(`Убрать вопрос «${question.question}» со страницы курса?`)) return
  step(() => deleteFaq(props.courseId, question.id), 'Вопрос убран')
}

onMounted(load)
</script>

<template>
  <section class="border-t border-subtle p-4 lg:p-5">
    <div class="flex items-center justify-between gap-4 pb-4">
      <div>
        <h2 class="text-lg font-bold text-ink">Вопросы о курсе</h2>
        <p class="pt-2 text-2xs font-medium text-subtle">
          Показываются на странице курса под программой
        </p>
      </div>
      <button
        class="text-sm font-semibold text-accent disabled:opacity-50"
        :disabled="isBusy"
        type="button"
        @click="dialog = { question: null }"
      >
        + Вопрос
      </button>
    </div>

    <p v-if="isLoading" class="py-8 text-center text-sm font-medium text-subtle">Загружаем…</p>

    <p
      v-else-if="questions.length === 0"
      class="rounded-lg border border-subtle px-5 py-8 text-center text-sm font-medium text-subtle"
    >
      Вопросов пока нет — на странице курса этот блок не появится
    </p>

    <ul v-else class="flex flex-col rounded-lg border border-subtle">
      <li
        v-for="question in questions"
        :key="question.id"
        class="border-b border-subtle p-4 last:border-b-0 lg:p-5"
      >
        <div class="flex flex-wrap items-start justify-between gap-4">
          <p class="min-w-0 flex-1 text-sm font-bold text-ink">{{ question.question }}</p>
          <div class="flex shrink-0 gap-4">
            <button
              class="text-sm font-semibold text-accent disabled:opacity-50"
              :disabled="isBusy"
              type="button"
              @click="dialog = { question }"
            >
              Изменить
            </button>
            <button
              class="text-sm font-semibold text-danger-500 disabled:opacity-50"
              :disabled="isBusy"
              type="button"
              @click="remove(question)"
            >
              Убрать
            </button>
          </div>
        </div>
        <p class="pt-2 text-sm font-medium leading-relaxed text-muted">{{ question.answer }}</p>
      </li>
    </ul>

    <AdminFaqForm
      v-if="dialog"
      :error="formError"
      :is-busy="isBusy"
      :question="dialog.question"
      @close="dialog = null"
      @submit="save"
    />
  </section>
</template>
