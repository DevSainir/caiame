<script setup>
import IconChevronDown from '@/core/components/icons/IconChevronDown.vue'

defineProps({
  placeholder: { type: String, required: true },
  options: { type: Array, default: () => [] },
})

const model = defineModel({ type: String, default: '' })
</script>

<template>
  <div class="relative flex items-center overflow-hidden bg-page">
    <select
      v-model="model"
      class="w-full appearance-none bg-page px-5 py-4 text-xs font-semibold text-subtle lg:px-8 lg:py-7 lg:text-sm"
    >
      <option value="">{{ placeholder }}</option>
      <option v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
    <IconChevronDown
      class="pointer-events-none absolute right-5 w-2 text-neutral-500 lg:right-8 lg:w-3"
    />
  </div>
</template>
