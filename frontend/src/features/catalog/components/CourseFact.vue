<script setup>
defineProps({
  value: { type: String, required: true },
  label: { type: String, required: true },
})
</script>

<template>
  <div class="flex flex-col justify-center rounded-lg bg-page px-4 py-3 lg:rounded-xl lg:px-6">
    <p class="text-base font-bold text-accent lg:text-lg">{{ value }}</p>
    <p class="text-2xs font-medium text-muted lg:text-xs">— {{ label }}</p>
  </div>
</template>
