<script setup>
import { reactive, ref } from 'vue'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseField from '@/core/components/BaseField.vue'
import BaseModal from '@/core/components/BaseModal.vue'

const props = defineProps({
  lesson: { type: Object, default: null },
  isBusy: { type: Boolean, default: false },
})
const emit = defineEmits(['submit', 'close'])

const INPUT =
  'rounded-lg border border-neutral-400 bg-page px-5 py-4 text-sm font-medium text-ink outline-none'

const form = reactive({
  title: props.lesson?.title ?? '',
  description: props.lesson?.description ?? '',
  kind: props.lesson?.kind ?? 'video',
  duration_minutes: props.lesson?.duration_minutes ?? 0,
  is_required: props.lesson?.is_required ?? true,
})
const titleError = ref('')

function submit() {
  titleError.value = form.title.trim() ? '' : 'Укажите название лекции'
  if (titleError.value) return
  emit('submit', {
    title: form.title.trim(),
    description: form.description.trim(),
    kind: form.kind,
    duration_minutes: Number(form.duration_minutes) || 0,
    is_required: form.is_required,
  })
}
</script>

<template>
  <BaseModal :title="props.lesson ? 'Лекция' : 'Новая лекция'" @close="emit('close')">
    <form class="flex flex-col gap-5" @submit.prevent="submit">
      <BaseField label="Название">
        <input v-model="form.title" :class="INPUT" type="text" />
        <span v-if="titleError" class="text-2xs font-medium text-danger-600">{{ titleError }}</span>
      </BaseField>

      <BaseField label="Описание">
        <textarea v-model="form.description" :class="INPUT" rows="3"></textarea>
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
            Необязательная не учитывается в проценте прохождения — так материал можно добавить в
            идущий курс, не сбрасывая процент тем, кто уже занимается
          </span>
        </span>
      </label>

      <div class="flex items-center justify-end gap-3 pt-2">
        <button class="text-sm font-semibold text-subtle" type="button" @click="emit('close')">
          Отмена
        </button>
        <BaseButton :disabled="props.isBusy" size="sm" type="submit">Сохранить</BaseButton>
      </div>
    </form>
  </BaseModal>
</template>
