<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import BaseContainer from '@/core/components/BaseContainer.vue'
import IconUser from '@/core/components/icons/IconUser.vue'
import { useAuthStore } from '@/features/auth/store'
import logoUrl from '@/assets/images/logo.svg'

const route = useRoute()
const auth = useAuthStore()

// Auth screens put the page name in the middle and offer the way back instead of the
// action the visitor is already performing.
const title = computed(() => route.meta.headerTitle ?? null)

const GUEST_LINKS = {
  login: [
    { label: 'Регистрация', to: '/register' },
    { label: 'Вернуться на главную', to: '/' },
  ],
  register: [
    { label: 'Войти', to: '/login' },
    { label: 'Вернуться на главную', to: '/' },
  ],
  default: [
    { label: 'Войти', to: '/login' },
    { label: 'Зарегистрироваться', to: '/register' },
  ],
}

const guestLinks = computed(() => GUEST_LINKS[route.name] ?? GUEST_LINKS.default)

// На телефоне экраны входа оставляют только выход обратно — так в макете, и это
// единственное, что помещается рядом с логотипом на 360px.
const isAuthPage = computed(() => title.value !== null)
</script>

<template>
  <header class="bg-page">
    <BaseContainer>
      <div class="flex h-15 items-center justify-between lg:grid lg:h-20 lg:grid-cols-3">
        <RouterLink to="/">
          <img :src="logoUrl" alt="ЦАИДМО" class="h-6 lg:h-7" />
        </RouterLink>

        <!-- Середина шапки на телефон не помещается: каталог и так ниже на этой же
             странице, а название экрана дублирует заголовок под шапкой. -->
        <nav class="hidden lg:block lg:justify-self-center">
          <span v-if="title" class="text-base font-bold text-ink">{{ title }}</span>
          <RouterLink v-else class="text-base font-bold text-ink" to="/courses">
            Изучить курсы
          </RouterLink>
        </nav>

        <RouterLink
          v-if="auth.isReady && auth.isAuthenticated"
          aria-label="Личный кабинет"
          class="text-ink lg:justify-self-end"
          to="/profile"
        >
          <IconUser class="w-6" />
        </RouterLink>
        <div v-else-if="auth.isReady" class="flex items-center gap-3 lg:gap-8 lg:justify-self-end">
          <RouterLink
            class="text-xs font-semibold text-ink lg:text-sm"
            :class="{ 'hidden lg:block': isAuthPage }"
            :to="guestLinks[0].to"
          >
            {{ guestLinks[0].label }}
          </RouterLink>
          <span class="h-4 w-px bg-neutral-400" :class="{ 'hidden lg:block': isAuthPage }" />
          <RouterLink class="text-xs font-semibold text-ink lg:text-sm" :to="guestLinks[1].to">
            {{ guestLinks[1].label }}
          </RouterLink>
        </div>
      </div>
    </BaseContainer>
  </header>
</template>
