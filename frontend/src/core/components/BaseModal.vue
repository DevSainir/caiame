<script setup>
import { onBeforeUnmount, onMounted } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
})
const emit = defineEmits(['close'])

// Escape закрывает окно, потому что этого от него ждут; клик по затемнению — тоже, но
// только по самому затемнению, иначе окно закрывается при выделении текста внутри формы.
function onKey(event) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-end justify-center overflow-y-auto bg-neutral-900/50 p-4 lg:items-center"
    role="presentation"
    @click.self="emit('close')"
  >
    <div
      :aria-label="props.title"
      class="w-full max-w-xl rounded-xl bg-page p-5 lg:p-8"
      role="dialog"
    >
      <div class="flex items-start justify-between gap-4">
        <h2 class="text-xl font-bold text-ink">{{ props.title }}</h2>
        <button
          aria-label="Закрыть"
          class="shrink-0 text-sm font-semibold text-subtle"
          type="button"
          @click="emit('close')"
        >
          ✕
        </button>
      </div>

      <div class="pt-5">
        <slot />
      </div>
    </div>
  </div>
</template>
