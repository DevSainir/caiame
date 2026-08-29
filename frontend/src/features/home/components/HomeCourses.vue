<script setup>
import BaseContainer from '@/core/components/BaseContainer.vue'
import BaseSelect from '@/core/components/BaseSelect.vue'
import CourseCard from '@/features/home/components/CourseCard.vue'
import { audienceLabel } from '@/features/catalog/labels'

const props = defineProps({
  courses: { type: Array, default: () => [] },
  filters: { type: Object, default: () => ({}) },
  selected: { type: Object, required: true },
  isLoading: { type: Boolean, default: false },
  isLoadingMore: { type: Boolean, default: false },
  hasMore: { type: Boolean, default: false },
  error: { type: Object, default: null },
})

const emit = defineEmits(['change', 'more', 'retry'])

const options = (items, toOption) => (items ?? []).map(toOption)

// One field, one event. Emitting a merged object instead would carry a snapshot of the
// other filters, and two changes in the same tick would silently drop one of them.
function select(field, value) {
  emit('change', field, value)
}
</script>

<template>
  <section id="courses">
    <div class="bg-accent pb-28 pt-10 lg:pb-35 lg:pt-20">
      <BaseContainer>
        <div
          class="flex flex-col items-center gap-3 text-center lg:flex-row lg:items-start lg:gap-8 lg:text-left"
        >
          <h2 class="text-2xl font-bold text-inverse lg:basis-1/4 lg:text-5xl">Список курсов</h2>
          <p class="text-sm font-medium text-inverse lg:basis-2/5 lg:text-lg">
            Изучите наш широкий каталог курсов, специально разработанных для медицинских
            специалистов. Вы можете фильтровать курсы по специализации, аудитории и типу
            кредитования, чтобы найти именно то, что вам нужно.
          </p>
        </div>

        <!-- Четыре ячейки в сетку 2×2 на телефоне и в один ряд на десктопе. -->
        <div class="grid grid-cols-2 gap-2 pt-8 lg:flex lg:pt-14">
          <div
            class="flex flex-1 items-center rounded-lg bg-page px-5 py-4 text-sm font-bold text-ink lg:rounded-none lg:rounded-l-xl lg:px-8 lg:py-7 lg:text-xl"
          >
            Фильтры:
          </div>
          <BaseSelect
            class="flex-1 rounded-lg lg:rounded-none"
            :model-value="props.selected.specialization"
            :options="
              options(props.filters.specializations, (i) => ({ value: i.slug, label: i.name }))
            "
            placeholder="Специализация"
            @update:model-value="select('specialization', $event)"
          />
          <BaseSelect
            class="flex-1 rounded-lg lg:rounded-none"
            :model-value="props.selected.audience"
            :options="
              options(props.filters.audiences, (i) => ({ value: i, label: audienceLabel(i) }))
            "
            placeholder="Для кого"
            @update:model-value="select('audience', $event)"
          />
          <BaseSelect
            class="flex-1 rounded-lg lg:rounded-none lg:rounded-r-xl"
            :model-value="props.selected.accreditation"
            :options="
              options(props.filters.accreditations, (i) => ({ value: i.slug, label: i.name }))
            "
            placeholder="Тип кредитования"
            @update:model-value="select('accreditation', $event)"
          />
        </div>
      </BaseContainer>
    </div>

    <BaseContainer>
      <div class="-mt-24 rounded-xl bg-page p-5 lg:-mt-28 lg:p-8">
        <p
          v-if="props.isLoading"
          class="py-24 text-center text-sm font-semibold text-subtle lg:py-35 lg:text-lg"
        >
          Загружаем курсы…
        </p>

        <div v-else-if="props.error" class="flex flex-col items-center gap-5 py-24 lg:py-35">
          <p class="text-center text-sm font-semibold text-subtle lg:text-lg">
            Не удалось загрузить каталог курсов
          </p>
          <button class="text-base font-bold text-accent" type="button" @click="emit('retry')">
            Попробовать ещё раз
          </button>
        </div>

        <p
          v-else-if="props.courses.length === 0"
          class="py-24 text-center text-sm font-semibold text-subtle lg:py-35 lg:text-lg"
        >
          По выбранным фильтрам курсов пока нет
        </p>

        <div v-else class="grid grid-cols-1 gap-5 lg:grid-cols-3 lg:gap-8">
          <CourseCard v-for="course in props.courses" :key="course.id" :course="course" />
        </div>

        <!-- Кнопки нет, когда показывать больше нечего: «посмотреть больше» без больше —
             это тупик, который выглядит как поломка. -->
        <div v-if="props.hasMore && !props.isLoading && !props.error" class="pt-8 lg:pt-14">
          <button
            class="mx-auto block text-sm font-semibold text-subtle disabled:opacity-50 lg:text-lg"
            :disabled="props.isLoadingMore"
            type="button"
            @click="emit('more')"
          >
            {{ props.isLoadingMore ? 'Загружаем…' : 'Посмотреть больше курсов' }}
          </button>
        </div>
      </div>
    </BaseContainer>
  </section>
</template>
