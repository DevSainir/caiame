<script setup>
import { reactive, ref } from 'vue'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseField from '@/core/components/BaseField.vue'
import BaseModal from '@/core/components/BaseModal.vue'

const props = defineProps({
  // Пусто — создаём новую строку программы, иначе правим существующую.
  unit: { type: Object, default: null },
  kind: { type: String, default: 'module' },
  isBusy: { type: Boolean, default: false },
})
const emit = defineEmits(['submit', 'close'])

const INPUT =
  'rounded-lg border border-neutral-400 bg-page px-5 py-4 text-sm font-medium text-ink outline-none'
const NAMES = { module: 'Модуль', assignment: 'Задание', test: 'Тестирование' }

const form = reactive({
  title: props.unit?.title ?? '',
  summary: props.unit?.summary ?? '',
})
const titleError = ref('')

function submit() {
  titleError.value = form.title.trim() ? '' : 'Укажите название'
  if (titleError.value) return
  emit('submit', { title: form.title.trim(), summary: form.summary.trim() })
}
</script>

<template>
  <BaseModal :title="NAMES[props.unit?.kind ?? props.kind]" @close="emit('close')">
    <form class="flex flex-col gap-5" @submit.prevent="submit">
      <BaseField label="Название">
        <input v-model="form.title" :class="INPUT" type="text" />
        <span v-if="titleError" class="text-2xs font-medium text-danger-600">{{ titleError }}</span>
      </BaseField>

      <BaseField label="Короткое описание">
        <textarea v-model="form.summary" :class="INPUT" rows="3"></textarea>
      </BaseField>

      <div class="flex items-center justify-end gap-3 pt-2">
        <button class="text-sm font-semibold text-subtle" type="button" @click="emit('close')">
          Отмена
        </button>
        <BaseButton :disabled="props.isBusy" size="sm" type="submit">Сохранить</BaseButton>
      </div>
    </form>
  </BaseModal>
</template>
