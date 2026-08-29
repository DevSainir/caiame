<script setup>
import { useAnchorNavigation } from '@/core/scroll'

const props = defineProps({
  variant: { type: String, default: 'primary' },
  size: { type: String, default: 'md' },
  shape: { type: String, default: 'default' },
  type: { type: String, default: 'button' },
  disabled: { type: Boolean, default: false },
  to: { type: [String, Object], default: null },
  // Кнопка-якорь: ведёт на страницу и прокручивает к секции, не оставляя решётки в адресе.
  anchor: { type: String, default: null },
  // Тег вместо кнопки: карточка курса сама целиком ссылка, а ссылка внутри ссылки —
  // невалидная разметка. Внутри такой карточки кнопка остаётся только на вид.
  element: { type: String, default: null },
})

const navigateToAnchor = useAnchorNavigation()

const VARIANTS = {
  primary: 'bg-accent text-inverse hover:bg-primary-600',
  success: 'bg-success-500 text-inverse hover:bg-success-600',
  dark: 'bg-neutral-900 text-inverse hover:bg-neutral-800',
}

const SIZES = {
  sm: 'px-10 py-2 text-xs',
  md: 'px-8 py-2 text-base',
  lg: 'px-8 py-3 text-sm',
}

const SHAPES = {
  default: 'rounded-sm',
  pill: 'rounded-full',
}
</script>

<template>
  <component
    :is="props.element || (props.anchor ? 'a' : props.to ? 'RouterLink' : 'button')"
    :disabled="props.to || props.anchor || props.element ? undefined : props.disabled"
    :href="props.anchor && !props.element ? props.to || '/' : undefined"
    :to="props.anchor ? undefined : props.to"
    :type="props.to || props.anchor || props.element ? undefined : props.type"
    class="inline-flex items-center justify-center font-bold transition-colors disabled:opacity-50"
    :class="[VARIANTS[props.variant], SIZES[props.size], SHAPES[props.shape]]"
    @click="props.anchor && navigateToAnchor($event, { to: props.to || '/', anchor: props.anchor })"
  >
    <slot />
  </component>
</template>
