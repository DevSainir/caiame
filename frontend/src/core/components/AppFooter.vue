<script setup>
import AnchorLink from '@/core/components/AnchorLink.vue'
import BaseContainer from '@/core/components/BaseContainer.vue'

const COLUMNS = [
  [
    { label: 'Курсы', anchor: 'courses' },
    { label: 'Форум и чат', to: '/support' },
    { label: 'Контакты', to: '/support' },
  ],
  [
    { label: 'Личный кабинет', to: '/profile' },
    { label: 'Администрирование', to: '/admin' },
    { label: 'О нас', to: '/support' },
  ],
  [
    { label: 'Регистрация', to: '/register' },
    { label: 'Войти', to: '/login' },
    { label: 'Техподдержка', to: '/support' },
  ],
]
</script>

<template>
  <footer class="bg-inverse text-inverse">
    <BaseContainer>
      <div class="pb-10 pt-10 lg:pb-24 lg:pt-25">
        <!-- Название над колонками на телефоне, слева от них на десктопе. -->
        <p class="text-lg font-bold lg:hidden">
          Центрально-Азиатский Институт Дополнительного Медицинского Образования
        </p>

        <!-- Две колонки, а не три: на 360px в треть ширины не помещается
             «Администрирование», и оно наезжает на соседнюю колонку. -->
        <div class="grid grid-cols-2 gap-x-5 gap-y-6 pt-8 lg:grid-cols-4 lg:gap-0 lg:pt-0">
          <p class="hidden text-xl font-bold lg:block">
            Центрально-Азиатский Институт Дополнительного Медицинского Образования
          </p>

          <ul v-for="(column, index) in COLUMNS" :key="index" class="flex flex-col gap-3 lg:gap-6">
            <li v-for="link in column" :key="link.label">
              <AnchorLink v-if="link.anchor" :anchor="link.anchor" class="text-xs lg:text-base">
                {{ link.label }}
              </AnchorLink>
              <RouterLink v-else class="text-xs lg:text-base" :to="link.to">
                {{ link.label }}
              </RouterLink>
            </li>
          </ul>
        </div>

        <p class="pt-10 text-2xs font-medium lg:pt-25 lg:text-xs">
          © 2026 Центрально-Азиатский Институт Дополнительного Медицинского Образования
        </p>
      </div>
    </BaseContainer>
  </footer>
</template>
