<template>
  <!-- Поля 20px на телефоне — те же 6.25% ширины, что и в макете. На десктопе колонка
       упирается в max-w-container, и поля получаются сами. -->
  <div class="px-5 lg:px-6">
    <div class="mx-auto w-full max-w-container">
      <slot />
    </div>
  </div>
</template>
