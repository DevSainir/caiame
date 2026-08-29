<script setup>
import { useAnchorNavigation } from '@/core/scroll'

const props = defineProps({
  // Страница, на которой живёт якорь. По умолчанию главная: других якорей пока нет.
  to: { type: String, default: '/' },
  anchor: { type: String, required: true },
})

const navigateToAnchor = useAnchorNavigation()
</script>

<template>
  <a :href="props.to" @click="navigateToAnchor($event, { to: props.to, anchor: props.anchor })">
    <slot />
  </a>
</template>
