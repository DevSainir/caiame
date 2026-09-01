<script setup>
import { computed } from 'vue'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseContainer from '@/core/components/BaseContainer.vue'
import CourseFact from '@/features/catalog/components/CourseFact.vue'
import { audienceLabel } from '@/features/catalog/labels'
import { formatHours, formatPrice } from '@/core/format'
import { useAuthStore } from '@/core/session/store'

const props = defineProps({
  course: { type: Object, required: true },
  // Что известно о доступе. Приходит вместе с планом курса и до его загрузки равно null —
  // тогда кнопки нет вовсе: мигнуть «зарегистрируйтесь» вошедшему студенту хуже, чем
  // подождать полсекунды.
  access: { type: Object, default: null },
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

// Три состояния вместо одного. Гостю — регистрация, как в макете. Вошедшему без доступа —
// объяснение, а не кнопка: записывает на цикл учебная часть, и ссылки, которая бы это
// сделала, не существует. Тому, у кого доступ есть, — вход в обучение.
const isGuest = computed(() => auth.isReady && !auth.isAuthenticated)
const hasAccess = computed(() => props.access?.has_access === true)
const isEnrolledButClosed = computed(
  () => auth.isReady && auth.isAuthenticated && props.access !== null && !hasAccess.value,
)
const firstModuleId = computed(() => props.access?.modules?.[0]?.id ?? null)

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

      <BaseButton v-if="isGuest" class="mt-5 w-full" to="/register">Зарегистрироваться</BaseButton>
      <BaseButton
        v-else-if="hasAccess && firstModuleId"
        class="mt-5 w-full"
        :to="`/modules/${firstModuleId}`"
      >
        Перейти к обучению
      </BaseButton>
      <p
        v-else-if="isEnrolledButClosed"
        class="mt-5 text-xs font-medium leading-relaxed text-muted"
      >
        Материалы откроет учебная часть академии, когда запишет вас на цикл.
      </p>
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
          <BaseButton v-if="isGuest" class="flex-1 rounded-xl" to="/register">
            Зарегистрироваться
          </BaseButton>
          <BaseButton
            v-else-if="hasAccess && firstModuleId"
            class="flex-1 rounded-xl"
            :to="`/modules/${firstModuleId}`"
          >
            Перейти к обучению
          </BaseButton>
          <p
            v-else-if="isEnrolledButClosed"
            class="flex-1 text-xs font-medium leading-relaxed text-muted"
          >
            Материалы откроет учебная часть академии, когда запишет вас на цикл.
          </p>
        </div>
      </div>
    </BaseContainer>
  </section>
</template>
