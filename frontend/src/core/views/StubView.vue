<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <section class="mx-auto flex max-w-container flex-col items-center gap-6 px-25 py-35">
    <h1 class="text-3xl font-bold">Раздел в разработке</h1>
    <p class="text-base text-muted">
      Страница «{{ route.name }}» появится в одном из ближайших релизов.
    </p>
    <RouterLink class="text-base font-semibold text-accent" to="/">На главную</RouterLink>
  </section>
</template>
