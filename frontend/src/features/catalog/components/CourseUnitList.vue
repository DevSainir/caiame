<script setup>
import IconArrowRight from '@/core/components/icons/IconArrowRight.vue'

const props = defineProps({
  units: { type: Array, default: () => [] },
})

const STATUS_LABELS = {
  not_started: 'Не начат',
  in_progress: 'В процессе',
  done: 'Завершено',
}

const STATUS_TONE = {
  not_started: 'text-disabled',
  in_progress: 'text-ink',
  done: 'text-accent',
}

// Тестирование выделено красным независимо от того, начато оно или нет: это не статус,
// а вид работы — за тест ставят оценку, и его видно в списке издалека.
const isTest = (unit) => unit.kind === 'test'

const titleTone = (unit) => {
  if (isTest(unit)) return 'text-danger-500'
  return unit.status === 'done' ? 'text-accent' : 'text-ink'
}

const summaryTone = (unit) =>
  !isTest(unit) && unit.status === 'done' ? 'text-accent' : 'text-muted'
</script>

<template>
  <!-- Телефон: каждая строка — отдельная карточка. Десктоп: одна карточка на весь список,
       строки внутри разделены линиями. -->
  <div class="lg:rounded-xl lg:border lg:border-subtle lg:bg-page lg:px-15 lg:py-4">
    <ul class="flex flex-col gap-3 lg:gap-0">
      <li
        v-for="(unit, index) in props.units"
        :key="unit.id"
        class="flex items-center justify-between gap-4 rounded-lg bg-page px-4 py-4 lg:rounded-none lg:bg-transparent lg:px-0 lg:py-8"
        :class="index > 0 ? 'lg:border-t lg:border-subtle' : ''"
      >
        <span class="flex flex-col gap-2">
          <span class="text-base font-bold lg:text-xl" :class="titleTone(unit)">
            {{ unit.title }}
          </span>
          <span class="text-xs font-medium lg:text-sm" :class="summaryTone(unit)">
            {{ unit.summary }}
          </span>
        </span>

        <span class="flex shrink-0 flex-col items-end gap-2 lg:flex-row lg:items-center lg:gap-6">
          <span class="text-2xs font-semibold lg:text-xs" :class="STATUS_TONE[unit.status]">
            {{ STATUS_LABELS[unit.status] }}
          </span>
          <IconArrowRight class="w-6" :class="isTest(unit) ? 'text-danger-500' : 'text-accent'" />
        </span>
      </li>
    </ul>

    <div v-if="$slots.default" class="mt-3 lg:mt-0">
      <slot />
    </div>
  </div>
</template>
