<script setup>
import IconChevronDown from '@/core/components/icons/IconChevronDown.vue'

defineProps({
  placeholder: { type: String, required: true },
  options: { type: Array, default: () => [] },
})

const model = defineModel({ type: String, default: '' })
</script>

<template>
  <div class="relative flex items-center bg-page">
    <select
      v-model="model"
      class="w-full appearance-none bg-page px-8 py-7 text-sm font-semibold text-subtle"
    >
      <option value="">{{ placeholder }}</option>
      <option v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
    <IconChevronDown class="pointer-events-none absolute right-8 w-3 text-neutral-500" />
  </div>
</template>
