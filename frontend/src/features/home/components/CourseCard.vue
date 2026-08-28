<script setup>
import BaseBadge from '@/core/components/BaseBadge.vue'
import BaseButton from '@/core/components/BaseButton.vue'
import { difficultyLabel } from '@/features/catalog/labels'

const props = defineProps({
  course: { type: Object, required: true },
})

const badges = () =>
  [
    difficultyLabel(props.course.difficulty),
    props.course.specialization?.name,
    props.course.accreditation?.short_code,
  ].filter(Boolean)
</script>

<template>
  <article class="row-span-4 grid grid-rows-subgrid gap-5 rounded-lg border px-4 py-5">
    <div class="flex flex-wrap content-start gap-2">
      <BaseBadge v-for="badge in badges()" :key="badge">{{ badge }}</BaseBadge>
    </div>

    <div class="flex aspect-video items-center justify-center overflow-hidden rounded-md bg-neutral-100">
      <img
        v-if="props.course.cover_url"
        :alt="props.course.title"
        class="h-full w-full object-cover"
        :src="props.course.cover_url"
      />
      <span v-else class="text-2xl font-semibold text-neutral-400">ФОТО</span>
    </div>

    <div class="flex flex-col gap-2">
      <h3 class="text-xl font-bold text-ink">{{ props.course.title }}</h3>
      <p class="text-sm font-medium text-subtle">{{ props.course.summary }}</p>
    </div>

    <BaseButton class="justify-self-start" size="sm" :to="`/courses/${props.course.slug}`">
      Подробнее
    </BaseButton>
  </article>
</template>
