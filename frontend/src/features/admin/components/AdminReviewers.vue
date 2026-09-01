<script setup>
import { onMounted, ref } from 'vue'
import { describeError } from '@/core/api/messages'
import BaseButton from '@/core/components/BaseButton.vue'
import { useNotificationStore } from '@/core/notifications/store'
import { addReviewer, fetchReviewers, removeReviewer } from '@/features/admin/api'

const props = defineProps({
  courseId: { type: String, required: true },
})

const notifications = useNotificationStore()

const INPUT =
  'rounded-lg border border-neutral-400 bg-page px-5 py-3 text-sm font-medium text-ink outline-none'

const reviewers = ref([])
const email = ref('')
const isLoading = ref(true)
const isBusy = ref(false)
const error = ref('')

async function load() {
  isLoading.value = true
  try {
    reviewers.value = await fetchReviewers(props.courseId)
  } catch (failure) {
    error.value = describeError(failure, 'Не удалось загрузить список проверяющих')
  } finally {
    isLoading.value = false
  }
}

async function add() {
  if (!email.value.includes('@')) {
    error.value = 'Укажите почту сотрудника'
    return
  }
  isBusy.value = true
  error.value = ''
  try {
    reviewers.value = await addReviewer(props.courseId, email.value.trim().toLowerCase())
    email.value = ''
    notifications.notify('Проверяющий назначен')
  } catch (failure) {
    error.value =
      failure?.code === 'not_a_member_of_staff'
        ? 'Это не сотрудник академии: проверять работы студент не может'
        : describeError(failure, 'Не удалось назначить проверяющего')
  } finally {
    isBusy.value = false
  }
}

async function remove(reviewer) {
  if (!window.confirm(`Снять ${reviewer.email} с проверки работ этого курса?`)) return
  isBusy.value = true
  try {
    reviewers.value = await removeReviewer(props.courseId, reviewer.id)
    notifications.notify('Проверяющий снят с курса')
  } catch (failure) {
    notifications.notify(describeError(failure, 'Не удалось снять проверяющего'), 'error')
  } finally {
    isBusy.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="border-t border-subtle p-4 lg:p-5">
    <div class="pb-4">
      <h2 class="text-lg font-bold text-ink">Кто проверяет работы</h2>
      <p class="pt-2 text-2xs font-medium leading-relaxed text-subtle">
        Преподаватель видит в очереди только те курсы, на которые его поставили. Администраторы
        видят все работы и в списке не нужны.
      </p>
    </div>

    <p v-if="isLoading" class="py-6 text-center text-sm font-medium text-subtle">Загружаем…</p>

    <template v-else>
      <ul v-if="reviewers.length" class="flex flex-col rounded-lg border border-subtle">
        <li
          v-for="reviewer in reviewers"
          :key="reviewer.id"
          class="flex flex-wrap items-center justify-between gap-4 border-b border-subtle p-4 last:border-b-0"
        >
          <div class="min-w-0">
            <p class="text-sm font-bold text-ink">{{ reviewer.name || reviewer.email }}</p>
            <p class="pt-1 text-2xs font-medium text-subtle">{{ reviewer.email }}</p>
          </div>
          <button
            class="text-sm font-semibold text-danger-500 disabled:opacity-50"
            :disabled="isBusy"
            type="button"
            @click="remove(reviewer)"
          >
            Снять
          </button>
        </li>
      </ul>

      <p v-else class="rounded-lg border border-subtle px-5 py-6 text-sm font-medium text-subtle">
        Никто не назначен — работы этого курса видят только администраторы
      </p>

      <form class="flex flex-wrap items-center gap-3 pt-4" @submit.prevent="add">
        <input
          v-model="email"
          :class="[INPUT, 'flex-1']"
          placeholder="Почта преподавателя"
          type="email"
        />
        <BaseButton :disabled="isBusy" size="sm" type="submit">Назначить</BaseButton>
      </form>

      <p v-if="error" class="pt-3 text-xs font-medium text-danger-600">{{ error }}</p>
    </template>
  </section>
</template>
