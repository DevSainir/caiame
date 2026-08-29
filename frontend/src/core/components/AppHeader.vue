<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AnchorLink from '@/core/components/AnchorLink.vue'
import BaseContainer from '@/core/components/BaseContainer.vue'
import IconUser from '@/core/components/icons/IconUser.vue'
import { scrollToTop } from '@/core/scroll'
import { useAuthStore } from '@/core/session/store'
import { useNotificationStore } from '@/core/notifications/store'
import logoUrl from '@/assets/images/logo.svg'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const notifications = useNotificationStore()
const isSigningOut = ref(false)

/**
 * Выход из аккаунта.
 *
 * Уводим на главную только с закрытых страниц: с открытой странице незачем никуда
 * прыгать, а неожиданный переход после нажатия читается как сбой.
 */
async function signOut() {
  if (isSigningOut.value) return
  isSigningOut.value = true
  try {
    await auth.signOut()
    notifications.notify('Вы вышли из аккаунта')
    if (route.meta.requiresAuth) await router.push('/')
  } catch {
    notifications.notify('Не удалось выйти. Проверьте соединение и попробуйте ещё раз', 'danger')
  } finally {
    isSigningOut.value = false
  }
}

/**
 * Логотип на уже открытой главной.
 *
 * Роутер повторный переход на тот же адрес отменяет, поэтому прокрутку наверх делаем сами:
 * иначе нажатие на логотип со середины страницы не делает ничего и читается как поломка.
 */
function goHome(event) {
  if (route.path !== '/' || event.metaKey || event.ctrlKey || event.shiftKey) return
  event.preventDefault()
  scrollToTop()
}

// Auth screens put the page name in the middle and offer the way back instead of the
// action the visitor is already performing.
const title = computed(() => route.meta.headerTitle ?? null)

// Экран входа предлагает регистрацию, экран регистрации — вход: второе действие, а не то,
// которое человек уже выполняет. Назад ведёт логотип, отдельной ссылки для этого нет.
const GUEST_LINKS = {
  login: [{ label: 'Регистрация', to: '/register' }],
  register: [{ label: 'Войти', to: '/login' }],
  default: [
    { label: 'Войти', to: '/login' },
    { label: 'Зарегистрироваться', to: '/register' },
  ],
}

const guestLinks = computed(() => GUEST_LINKS[route.name] ?? GUEST_LINKS.default)
</script>

<template>
  <header class="bg-page">
    <BaseContainer>
      <div class="flex h-15 items-center justify-between lg:grid lg:h-20 lg:grid-cols-3">
        <RouterLink to="/" @click="goHome">
          <img :src="logoUrl" alt="ЦАИДМО" class="h-6 lg:h-7" />
        </RouterLink>

        <!-- Середина шапки на телефон не помещается: каталог и так ниже на этой же
             странице, а название экрана дублирует заголовок под шапкой. -->
        <nav class="hidden lg:block lg:justify-self-center">
          <span v-if="title" class="text-base font-bold text-ink">{{ title }}</span>
          <AnchorLink v-else anchor="courses" class="text-base font-bold text-ink">
            Изучить курсы
          </AnchorLink>
        </nav>

        <!-- Состояния «вошёл» в макете нет, поэтому берём словарь самой шапки:
             иконка, тот же серый разделитель, ссылка тем же начертанием. -->
        <div
          v-if="auth.isReady && auth.isAuthenticated"
          class="flex items-center gap-3 lg:gap-8 lg:justify-self-end"
        >
          <RouterLink aria-label="Личный кабинет" class="text-ink" to="/profile">
            <IconUser class="w-6" />
          </RouterLink>
          <span class="h-3 w-0.25 bg-neutral-400 lg:h-3.5" />
          <button
            class="text-xs font-semibold text-ink disabled:opacity-50 lg:text-sm"
            :disabled="isSigningOut"
            type="button"
            @click="signOut"
          >
            Выйти
          </button>
        </div>
        <div v-else-if="auth.isReady" class="flex items-center gap-3 lg:gap-8 lg:justify-self-end">
          <template v-for="(link, index) in guestLinks" :key="link.label">
            <!-- Палочка между ссылками: 1px на 14px по макету. Цвет макета отличается
                 от neutral-400 на две единицы в канале — берём ступень шкалы. -->
            <span v-if="index > 0" class="h-3 w-0.25 bg-neutral-400 lg:h-3.5" />
            <RouterLink class="text-xs font-semibold text-ink lg:text-sm" :to="link.to">
              {{ link.label }}
            </RouterLink>
          </template>
        </div>
      </div>
    </BaseContainer>
  </header>
</template>
