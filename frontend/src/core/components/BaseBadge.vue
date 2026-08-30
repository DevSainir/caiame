<template>
  <!-- Поля уже на телефоне: в мобильном макете тег заметно компактнее, и с десктопными
       40px три тега на карточке не помещаются в строку, промахиваясь на пиксель. -->
  <span
    class="inline-flex h-7 items-center justify-center rounded-sm bg-success-500 px-3 text-2xs font-semibold text-inverse lg:px-10"
  >
    <slot />
  </span>
</template>
