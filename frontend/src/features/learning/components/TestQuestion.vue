<script setup>
import { formatPoints } from '@/core/format'
const props = defineProps({
  question: { type: Object, required: true },
  selected: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['pick'])

/**
 * Выбор варианта.
 *
 * Один верный ответ заменяет выбор, несколько — добавляет и убирает. Ребёнок ничего не
 * хранит: он сообщает новый набор наверх, где живёт вся попытка.
 */
function pick(optionId) {
  if (props.disabled) return
  if (props.question.kind === 'single') {
    emit('pick', [optionId])
    return
  }
  const next = props.selected.includes(optionId)
    ? props.selected.filter((id) => id !== optionId)
    : [...props.selected, optionId]
  emit('pick', next)
}
</script>

<template>
  <fieldset class="flex flex-col gap-3">
    <div class="flex items-start justify-between gap-4">
      <legend class="text-base font-bold text-ink lg:text-lg">
        {{ props.question.position }}. {{ props.question.text }}
      </legend>
      <span
        class="shrink-0 rounded-sm bg-primary-50 px-3 py-2 text-2xs font-medium text-accent lg:text-xs"
      >
        {{ formatPoints(props.question.points) }}
      </span>
    </div>

    <label
      v-for="option in props.question.options"
      :key="option.id"
      class="flex items-center gap-3 text-sm font-medium text-ink"
    >
      <input
        class="h-4 w-4 accent-primary-500"
        :checked="props.selected.includes(option.id)"
        :disabled="props.disabled"
        :name="props.question.id"
        :type="props.question.kind === 'single' ? 'radio' : 'checkbox'"
        @change="pick(option.id)"
      />
      {{ option.text }}
    </label>
  </fieldset>
</template>
