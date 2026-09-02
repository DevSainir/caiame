<template>
  <!-- Материалы закрыты. Пишем прямо и без обещаний, которых система пока не выполняет:
       оплаты на сайте нет, доступ открывает учебная часть.
       Ссылка обязательна: без неё экран — тупик, из которого выходят только кнопкой
       «назад». Ведёт в каталог, а не на страницу курса: какой это курс, отказ не
       сообщает — и правильно делает. -->
  <div class="flex flex-col items-center gap-5 rounded-xl bg-page px-4 py-16 text-center lg:py-24">
    <h1 class="max-w-lg text-xl font-bold text-ink lg:text-2xl">Материалы курса пока закрыты</h1>
    <p class="max-w-lg text-sm font-medium leading-relaxed text-muted">
      Доступ к лекциям открывает учебная часть академии — после того, как вы записались на цикл.
      Программа курса и его описание остаются открытыми.
    </p>
    <RouterLink class="text-base font-bold text-accent" to="/">Ко всем курсам</RouterLink>
  </div>
</template>
