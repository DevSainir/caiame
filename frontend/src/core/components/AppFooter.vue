<script setup>
import AnchorLink from '@/core/components/AnchorLink.vue'
import BaseContainer from '@/core/components/BaseContainer.vue'

// Только то, что действительно открывается. Ссылка на страницу, которой нет, хуже её
// отсутствия: человек по ней уходит и возвращается ни с чем.
const COLUMNS = [
  [
    { label: 'Курсы', anchor: 'courses' },
    { label: 'Личный кабинет', to: '/profile' },
  ],
  [
    { label: 'Регистрация', to: '/register' },
    { label: 'Войти', to: '/login' },
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

        <!-- Название занимает половину ширины на десктопе, ссылки — по колонке на
             каждую группу. -->
        <div class="grid grid-cols-2 gap-x-5 gap-y-6 pt-8 lg:grid-cols-4 lg:gap-0 lg:pt-0">
          <p class="hidden text-xl font-bold lg:col-span-2 lg:block">
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
