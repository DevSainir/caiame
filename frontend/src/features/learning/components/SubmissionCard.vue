<script setup>
import { formatDate } from '@/core/format'

const props = defineProps({
  submission: { type: Object, required: true },
})

const STATUS_LABELS = {
  submitted: 'На проверке',
  in_review: 'На проверке',
  accepted: 'Принято',
  needs_revision: 'Нужны доработки',
  draft: 'Черновик',
}
const STATUS_TONE = {
  accepted: 'text-success-600',
  needs_revision: 'text-danger-500',
}
</script>

<template>
  <article class="rounded-lg border border-subtle p-4 lg:p-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-sm font-bold text-ink">Попытка {{ props.submission.attempt_no }}</p>
      <span
        class="text-xs font-semibold"
        :class="STATUS_TONE[props.submission.status] ?? 'text-subtle'"
      >
        {{ STATUS_LABELS[props.submission.status] }}
        <template v-if="props.submission.is_late"> · сдано после срока</template>
      </span>
    </div>

    <p v-if="props.submission.submitted_at" class="pt-2 text-2xs font-medium text-subtle">
      Отправлено {{ formatDate(props.submission.submitted_at) }}
    </p>

    <p v-if="props.submission.comment" class="pt-3 text-sm font-medium leading-relaxed text-muted">
      {{ props.submission.comment }}
    </p>

    <ul v-if="props.submission.attachments.length" class="flex flex-col gap-2 pt-3">
      <li v-for="file in props.submission.attachments" :key="file.id">
        <a
          class="text-sm font-semibold text-accent"
          :href="file.url"
          rel="noopener"
          target="_blank"
        >
          {{ file.name }}
        </a>
      </li>
    </ul>

    <div v-if="props.submission.review" class="mt-4 rounded-lg bg-subtle p-4">
      <p class="text-xs font-semibold text-muted">
        Рецензия · {{ props.submission.review.score }} баллов
        <template v-if="props.submission.review.reviewer_name">
          · {{ props.submission.review.reviewer_name }}
        </template>
      </p>
      <p class="pt-2 text-sm font-medium leading-relaxed text-ink">
        {{ props.submission.review.comment }}
      </p>
    </div>
  </article>
</template>
