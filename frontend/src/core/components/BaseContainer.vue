<template>
  <!-- Поля 20px на телефоне — те же 6.25% ширины, что и в макете. На десктопе колонка
       упирается в max-w-container, и поля получаются сами. Между телефоном и десктопом
       макета нет, поэтому телефонная колонка не растягивается, а стоит по центру. -->
  <div class="px-5 lg:px-6">
    <div class="mx-auto w-full max-w-phone lg:max-w-container">
      <slot />
    </div>
  </div>
</template>
