<script setup>
import BaseContainer from '@/core/components/BaseContainer.vue'

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})

const SECTIONS = [
  { label: 'Курсы', to: '/admin' },
  { label: 'Проверка работ', to: '/admin/submissions' },
  { label: 'Студенты и доступ', to: '/admin/access' },
]
</script>

<template>
  <div class="py-8 lg:py-14">
    <BaseContainer>
      <div class="flex flex-col gap-6 lg:flex-row lg:gap-8">
        <!-- Меню слева на широком экране, полосой сверху на телефоне: колонка в 240px
             съедает половину узкого экрана. -->
        <nav class="flex gap-2 overflow-x-auto lg:w-50 lg:shrink-0 lg:flex-col lg:gap-1">
          <RouterLink
            v-for="section in SECTIONS"
            :key="section.to"
            active-class="bg-subtle text-ink"
            class="whitespace-nowrap rounded-sm px-4 py-3 text-sm font-medium text-muted"
            :to="section.to"
          >
            {{ section.label }}
          </RouterLink>
        </nav>

        <div class="min-w-0 flex-1 overflow-hidden rounded-xl border border-subtle bg-page">
          <header
            class="flex flex-wrap items-center justify-between gap-4 border-b border-subtle px-5 py-5"
          >
            <div class="min-w-0">
              <slot name="breadcrumb" />
              <h1 class="text-2xl font-bold text-ink">{{ title }}</h1>
              <p v-if="subtitle" class="pt-2 text-xs font-medium text-subtle">{{ subtitle }}</p>
            </div>
            <div class="flex flex-wrap items-center gap-3">
              <slot name="actions" />
            </div>
          </header>

          <slot />
        </div>
      </div>
    </BaseContainer>
  </div>
</template>
