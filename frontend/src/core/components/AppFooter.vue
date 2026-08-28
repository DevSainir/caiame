<script setup>
import BaseContainer from '@/core/components/BaseContainer.vue'

const COLUMNS = [
  [
    { label: 'Курсы', to: '/courses' },
    { label: 'Форум и чат', to: '/support' },
    { label: 'Контакты', to: '/support' },
  ],
  [
    { label: 'Личный кабинет', to: '/profile' },
    { label: 'Администрирование', to: '/profile' },
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
      <div class="pb-24 pt-25">
        <div class="grid grid-cols-4">
          <p class="text-xl font-bold">Платформа Непрерывного Медицинского Образования</p>

          <ul v-for="(column, index) in COLUMNS" :key="index" class="flex flex-col gap-6">
            <li v-for="link in column" :key="link.label">
              <RouterLink class="text-base" :to="link.to">{{ link.label }}</RouterLink>
            </li>
          </ul>
        </div>

        <p class="pt-25 text-xs font-medium">
          © 2026 Центрально азиатский институт дополнительного медицинского образования
        </p>
      </div>
    </BaseContainer>
  </footer>
</template>
