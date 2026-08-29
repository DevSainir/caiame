<script setup>
import BaseContainer from '@/core/components/BaseContainer.vue'

defineProps({
  benefits: { type: Array, default: () => [] },
})
</script>

<template>
  <section v-if="benefits.length > 0" class="pt-14 lg:pt-35">
    <BaseContainer>
      <h2 class="text-2xl font-bold text-ink lg:text-3xl">Почему именно этот курс?</h2>

      <!-- Две колонки, как на плакате курса; на телефоне блоки идут подряд. -->
      <dl class="grid gap-6 pt-5 lg:grid-cols-2 lg:gap-x-12 lg:gap-y-8 lg:pt-8">
        <div v-for="benefit in benefits" :key="benefit.id" class="flex flex-col gap-2">
          <dt class="text-base font-bold text-ink lg:text-lg">{{ benefit.title }}</dt>
          <dd class="text-sm font-medium leading-relaxed text-muted lg:text-base">
            {{ benefit.text }}
          </dd>
        </div>
      </dl>
    </BaseContainer>
  </section>
</template>
