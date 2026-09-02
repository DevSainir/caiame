<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
})
const emit = defineEmits(['close'])

const dialog = ref(null)
// Куда вернуть фокус: человек открыл окно с какой-то кнопки, и после закрытия он ждёт себя
// там же, а не в начале страницы.
let opener = null

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]),' +
  ' textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

function focusable() {
  return [...(dialog.value?.querySelectorAll(FOCUSABLE) ?? [])]
}

/**
 * Клавиатура внутри окна.
 *
 * Escape закрывает: этого от него ждут. Tab ходит по кругу внутри окна — иначе фокус
 * уходит за затемнение, на страницу, которой в этот момент как бы нет: человек нажимает
 * Enter и попадает в кнопку, которой не видит.
 */
function onKey(event) {
  if (event.key === 'Escape') {
    emit('close')
    return
  }
  if (event.key !== 'Tab') return
  const items = focusable()
  if (!items.length) return
  const first = items[0]
  const last = items[items.length - 1]
  const active = document.activeElement
  if (!event.shiftKey && (active === last || !dialog.value?.contains(active))) {
    event.preventDefault()
    first.focus()
  } else if (event.shiftKey && (active === first || !dialog.value?.contains(active))) {
    event.preventDefault()
    last.focus()
  }
}

onMounted(() => {
  opener = document.activeElement
  document.addEventListener('keydown', onKey)
  // Первое поле, а не заголовок: окно почти всегда — форма, и человек начинает печатать.
  const items = focusable()
  ;(items.find((item) => item.tagName !== 'BUTTON') ?? items[0] ?? dialog.value)?.focus()
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
  opener?.focus?.()
})
</script>

<template>
  <div
    class="fixed inset-0 z-overlay flex items-end justify-center overflow-y-auto bg-neutral-900/50 p-4 lg:items-center"
    role="presentation"
    @click.self="emit('close')"
  >
    <div
      ref="dialog"
      :aria-label="props.title"
      aria-modal="true"
      class="w-full max-w-xl rounded-xl bg-page p-5 outline-none lg:p-8"
      role="dialog"
      tabindex="-1"
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
