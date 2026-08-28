<script setup>
import AppFooter from '@/core/components/AppFooter.vue'
import AppHeader from '@/core/components/AppHeader.vue'
import AppToaster from '@/core/components/AppToaster.vue'
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <AppHeader />
    <main class="flex-1">
      <RouterView />
    </main>
    <AppFooter />
    <AppToaster />
  </div>
</template>
