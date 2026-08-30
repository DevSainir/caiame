<script setup>
import IconArrowRight from '@/core/components/icons/IconArrowRight.vue'
import IconFile from '@/core/components/icons/IconFile.vue'
import IconPlay from '@/core/components/icons/IconPlay.vue'
import { STATUS_TONE, lessonKindLabel, statusLabel } from '@/features/learning/labels'
import { formatMinutes } from '@/core/format'

const props = defineProps({
  lesson: { type: Object, required: true },
})
</script>

<template>
  <!-- Телефон: карточка со статусом сверху и синей кнопкой-стрелкой в углу.
       Десктоп: строка, где длительность, тип и статус выстроены в колонки. -->
  <RouterLink
    class="flex flex-col gap-3 rounded-lg bg-page p-4 lg:flex-row lg:items-center lg:justify-between lg:gap-6 lg:rounded-none lg:bg-transparent lg:p-0 lg:py-8"
    :to="`/lessons/${props.lesson.id}`"
  >
    <span class="text-2xs font-semibold lg:hidden" :class="STATUS_TONE[props.lesson.status]">
      {{ statusLabel(props.lesson.status) }}
    </span>

    <span class="text-base font-bold text-ink lg:flex-1 lg:text-lg">
      {{ props.lesson.title }}
    </span>

    <span class="flex items-center gap-4 lg:gap-8">
      <span class="text-2xs font-medium text-subtle lg:text-xs">
        {{ formatMinutes(props.lesson.duration_minutes) }}
      </span>

      <span class="flex items-center gap-2 text-2xs font-medium text-accent lg:w-35 lg:text-xs">
        <component :is="props.lesson.kind === 'video' ? IconPlay : IconFile" class="w-4" />
        {{ lessonKindLabel(props.lesson.kind) }}
      </span>

      <span
        class="hidden text-xs font-semibold lg:block lg:w-25"
        :class="STATUS_TONE[props.lesson.status]"
      >
        {{ statusLabel(props.lesson.status) }}
      </span>

      <!-- На телефоне стрелка — синяя кнопка в углу карточки, на десктопе просто стрелка. -->
      <span
        class="ml-auto flex h-10 w-10 items-center justify-center rounded-md bg-accent text-inverse lg:ml-0 lg:h-auto lg:w-auto lg:bg-transparent lg:text-accent"
      >
        <IconArrowRight class="w-6" />
      </span>
    </span>
  </RouterLink>
</template>
