<script setup>
import { computed } from 'vue'

// Ближе этого к краю подпись значения встаёт на место подписи края — тогда край не рисуем.
const EDGE_PERCENT = 8

const props = defineProps({
  percent: { type: Number, required: true },
})

const clamped = computed(() => Math.min(100, Math.max(0, Math.round(props.percent))))

// Ширина полосы и место подписи — доли от ширины блока, а не размер: токеном такое не
// выражается, поэтому это единственные два инлайновых стиля на странице.
const fill = computed(() => ({ width: `${clamped.value}%` }))

/**
 * Подпись едет вместе с бегунком, но не вылезает за полосу.
 *
 * У краёв она прижимается к своему концу, а не центрируется по бегунку: на нуле
 * отцентрированная подпись наполовину уезжает за левый край и наезжает на «0%».
 */
const marker = computed(() => {
  const shift =
    clamped.value <= EDGE_PERCENT ? '0%' : clamped.value >= 100 - EDGE_PERCENT ? '-100%' : '-50%'
  return { left: `${clamped.value}%`, transform: `translateX(${shift})` }
})

const showStart = computed(() => clamped.value > EDGE_PERCENT)
const showEnd = computed(() => clamped.value < 100 - EDGE_PERCENT)
</script>

<template>
  <div class="rounded-lg bg-page px-4 py-5 lg:rounded-none lg:px-0 lg:py-8">
    <h3 class="text-lg font-bold text-ink lg:text-2xl">Прогресс курса</h3>

    <div class="pt-4 lg:pt-6">
      <!-- Края подписаны, пока на их месте не оказалось само значение. -->
      <div class="relative flex justify-between text-xs font-semibold text-disabled lg:text-sm">
        <span :class="showStart ? '' : 'invisible'">0%</span>
        <span class="absolute text-accent" :style="marker">{{ clamped }}%</span>
        <span :class="showEnd ? '' : 'invisible'">100%</span>
      </div>

      <div class="mt-2 h-2 rounded-full bg-neutral-100">
        <div class="relative h-full rounded-full bg-accent" :style="fill">
          <span
            class="absolute right-0 top-1/2 h-4 w-4 -translate-y-1/2 translate-x-1/2 rounded-full bg-accent"
          />
        </div>
      </div>
    </div>
  </div>
</template>
