<script setup>
const props = defineProps({
  variant: { type: String, default: 'primary' },
  size: { type: String, default: 'md' },
  shape: { type: String, default: 'default' },
  type: { type: String, default: 'button' },
  disabled: { type: Boolean, default: false },
  to: { type: [String, Object], default: null },
})

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
    :is="props.to ? 'RouterLink' : 'button'"
    :disabled="props.to ? undefined : props.disabled"
    :to="props.to"
    :type="props.to ? undefined : props.type"
    class="inline-flex items-center justify-center font-bold transition-colors disabled:opacity-50"
    :class="[VARIANTS[props.variant], SIZES[props.size], SHAPES[props.shape]]"
  >
    <slot />
  </component>
</template>
