<script setup>
import { ref } from 'vue'
import { describeError } from '@/core/api/messages'
import { useNotificationStore } from '@/core/notifications/store'
import { uploadMaterial } from '@/features/admin/api'

const props = defineProps({
  courseId: { type: String, required: true },
  lesson: { type: Object, required: true },
})
const emit = defineEmits(['uploaded'])

const notifications = useNotificationStore()

const ACCEPT = { video: 'video/mp4', pdf: 'application/pdf' }

const input = ref(null)
const isUploading = ref(false)
const progress = ref(0)

/**
 * Загрузка прямо из строки программы.
 *
 * Наполнение курса — это полторы сотни файлов подряд; открывать ради каждого отдельный
 * экран значит проделать полторы сотни лишних переходов. Экран лекции остаётся там, где
 * нужно поправить название, описание или заменить файл осознанно.
 */
async function upload(file) {
  if (!file || isUploading.value) return
  isUploading.value = true
  progress.value = 0
  try {
    await uploadMaterial(props.courseId, props.lesson.id, file, props.lesson.kind, (value) => {
      progress.value = value
    })
    notifications.notify(`Файл загружен: ${props.lesson.title}`)
    emit('uploaded')
  } catch (failure) {
    notifications.notify(describeError(failure, 'Не удалось загрузить файл'), 'error')
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <span class="flex items-center gap-2">
    <input
      ref="input"
      :accept="ACCEPT[props.lesson.kind]"
      class="hidden"
      type="file"
      @change="upload($event.target.files[0])"
    />
    <span v-if="isUploading" class="flex items-center gap-2">
      <span class="h-1 w-12 rounded-full bg-neutral-100">
        <span
          class="block h-full rounded-full bg-accent transition-all"
          :style="{ width: `${progress}%` }"
        ></span>
      </span>
      <span class="text-2xs font-medium text-subtle">{{ progress }} %</span>
    </span>
    <button v-else class="text-sm font-semibold text-accent" type="button" @click="input.click()">
      {{ props.lesson.has_material ? 'Заменить файл' : 'Загрузить файл' }}
    </button>
  </span>
</template>
