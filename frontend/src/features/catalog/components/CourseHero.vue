<script setup>
import { computed } from 'vue'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseContainer from '@/core/components/BaseContainer.vue'
import CourseFact from '@/features/catalog/components/CourseFact.vue'
import { audienceLabel } from '@/features/catalog/labels'
import { formatHours, formatPrice } from '@/features/catalog/format'
import { useAuthStore } from '@/core/session/store'

const props = defineProps({
  course: { type: Object, required: true },
})

const auth = useAuthStore()

// Язык в макете стоит рядом с ценой и длительностью, но полем курса он не является:
// платформа целиком русскоязычная. Появятся кыргызоязычные курсы — станет полем.
const LANGUAGE = 'Русский'

const facts = computed(() => [
  { value: audienceLabel(props.course.specialization?.audience), label: 'аудитория специализации' },
  { value: formatPrice(props.course.price_minor, props.course.currency), label: 'стоимость курса' },
  { value: formatHours(props.course.duration_hours), label: 'длительность обучения' },
  { value: LANGUAGE, label: 'язык курса' },
])

// Строка над заголовком: в макете это издатель, которого у нас нет. Специализация — то же
// самое по смыслу: она говорит, куда курс входит. Пока в ней один курс, строка повторяет
// заголовок.
const eyebrow = computed(() => `Специализация: ${props.course.specialization?.name ?? ''}`)
</script>

<template>
  <!-- Телефон: заголовок над картинкой, карточки лежат на её нижнем крае. -->
  <section class="pb-8 pt-6 lg:hidden">
    <BaseContainer>
      <p class="text-xs font-medium text-muted">{{ eyebrow }}</p>
      <h1 class="pt-3 text-2xl font-bold text-primary-500">{{ props.course.title }}</h1>

      <div class="relative mt-6 overflow-hidden rounded-lg">
        <img
          :alt="props.course.title"
          class="aspect-square w-full object-cover"
          :src="props.course.cover_url"
        />
        <div class="absolute inset-x-0 bottom-0 grid grid-cols-2 gap-2 p-2">
          <CourseFact
            v-for="fact in facts"
            :key="fact.label"
            :label="fact.label"
            :value="fact.value"
          />
        </div>
      </div>

      <BaseButton v-if="auth.isReady && !auth.isAuthenticated" class="mt-5 w-full" to="/register">
        Зарегистрироваться
      </BaseButton>
    </BaseContainer>
  </section>

  <!-- Десктоп: то же самое поверх обложки во всю ширину экрана. -->
  <section class="relative hidden overflow-hidden lg:block">
    <img
      :alt="props.course.title"
      class="absolute inset-0 h-full w-full object-cover"
      :src="props.course.cover_url"
    />
    <!-- В макете обложка — тёмная фотография, у нас пока сгенерированная светлая заглушка.
         Затемнение делает белый заголовок читаемым на любой из них. -->
    <div class="absolute inset-0 bg-neutral-950 opacity-50" />

    <BaseContainer class="relative">
      <div class="pb-15 pt-35">
        <p class="text-base font-medium text-inverse">{{ eyebrow }}</p>
        <h1 class="max-w-xl pt-3 text-5xl font-bold text-inverse">{{ props.course.title }}</h1>

        <div class="flex items-stretch gap-2 pt-35">
          <CourseFact
            v-for="fact in facts"
            :key="fact.label"
            class="flex-1"
            :label="fact.label"
            :value="fact.value"
          />
          <BaseButton
            v-if="auth.isReady && !auth.isAuthenticated"
            class="flex-1 rounded-xl"
            to="/register"
          >
            Зарегистрироваться
          </BaseButton>
        </div>
      </div>
    </BaseContainer>
  </section>
</template>
