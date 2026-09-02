<script setup>
import { storeToRefs } from 'pinia'
import { useNotificationStore } from '@/core/notifications/store'

const { items } = storeToRefs(useNotificationStore())

const TONES = {
  success: 'bg-success-500 text-inverse',
  danger: 'bg-danger-500 text-inverse',
}
</script>

<template>
  <div
    aria-live="polite"
    class="pointer-events-none fixed bottom-6 right-6 z-notice flex flex-col gap-3"
    role="status"
  >
    <!-- Живая область одна и объявлена на контейнере, который есть на странице всегда:
         диктор читает то, что появляется внутри уже существующей области, а область,
         возникшую вместе с текстом, может и не заметить. На самих сообщениях роли нет
         намеренно — вложенная область спорит с внешней, и что из них прочитают, зависит
         от диктора. -->
    <TransitionGroup
      enter-active-class="transition"
      enter-from-class="translate-y-3 opacity-0"
      leave-active-class="transition"
      leave-to-class="translate-y-3 opacity-0"
    >
      <div
        v-for="item in items"
        :key="item.id"
        class="pointer-events-auto rounded-lg px-6 py-4 text-sm font-semibold"
        :class="TONES[item.tone] ?? TONES.success"
      >
        {{ item.text }}
      </div>
    </TransitionGroup>
  </div>
</template>
