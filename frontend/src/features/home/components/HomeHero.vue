<script setup>
import BaseContainer from '@/core/components/BaseContainer.vue'
import IconArrowUpRight from '@/core/components/icons/IconArrowUpRight.vue'
import heroUrl from '@/assets/images/hero-laboratory.webp'

const ACTIONS = [
  { label: 'Войти', to: '/login', surface: 'bg-accent hover:bg-primary-600' },
  { label: 'Изучить курсы', to: '/courses', surface: 'bg-success-500 hover:bg-success-600' },
]
</script>

<template>
  <section class="pb-14 pt-8 lg:pb-35 lg:pt-18">
    <BaseContainer>
      <p class="text-lg font-medium text-subtle lg:text-4xl">Добро пожаловать в</p>
      <h1 class="max-w-xl pt-3 text-2xl font-bold text-primary-500 lg:pt-8 lg:text-5xl">
        Центрально-Азиатский Институт Дополнительного Медицинского Образования
      </h1>

      <!-- На телефоне картинка во всю ширину, кнопки под ней в две колонки;
           на десктопе кнопки становятся узкой колонкой справа. -->
      <div class="flex flex-col gap-5 pt-8 lg:flex-row lg:gap-8 lg:pt-14">
        <div class="relative aspect-square overflow-hidden rounded-xl lg:aspect-auto lg:basis-4/5">
          <img :src="heroUrl" alt="" class="h-full w-full object-cover" />
          <div
            class="absolute inset-0 bg-gradient-to-t from-neutral-950 via-transparent to-transparent"
          />
          <p
            class="absolute inset-x-0 bottom-0 max-w-xl p-5 text-sm font-medium text-inverse lg:p-12 lg:text-lg"
          >
            ЦАИДМО — ваш надежный помощник в обучении и повышении квалификации. Зарегистрируйтесь
            или войдите, чтобы начать обучение, которое поможет вам расти профессионально и
            расширять вашу карьеру.
          </p>
        </div>

        <div class="grid grid-cols-2 gap-2 lg:flex lg:basis-1/5 lg:flex-col lg:gap-8">
          <RouterLink
            v-for="action in ACTIONS"
            :key="action.label"
            :to="action.to"
            class="flex aspect-video flex-col justify-between rounded-xl p-5 text-inverse transition-colors lg:aspect-square lg:p-10"
            :class="action.surface"
          >
            <span class="text-lg font-bold lg:text-2xl">{{ action.label }}</span>
            <IconArrowUpRight class="w-5 self-end lg:w-6" />
          </RouterLink>
        </div>
      </div>
    </BaseContainer>
  </section>
</template>
