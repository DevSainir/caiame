<script setup>
import { computed, ref, useId } from 'vue'
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
// Текст ошибки надо не только показать, но и связать с полем: иначе экранный диктор
// прочитает поле и промолчит о том, что с ним не так.
const errorId = useId()

const isPassword = computed(() => props.type === 'password')
const inputType = computed(() => (isPassword.value && isRevealed.value ? 'text' : props.type))
</script>

<template>
  <div class="flex flex-col gap-2">
    <!-- Кольцо на focus-within обязательно: у самого поля выключен браузерный контур, и без
         замены человек, идущий по форме с клавиатуры, не видит, где он находится. -->
    <div
      class="flex items-center gap-4 rounded-lg border bg-page px-5 py-5 focus-within:ring-2 focus-within:ring-primary-500 lg:py-6"
      :class="props.error ? 'border-danger-500' : 'border-neutral-900'"
    >
      <input
        v-model="model"
        :aria-describedby="props.error ? errorId : undefined"
        :aria-invalid="props.error ? 'true' : undefined"
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

    <p v-if="props.error" :id="errorId" class="text-xs font-medium text-danger-600">
      {{ props.error }}
    </p>
  </div>
</template>
