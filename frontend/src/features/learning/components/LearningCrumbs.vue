<script setup>
const props = defineProps({
  course: { type: Object, required: true },
  module: { type: Object, default: null },
})
</script>

<template>
  <!-- Путь наверх. В десктопном макете его нет — там курс назван только в шапке, — но без
       него со страницы лекции некуда вернуться, кроме кнопки браузера. -->
  <div class="flex flex-col gap-3">
    <RouterLink
      class="text-lg font-bold text-primary-500 lg:text-2xl"
      :to="`/courses/${props.course.slug}`"
    >
      {{ props.course.title }}
    </RouterLink>

    <RouterLink
      v-if="props.module"
      class="w-full rounded-xl bg-page px-4 py-5 text-lg font-bold text-primary-500 lg:px-15 lg:py-6"
      :to="`/modules/${props.module.id}`"
    >
      {{ props.module.title }}
    </RouterLink>
  </div>
</template>
