<script setup>
defineProps({
  courseSlug: { type: String, default: '' },
})
</script>

<template>
  <!-- Материалы закрыты. Пишем прямо и без обещаний, которых система пока не выполняет:
       оплаты на сайте нет, доступ открывает учебная часть. -->
  <div class="flex flex-col items-center gap-5 rounded-xl bg-page px-4 py-16 text-center lg:py-24">
    <h1 class="max-w-lg text-xl font-bold text-ink lg:text-2xl">Материалы курса пока закрыты</h1>
    <p class="max-w-lg text-sm font-medium leading-relaxed text-muted">
      Доступ к лекциям открывает учебная часть академии — после того, как вы записались на цикл.
      Программа курса и его описание остаются открытыми.
    </p>
    <RouterLink
      v-if="courseSlug"
      class="text-base font-bold text-accent"
      :to="`/courses/${courseSlug}`"
    >
      Вернуться к курсу
    </RouterLink>
  </div>
</template>
