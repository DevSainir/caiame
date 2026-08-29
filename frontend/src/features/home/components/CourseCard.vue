<script setup>
import BaseBadge from '@/core/components/BaseBadge.vue'
import BaseButton from '@/core/components/BaseButton.vue'
import { audienceLabel } from '@/features/catalog/labels'

const props = defineProps({
  course: { type: Object, required: true },
})

// Бейджи говорят то, чего нет в заголовке: к какой специализации курс относится, кого он
// принимает и по какому типу кредитования идёт.
const badges = () =>
  [
    audienceLabel(props.course.specialization?.audience),
    props.course.specialization?.name,
    props.course.accreditation?.short_code,
  ].filter(Boolean)
</script>

<template>
  <!-- Ссылка — вся карточка, а не одна кнопка: по картинке и заголовку кликают чаще, чем
       по «Подробнее», и промах по ним читается как сломанный сайт. -->
  <RouterLink
    class="group row-span-4 grid grid-rows-subgrid gap-4 rounded-lg border p-4 transition-colors hover:border-accent lg:gap-5 lg:px-4 lg:py-5"
    :to="`/courses/${props.course.slug}`"
  >
    <div class="flex flex-wrap content-start gap-2">
      <BaseBadge v-for="badge in badges()" :key="badge">{{ badge }}</BaseBadge>
    </div>

    <div
      class="flex aspect-square items-center justify-center overflow-hidden rounded-md bg-neutral-100 lg:aspect-video"
    >
      <img
        v-if="props.course.cover_url"
        decoding="async"
        loading="lazy"
        :alt="props.course.title"
        class="h-full w-full object-cover"
        :src="props.course.cover_url"
      />
      <span v-else class="text-2xl font-semibold text-neutral-400">ФОТО</span>
    </div>

    <div class="flex flex-col gap-2">
      <h3 class="text-lg font-bold text-ink lg:text-xl">{{ props.course.title }}</h3>
      <p class="text-sm font-medium text-subtle">{{ props.course.summary }}</p>
    </div>

    <BaseButton class="justify-self-start group-hover:bg-primary-600" element="span" size="sm">
      Подробнее
    </BaseButton>
  </RouterLink>
</template>
