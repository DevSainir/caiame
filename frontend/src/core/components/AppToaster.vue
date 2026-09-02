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
    <!-- Живая область объявлена на контейнере, а не на самом сообщении: диктор читает то,
         что меняется внутри уже существующей области, а появившуюся вместе с текстом он
         может и не заметить. -->
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
        :role="item.tone === 'danger' ? 'alert' : 'status'"
      >
        {{ item.text }}
      </div>
    </TransitionGroup>
  </div>
</template>
