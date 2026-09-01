<script setup>
import { computed, ref } from 'vue'
import BaseButton from '@/core/components/BaseButton.vue'

const props = defineProps({
  material: { type: Object, default: null },
  kind: { type: String, default: 'video' },
  isBusy: { type: Boolean, default: false },
  progress: { type: Number, default: 0 },
  error: { type: String, default: '' },
})
const emit = defineEmits(['pick'])

const ACCEPT = { video: 'video/mp4', pdf: 'application/pdf' }
const HINTS = { video: 'Видео в формате MP4, до 2 ГБ', pdf: 'Файл PDF, до 50 МБ' }

const input = ref(null)
const isOver = ref(false)

// Килобайты, мегабайты, гигабайты: одна и та же строка «1 МБ» и на файле в 40 КБ, и на
// файле в мегабайт не даёт понять, тот ли файл загрузился.
const sizeLabel = computed(() => {
  const bytes = props.material?.size_bytes ?? 0
  const kilobytes = bytes / 1024
  if (kilobytes < 1024) return `${Math.max(1, Math.round(kilobytes))} КБ`
  const megabytes = kilobytes / 1024
  return megabytes >= 1024 ? `${(megabytes / 1024).toFixed(1)} ГБ` : `${megabytes.toFixed(1)} МБ`
})

const dateLabel = computed(() =>
  props.material
    ? new Date(props.material.uploaded_at).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
      })
    : '',
)

function choose(file) {
  if (file) emit('pick', file)
}

function onDrop(event) {
  isOver.value = false
  choose(event.dataTransfer?.files?.[0])
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <p class="text-xs font-semibold text-muted">Материал</p>

    <div
      class="flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-14 text-center"
      :class="isOver ? 'border-accent' : 'border-neutral-400'"
      @dragleave.prevent="isOver = false"
      @dragover.prevent="isOver = true"
      @drop.prevent="onDrop"
    >
      <p class="text-sm font-bold text-ink">Перетащите файл сюда</p>
      <p class="text-xs font-medium text-subtle">{{ HINTS[props.kind] }}</p>
      <input
        ref="input"
        :accept="ACCEPT[props.kind]"
        class="hidden"
        type="file"
        @change="choose($event.target.files[0])"
      />
      <BaseButton :disabled="props.isBusy" class="mt-2" size="sm" @click="input.click()">
        Выбрать файл
      </BaseButton>
    </div>

    <div v-if="props.isBusy" class="rounded-lg border border-subtle p-5">
      <p class="text-sm font-medium text-ink">Загружаем файл…</p>
      <div class="mt-4 h-2 rounded-full bg-neutral-100">
        <div
          class="h-full rounded-full bg-accent transition-all"
          :style="{ width: `${props.progress}%` }"
        ></div>
      </div>
    </div>

    <div v-else-if="props.material" class="rounded-lg border border-subtle p-5">
      <div class="flex items-center justify-between gap-4">
        <div class="min-w-0">
          <p class="truncate text-sm font-medium text-ink">{{ props.material.original_name }}</p>
          <p class="pt-2 text-2xs font-medium text-subtle">
            {{ sizeLabel }} · загружен {{ dateLabel }}
          </p>
        </div>
        <button
          class="shrink-0 text-sm font-semibold text-accent disabled:opacity-50"
          :disabled="props.isBusy"
          type="button"
          @click="input.click()"
        >
          Заменить
        </button>
      </div>
      <div class="mt-4 h-2 rounded-full bg-neutral-100">
        <div class="h-full w-full rounded-full bg-success-500"></div>
      </div>
    </div>

    <p v-else class="text-xs font-medium text-subtle">Файл пока не загружен</p>

    <p v-if="props.error" class="text-xs font-medium text-danger-600">{{ props.error }}</p>
  </div>
</template>
