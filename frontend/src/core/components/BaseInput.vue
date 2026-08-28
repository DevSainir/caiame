<script setup>
import { computed, ref } from 'vue'
import IconEyeClosed from '@/core/components/icons/IconEyeClosed.vue'
import IconEyeOpen from '@/core/components/icons/IconEyeOpen.vue'

const props = defineProps({
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  error: { type: String, default: '' },
  autocomplete: { type: String, default: 'off' },
})

const model = defineModel({ type: String, default: '' })
const isRevealed = ref(false)

const isPassword = computed(() => props.type === 'password')
const inputType = computed(() => (isPassword.value && isRevealed.value ? 'text' : props.type))
</script>

<template>
  <div class="flex flex-col gap-2">
    <div
      class="flex items-center gap-4 rounded-lg border bg-page px-5 py-6"
      :class="props.error ? 'border-danger-500' : 'border-neutral-900'"
    >
      <input
        v-model="model"
        :autocomplete="props.autocomplete"
        class="w-full bg-page text-sm font-medium text-ink outline-none placeholder:text-subtle"
        :placeholder="props.placeholder"
        :type="inputType"
      />
      <button
        v-if="isPassword"
        :aria-label="isRevealed ? 'Скрыть пароль' : 'Показать пароль'"
        class="shrink-0 text-subtle"
        type="button"
        @click="isRevealed = !isRevealed"
      >
        <IconEyeClosed v-if="isRevealed" class="w-5" />
        <IconEyeOpen v-else class="w-5" />
      </button>
    </div>

    <p v-if="props.error" class="text-xs font-medium text-danger-600">{{ props.error }}</p>
  </div>
</template>
