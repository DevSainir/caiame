<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { setNoIndex } from '@/core/page'

// Адрес существует и отвечает двумястами — страницу рисует приложение, — поэтому от
// поисковика её закрывает метка, а не код ответа.
onMounted(() => setNoIndex(true))
onBeforeUnmount(() => setNoIndex(false))
</script>

<template>
  <section
    class="mx-auto flex max-w-phone flex-col items-center gap-6 px-4 py-24 text-center lg:max-w-container lg:px-25 lg:py-35"
  >
    <h1 class="text-2xl font-bold text-ink lg:text-3xl">Такой страницы нет</h1>
    <p class="max-w-lg text-sm font-medium leading-relaxed text-muted">
      Возможно, ссылка устарела или в адресе опечатка.
    </p>
    <RouterLink class="text-base font-bold text-accent" to="/">На главную</RouterLink>
  </section>
</template>
