<script setup>
import BaseContainer from '@/core/components/BaseContainer.vue'
import CourseReviewCard from '@/features/catalog/components/CourseReviewCard.vue'
import IconSparkle from '@/core/components/icons/IconSparkle.vue'
import { formatReviews } from '@/features/catalog/format'

const props = defineProps({
  summary: { type: Object, default: null },
  reviews: { type: Array, default: () => [] },
  hasMore: { type: Boolean, default: false },
  isLoading: { type: Boolean, default: false },
})

const emit = defineEmits(['more'])

// Доля от ширины строки — не размер, токеном не выражается.
const barWidth = (percent) => ({ width: `${percent}%` })
</script>

<template>
  <section class="pt-14 lg:pt-35">
    <BaseContainer>
      <!-- Телефон: заголовок и оценка в одну строку, гистограммы нет — пять полосок
           на 320px превращаются в пять серых линий и ничего не сообщают. -->
      <div class="flex items-center justify-between lg:hidden">
        <h2 class="text-2xl font-bold text-ink">Отзывы</h2>
        <p v-if="props.summary?.count" class="flex items-center gap-2">
          <IconSparkle class="w-5 text-accent" />
          <span class="text-lg font-bold text-ink">{{ props.summary.average }}</span>
          <span class="text-2xs font-medium text-subtle">
            {{ formatReviews(props.summary.count) }}
          </span>
        </p>
      </div>

      <div class="flex flex-col gap-6 lg:flex-row lg:gap-12">
        <div class="hidden lg:block lg:basis-1/4">
          <h2 class="text-2xl font-bold text-ink">Отзывы</h2>

          <template v-if="props.summary?.count">
            <p class="flex items-center gap-3 pt-6">
              <IconSparkle class="w-5 text-accent" />
              <span class="text-2xl font-bold text-ink">{{ props.summary.average }}</span>
              <span class="text-xs font-medium text-subtle">
                {{ formatReviews(props.summary.count) }}
              </span>
            </p>

            <ul class="flex flex-col gap-3 pt-6">
              <li
                v-for="row in props.summary.histogram"
                :key="row.stars"
                class="flex items-center gap-3"
              >
                <span class="flex items-center gap-2 text-sm font-medium text-ink">
                  {{ row.stars }}
                  <IconSparkle class="w-3 text-accent" />
                </span>
                <span class="h-2 flex-1 rounded-full bg-neutral-100">
                  <span
                    class="block h-full rounded-full bg-accent"
                    :style="barWidth(row.percent)"
                  />
                </span>
                <span class="text-xs font-medium text-subtle">{{ row.percent }}%</span>
              </li>
            </ul>
          </template>
        </div>

        <div class="flex flex-col gap-3 pt-5 lg:flex-1 lg:gap-6 lg:pt-0">
          <p
            v-if="props.reviews.length === 0"
            class="py-12 text-center text-sm font-semibold text-subtle lg:text-base"
          >
            Этот курс ещё никто не оценил
          </p>

          <CourseReviewCard v-for="review in props.reviews" :key="review.id" :review="review" />

          <button
            v-if="props.hasMore"
            class="self-start text-sm font-medium text-subtle disabled:opacity-50"
            :disabled="props.isLoading"
            type="button"
            @click="emit('more')"
          >
            {{ props.isLoading ? 'Загружаем…' : 'Посмотреть остальные отзывы' }}
          </button>
        </div>
      </div>
    </BaseContainer>
  </section>
</template>
