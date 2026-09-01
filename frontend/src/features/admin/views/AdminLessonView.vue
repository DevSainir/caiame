<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { describeError } from '@/core/api/messages'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseField from '@/core/components/BaseField.vue'
import { useNotificationStore } from '@/core/notifications/store'
import AdminMaterialUpload from '@/features/admin/components/AdminMaterialUpload.vue'
import AdminShell from '@/features/admin/components/AdminShell.vue'
import { fetchLesson, updateLesson, uploadMaterial } from '@/features/admin/api'

const route = useRoute()
const notifications = useNotificationStore()

const INPUT =
  'rounded-lg border border-neutral-400 bg-page px-5 py-4 text-sm font-medium text-ink outline-none'

const lesson = ref(null)
const form = ref({
  title: '',
  description: '',
  kind: 'video',
  duration_minutes: 0,
  is_required: true,
})
const isLoading = ref(true)
const isSaving = ref(false)
const isUploading = ref(false)
const progress = ref(0)
const loadError = ref('')
const uploadError = ref('')

const courseId = computed(() => route.params.courseId)
const lessonId = computed(() => route.params.lessonId)

function fill(data) {
  lesson.value = data
  form.value = {
    title: data.title,
    description: data.description,
    kind: data.kind,
    duration_minutes: data.duration_minutes,
    is_required: data.is_required,
  }
}

async function load() {
  isLoading.value = true
  loadError.value = ''
  try {
    fill(await fetchLesson(courseId.value, lessonId.value))
  } catch (failure) {
    loadError.value = describeError(failure, 'Не удалось открыть лекцию')
  } finally {
    isLoading.value = false
  }
}

async function save() {
  if (isSaving.value) return
  isSaving.value = true
  try {
    await updateLesson(courseId.value, lessonId.value, {
      ...form.value,
      duration_minutes: Number(form.value.duration_minutes) || 0,
    })
    notifications.notify('Лекция сохранена')
  } catch (failure) {
    notifications.notify(describeError(failure, 'Не удалось сохранить лекцию'), 'error')
  } finally {
    isSaving.value = false
  }
}

/**
 * Отправить файл в хранилище и привязать его к лекции.
 *
 * Прогресс показываем настоящий: видео на два гигабайта идёт минутами, и полоса, которая
 * стоит на месте, читается как «зависло».
 */
async function upload(file) {
  if (isUploading.value) return
  isUploading.value = true
  uploadError.value = ''
  progress.value = 0
  try {
    fill(
      await uploadMaterial(courseId.value, lessonId.value, file, form.value.kind, (value) => {
        progress.value = value
      }),
    )
    notifications.notify('Файл загружен')
  } catch (failure) {
    uploadError.value = describeError(failure, 'Не удалось загрузить файл')
  } finally {
    isUploading.value = false
  }
}

watch([courseId, lessonId], load, { immediate: true })
</script>

<template>
  <AdminShell subtitle="Лекция и её материал" title="Лекция">
    <template #breadcrumb>
      <RouterLink class="text-2xs font-medium text-subtle" :to="`/admin/courses/${courseId}`">
        ← Программа курса
      </RouterLink>
    </template>

    <template #actions>
      <BaseButton :disabled="isSaving || isLoading" size="sm" @click="save">Сохранить</BaseButton>
    </template>

    <p v-if="isLoading" class="py-24 text-center text-sm font-semibold text-subtle">
      Загружаем лекцию…
    </p>

    <p v-else-if="loadError" class="py-24 text-center text-sm font-semibold text-subtle">
      {{ loadError }}
    </p>

    <div v-else class="grid gap-8 p-5 lg:grid-cols-2 lg:p-6">
      <div class="flex flex-col gap-5">
        <BaseField label="Название">
          <input v-model="form.title" :class="INPUT" type="text" />
        </BaseField>

        <BaseField label="Описание">
          <textarea v-model="form.description" :class="INPUT" rows="4"></textarea>
        </BaseField>

        <div class="grid grid-cols-2 gap-4">
          <BaseField label="Вид">
            <select v-model="form.kind" :class="INPUT">
              <option value="video">Видео-лекция</option>
              <option value="pdf">Материал в файле</option>
            </select>
          </BaseField>
          <BaseField label="Длительность, мин">
            <input v-model="form.duration_minutes" :class="INPUT" min="0" type="number" />
          </BaseField>
        </div>

        <label class="flex items-start gap-3">
          <input v-model="form.is_required" class="mt-1" type="checkbox" />
          <span class="flex flex-col gap-1">
            <span class="text-sm font-medium text-ink">Обязательная лекция</span>
            <span class="text-2xs font-medium leading-relaxed text-subtle">
              Необязательная не учитывается в проценте прохождения
            </span>
          </span>
        </label>
      </div>

      <AdminMaterialUpload
        :error="uploadError"
        :is-busy="isUploading"
        :kind="form.kind"
        :material="lesson?.material"
        :progress="progress"
        @pick="upload"
      />
    </div>
  </AdminShell>
</template>
