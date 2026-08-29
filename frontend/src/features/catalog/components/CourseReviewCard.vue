<script setup>
import IconSparkle from '@/core/components/icons/IconSparkle.vue'
import { formatDate } from '@/features/catalog/format'
import { initialsFor } from '@/core/initials'

const props = defineProps({
  review: { type: Object, required: true },
})
</script>

<template>
  <article
    class="flex flex-col gap-4 rounded-lg border border-subtle bg-page p-4 lg:flex-row lg:items-start lg:gap-6 lg:p-6"
  >
    <!-- Колонка автора одной ширины во всех карточках: иначе длинное имя сдвигает текст
         отзыва вправо, и колонка текста едет от карточки к карточке. -->
    <div class="flex shrink-0 items-center gap-3 lg:w-1/4 lg:gap-4">
      <span
        class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent text-base font-semibold text-inverse lg:h-12 lg:w-12"
      >
        {{ initialsFor({ fullName: props.review.author_name }) }}
      </span>
      <span class="text-sm font-semibold text-ink">{{ props.review.author_name }}</span>
    </div>

    <div class="flex flex-col gap-3 lg:flex-1">
      <div class="flex items-center gap-3">
        <span class="flex items-center gap-2 text-xs font-semibold text-accent lg:text-sm">
          <IconSparkle class="w-4" />
          {{ props.review.rating }}
        </span>
        <span class="text-2xs font-medium text-subtle lg:text-xs">
          Отзыв от {{ formatDate(props.review.created_at) }}
        </span>
      </div>
      <p class="text-sm font-medium text-ink lg:text-base">{{ props.review.text }}</p>
    </div>
  </article>
</template>
