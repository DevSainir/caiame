<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { describeError } from '@/core/api/messages'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseContainer from '@/core/components/BaseContainer.vue'
import { formatDate } from '@/core/format'
import { useNotificationStore } from '@/core/notifications/store'
import AccessNotice from '@/features/learning/components/AccessNotice.vue'
import LearningCrumbs from '@/features/learning/components/LearningCrumbs.vue'
import SubmissionCard from '@/features/learning/components/SubmissionCard.vue'
import { fetchAssignment, submitWork, uploadAttachment } from '@/features/learning/api'

const route = useRoute()
const notifications = useNotificationStore()

const assignment = ref(null)
const comment = ref('')
const attachments = ref([])
const isLoading = ref(true)
const isSending = ref(false)
const isUploading = ref(false)
const error = ref(null)
const formError = ref('')
const fileInput = ref(null)

const isLocked = computed(() => error.value?.status === 402)
const course = computed(() =>
  assignment.value
    ? { slug: assignment.value.course_slug, title: assignment.value.course_title }
    : null,
)

async function load(id) {
  isLoading.value = true
  error.value = null
  try {
    assignment.value = await fetchAssignment(id)
  } catch (failure) {
    error.value = failure
    assignment.value = null
  } finally {
    isLoading.value = false
  }
}

async function attach(file) {
  if (!file) return
  isUploading.value = true
  formError.value = ''
  try {
    attachments.value = [...attachments.value, await uploadAttachment(file)]
  } catch (failure) {
    formError.value = describeError(failure, 'Не удалось загрузить файл')
  } finally {
    isUploading.value = false
  }
}

async function send() {
  if (isSending.value) return
  if (!comment.value.trim() && attachments.value.length === 0) {
    formError.value = 'Напишите пару слов или приложите файл — пустую работу проверять нечего'
    return
  }
  isSending.value = true
  formError.value = ''
  try {
    assignment.value = await submitWork(route.params.id, {
      comment: comment.value.trim(),
      media_ids: attachments.value.map((file) => file.id),
    })
    comment.value = ''
    attachments.value = []
    notifications.notify('Работа отправлена на проверку')
  } catch (failure) {
    formError.value = describeError(failure, 'Не удалось отправить работу')
  } finally {
    isSending.value = false
  }
}

watch(() => route.params.id, load, { immediate: true })
</script>

<template>
  <div class="pb-14 pt-6 lg:pb-35 lg:pt-14">
    <BaseContainer>
      <p v-if="isLoading" class="py-24 text-center text-sm font-semibold text-subtle lg:text-lg">
        Загружаем задание…
      </p>

      <AccessNotice v-else-if="isLocked" />

      <div v-else-if="error" class="flex flex-col items-center gap-5 py-24">
        <p class="text-center text-sm font-semibold text-subtle lg:text-lg">
          {{ error.status === 404 ? 'Такого задания нет' : describeError(error) }}
        </p>
        <RouterLink class="text-base font-bold text-accent" to="/">Ко всем курсам</RouterLink>
      </div>

      <template v-else-if="assignment">
        <LearningCrumbs :course="course" />

        <div class="mt-5 rounded-xl bg-page px-4 py-5 lg:mt-8 lg:px-15 lg:py-14">
          <h1 class="max-w-xl text-xl font-bold text-ink lg:text-3xl">{{ assignment.title }}</h1>
          <p class="max-w-xl pt-4 text-sm font-medium leading-relaxed text-muted lg:pt-6">
            {{ assignment.description }}
          </p>
          <p v-if="assignment.deadline_at" class="pt-4 text-xs font-semibold text-subtle">
            Сдать до {{ formatDate(assignment.deadline_at) }} · максимум
            {{ assignment.max_score }} баллов
          </p>
          <p v-else class="pt-4 text-xs font-semibold text-subtle">
            Срок не ограничен · максимум {{ assignment.max_score }} баллов
          </p>
        </div>

        <section v-if="assignment.submissions.length" class="pt-8 lg:pt-14">
          <h2 class="text-xl font-bold text-ink lg:text-2xl">Ваши работы</h2>
          <div class="flex flex-col gap-4 pt-4 lg:pt-6">
            <SubmissionCard
              v-for="submission in assignment.submissions"
              :key="submission.id"
              :submission="submission"
            />
          </div>
        </section>

        <section v-if="assignment.can_submit" class="pt-8 lg:pt-14">
          <h2 class="text-xl font-bold text-ink lg:text-2xl">
            {{ assignment.submissions.length ? 'Отправить доработку' : 'Отправить работу' }}
          </h2>

          <div class="flex max-w-xl flex-col gap-4 pt-4 lg:pt-6">
            <textarea
              v-model="comment"
              class="min-h-30 rounded-lg border border-neutral-400 bg-page px-5 py-4 text-sm font-medium text-ink outline-none"
              placeholder="Что вы сделали и на что обратить внимание"
            ></textarea>

            <ul v-if="attachments.length" class="flex flex-col gap-2">
              <li v-for="file in attachments" :key="file.id" class="text-sm font-medium text-muted">
                {{ file.name }}
              </li>
            </ul>

            <input
              ref="fileInput"
              accept=".pdf,.png,.jpg,.jpeg,.zip"
              class="hidden"
              type="file"
              @change="attach($event.target.files[0])"
            />

            <div class="flex flex-wrap items-center gap-4">
              <button
                class="text-sm font-semibold text-accent disabled:opacity-50"
                :disabled="isUploading"
                type="button"
                @click="fileInput.click()"
              >
                {{ isUploading ? 'Загружаем файл…' : '+ Приложить файл' }}
              </button>
              <BaseButton :disabled="isSending || isUploading" size="sm" @click="send">
                {{ isSending ? 'Отправляем…' : 'Отправить на проверку' }}
              </BaseButton>
            </div>

            <p v-if="formError" class="text-sm font-medium text-danger-600">{{ formError }}</p>
            <p class="text-xs font-medium leading-relaxed text-subtle">
              Можно приложить документ, снимок или архив. После отправки работа попадёт к
              преподавателю; пока он её смотрит, отправить новую нельзя.
            </p>
          </div>
        </section>

        <p v-else class="pt-8 text-sm font-medium text-subtle lg:pt-14">
          {{
            assignment.submissions.at(-1)?.status === 'accepted'
              ? 'Работа принята — задание закрыто.'
              : 'Работа у преподавателя. Как только он её посмотрит, здесь появится рецензия.'
          }}
        </p>
      </template>
    </BaseContainer>
  </div>
</template>
