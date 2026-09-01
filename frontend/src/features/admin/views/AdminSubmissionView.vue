<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { describeError } from '@/core/api/messages'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseField from '@/core/components/BaseField.vue'
import { formatDate } from '@/core/format'
import { useNotificationStore } from '@/core/notifications/store'
import AdminShell from '@/features/admin/components/AdminShell.vue'
import { fetchSubmission, reviewSubmission } from '@/features/admin/api'

const route = useRoute()
const notifications = useNotificationStore()

const INPUT =
  'rounded-lg border border-neutral-400 bg-page px-5 py-4 text-sm font-medium text-ink outline-none'

const work = ref(null)
const form = reactive({ score: 0, comment: '' })
const isLoading = ref(true)
const isSaving = ref(false)
const loadError = ref('')
const formError = ref('')

const isDecided = computed(() => ['accepted', 'needs_revision'].includes(work.value?.status ?? ''))

async function load() {
  isLoading.value = true
  loadError.value = ''
  try {
    work.value = await fetchSubmission(route.params.id)
    form.score = work.value.max_score
  } catch (failure) {
    loadError.value = describeError(failure, 'Не удалось открыть работу')
  } finally {
    isLoading.value = false
  }
}

async function decide(decision) {
  if (isSaving.value) return
  if (!form.comment.trim()) {
    formError.value = 'Напишите студенту, что именно вы увидели — без этого рецензия бесполезна'
    return
  }
  isSaving.value = true
  formError.value = ''
  try {
    work.value = await reviewSubmission(route.params.id, {
      score: Number(form.score) || 0,
      comment: form.comment.trim(),
      decision,
    })
    notifications.notify(
      decision === 'accepted' ? 'Работа принята' : 'Работа отправлена на доработку',
    )
  } catch (failure) {
    formError.value = describeError(failure, 'Не удалось сохранить рецензию')
  } finally {
    isSaving.value = false
  }
}

watch(() => route.params.id, load, { immediate: true })
</script>

<template>
  <AdminShell
    :subtitle="work ? `${work.assignment_title} · попытка ${work.attempt_no}` : ''"
    :title="work?.student_name || work?.student_email || 'Работа'"
  >
    <template #breadcrumb>
      <RouterLink class="text-2xs font-medium text-subtle" to="/admin/submissions">
        ← Проверка работ
      </RouterLink>
    </template>

    <p v-if="isLoading" class="py-24 text-center text-sm font-semibold text-subtle">
      Загружаем работу…
    </p>

    <p v-else-if="loadError" class="py-24 text-center text-sm font-semibold text-subtle">
      {{ loadError }}
    </p>

    <div v-else-if="work" class="grid gap-8 p-5 lg:grid-cols-2 lg:p-6">
      <div class="flex flex-col gap-4">
        <p v-if="work.is_late" class="text-xs font-semibold text-danger-500">Сдано после срока</p>
        <p class="text-sm font-medium leading-relaxed text-ink">
          {{ work.comment || 'Студент не оставил комментария' }}
        </p>

        <ul v-if="work.attachments.length" class="flex flex-col gap-2">
          <li v-for="file in work.attachments" :key="file.id">
            <a
              class="text-sm font-semibold text-accent"
              :href="file.url"
              rel="noopener"
              target="_blank"
            >
              {{ file.name }}
            </a>
          </li>
        </ul>
        <p v-else class="text-xs font-medium text-subtle">Файлов не приложено</p>

        <div v-if="work.history.length" class="pt-4">
          <p class="text-xs font-semibold text-muted">Что было раньше</p>
          <div
            v-for="item in work.history"
            :key="item.id"
            class="mt-3 rounded-lg bg-subtle p-4 text-sm font-medium text-muted"
          >
            <p class="text-2xs font-semibold text-subtle">
              Попытка {{ item.attempt_no }}
              <template v-if="item.submitted_at"> · {{ formatDate(item.submitted_at) }}</template>
            </p>
            <p class="pt-2">{{ item.comment }}</p>
            <p v-if="item.review" class="pt-2 text-ink">
              Рецензия: {{ item.review.comment }} ({{ item.review.score }})
            </p>
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-5">
        <template v-if="isDecided">
          <p class="text-sm font-semibold text-ink">
            {{ work.status === 'accepted' ? 'Работа принята' : 'Работа отправлена на доработку' }}
          </p>
          <p class="text-xs font-medium leading-relaxed text-subtle">
            Эта попытка уже оценена. Если студент пришлёт доработку, она появится в очереди
            отдельной попыткой.
          </p>
        </template>

        <template v-else>
          <BaseField label="Комментарий студенту">
            <textarea v-model="form.comment" :class="INPUT" rows="6"></textarea>
          </BaseField>

          <BaseField :hint="`Максимум ${work.max_score}`" label="Балл">
            <input
              v-model="form.score"
              :class="INPUT"
              :max="work.max_score"
              min="0"
              type="number"
            />
          </BaseField>

          <p v-if="formError" class="text-xs font-medium text-danger-600">{{ formError }}</p>

          <div class="flex flex-wrap items-center gap-3">
            <BaseButton :disabled="isSaving" size="sm" @click="decide('accepted')">
              Принять
            </BaseButton>
            <button
              class="rounded-sm border border-subtle px-6 py-2 text-sm font-semibold text-danger-500 disabled:opacity-50"
              :disabled="isSaving"
              type="button"
              @click="decide('needs_revision')"
            >
              На доработку
            </button>
          </div>

          <p class="text-xs font-medium leading-relaxed text-subtle">
            Комментарий студент увидит целиком. Возврат на доработку открывает следующую попытку и
            ничего не стирает.
          </p>
        </template>
      </div>
    </div>
  </AdminShell>
</template>
