<script setup>
defineProps({
  label: { type: String, required: true },
  hint: { type: String, default: '' },
})
</script>

<template>
  <label class="flex flex-col gap-2">
    <span class="text-xs font-semibold text-muted">{{ label }}</span>
    <slot />
    <span v-if="hint" class="text-2xs font-medium leading-relaxed text-subtle">{{ hint }}</span>
  </label>
</template>
