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
  <section class="pb-35 pt-18">
    <BaseContainer>
      <p class="text-4xl font-medium text-subtle">Добро пожаловать на</p>
      <h1 class="max-w-xl pt-8 text-5xl font-bold text-primary-500">
        Платформу Непрерывного Медицинского Образования
      </h1>

      <div class="flex gap-8 pt-14">
        <div class="relative basis-4/5 overflow-hidden rounded-xl">
          <img :src="heroUrl" alt="" class="h-full w-full object-cover" />
          <div
            class="absolute inset-0 bg-gradient-to-t from-neutral-950 via-transparent to-transparent"
          />
          <p class="absolute inset-x-0 bottom-0 max-w-xl p-12 text-lg font-medium text-inverse">
            Платформа НМО — ваш надежный помощник в обучении и повышении квалификации.
            Зарегистрируйтесь или войдите, чтобы начать обучение, которое поможет вам расти
            профессионально и расширять вашу карьеру.
          </p>
        </div>

        <div class="flex basis-1/5 flex-col gap-8">
          <RouterLink
            v-for="action in ACTIONS"
            :key="action.label"
            :to="action.to"
            class="flex aspect-square flex-col justify-between rounded-xl p-10 text-inverse transition-colors"
            :class="action.surface"
          >
            <span class="text-2xl font-bold">{{ action.label }}</span>
            <IconArrowUpRight class="w-6 self-end" />
          </RouterLink>
        </div>
      </div>
    </BaseContainer>
  </section>
</template>
