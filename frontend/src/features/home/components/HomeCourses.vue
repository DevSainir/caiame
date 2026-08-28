<script setup>
import BaseContainer from '@/core/components/BaseContainer.vue'
import BaseSelect from '@/core/components/BaseSelect.vue'
import CourseCard from '@/features/home/components/CourseCard.vue'
import { difficultyLabel } from '@/features/catalog/labels'

const props = defineProps({
  courses: { type: Array, default: () => [] },
  filters: { type: Object, default: () => ({}) },
  selected: { type: Object, required: true },
  isLoading: { type: Boolean, default: false },
  error: { type: Object, default: null },
})

const emit = defineEmits(['update:selected', 'retry'])

const options = (items, toOption) => (items ?? []).map(toOption)

function select(field, value) {
  emit('update:selected', { ...props.selected, [field]: value })
}
</script>

<template>
  <section>
    <div class="bg-accent pb-35 pt-20">
      <BaseContainer>
        <div class="flex gap-8">
          <h2 class="basis-1/4 text-5xl font-bold text-inverse">Список курсов</h2>
          <p class="basis-2/5 text-lg font-medium text-inverse">
            Изучите наш широкий каталог курсов, специально разработанных для медицинских
            специалистов. Вы можете фильтровать курсы по специализации, сложности и типу
            кредитования, чтобы найти именно то, что вам нужно.
          </p>
        </div>

        <div class="flex gap-2 pt-14">
          <div
            class="flex flex-1 items-center rounded-l-xl bg-page px-8 py-7 text-xl font-bold text-ink"
          >
            Фильтры:
          </div>
          <BaseSelect
            class="flex-1"
            :model-value="props.selected.specialization"
            :options="options(props.filters.specializations, (i) => ({ value: i.slug, label: i.name }))"
            placeholder="Специализация"
            @update:model-value="select('specialization', $event)"
          />
          <BaseSelect
            class="flex-1"
            :model-value="props.selected.difficulty"
            :options="options(props.filters.difficulties, (i) => ({ value: i, label: difficultyLabel(i) }))"
            placeholder="Сложность"
            @update:model-value="select('difficulty', $event)"
          />
          <BaseSelect
            class="flex-1 rounded-r-xl"
            :model-value="props.selected.accreditation"
            :options="options(props.filters.accreditations, (i) => ({ value: i.slug, label: i.name }))"
            placeholder="Тип кредитования"
            @update:model-value="select('accreditation', $event)"
          />
        </div>
      </BaseContainer>
    </div>

    <BaseContainer>
      <div class="-mt-28 rounded-xl bg-page p-8">
        <p v-if="props.isLoading" class="py-35 text-center text-lg font-semibold text-subtle">
          Загружаем курсы…
        </p>

        <div v-else-if="props.error" class="flex flex-col items-center gap-5 py-35">
          <p class="text-lg font-semibold text-subtle">Не удалось загрузить каталог курсов</p>
          <button class="text-base font-bold text-accent" type="button" @click="emit('retry')">
            Попробовать ещё раз
          </button>
        </div>

        <p
          v-else-if="props.courses.length === 0"
          class="py-35 text-center text-lg font-semibold text-subtle"
        >
          По выбранным фильтрам курсов пока нет
        </p>

        <div v-else class="grid grid-cols-3 gap-8">
          <CourseCard v-for="course in props.courses" :key="course.id" :course="course" />
        </div>

        <p
          v-if="!props.isLoading && !props.error && props.courses.length > 0"
          class="pt-14 text-center text-lg font-semibold text-subtle"
        >
          Посмотреть больше курсов
        </p>
      </div>
    </BaseContainer>
  </section>
</template>
