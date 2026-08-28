<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseInput from '@/core/components/BaseInput.vue'
import { describeFailure } from '@/features/auth/failures'
import { useAuthStore } from '@/features/auth/store'
import { useNotificationStore } from '@/core/notifications/store'
import { validateEmail } from '@/features/auth/validation'

const router = useRouter()
const auth = useAuthStore()
const notifications = useNotificationStore()

const form = reactive({ email: '', password: '' })
const errors = reactive({ email: '', password: '', form: '' })
const isSubmitting = ref(false)

const canSubmit = computed(() => form.email !== '' && form.password !== '' && !isSubmitting.value)

function clear(field) {
  errors[field] = ''
  errors.form = ''
}

async function submit() {
  errors.email = validateEmail(form.email)
  // No length rule on sign-in: the password was accepted at registration, and telling a
  // visitor their existing password is "too short" is both wrong and a hint to an attacker.
  errors.password = form.password === '' ? 'Введите пароль' : ''
  errors.form = ''
  if (errors.email || errors.password) return

  isSubmitting.value = true
  try {
    await auth.signIn({ email: form.email.trim(), password: form.password })
    notifications.notify('С возвращением!')
    router.push('/')
  } catch (failure) {
    errors.form = describeFailure(failure, 'Не получилось войти. Попробуйте ещё раз.')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <section class="flex justify-center px-5 pb-20 pt-10 lg:px-6 lg:pb-35 lg:pt-25">
    <form class="flex w-full max-w-card flex-col gap-6 lg:gap-8" novalidate @submit.prevent="submit">
      <h1 class="text-2xl font-semibold text-ink lg:text-3xl">Укажите почту и пароль от аккаунта</h1>

      <div class="flex flex-col gap-5">
        <BaseInput
          v-model="form.email"
          autocomplete="email"
          :error="errors.email"
          placeholder="Почта*"
          type="email"
          @update:model-value="clear('email')"
        />
        <BaseInput
          v-model="form.password"
          autocomplete="current-password"
          :error="errors.password"
          placeholder="Пароль*"
          type="password"
          @update:model-value="clear('password')"
        />
      </div>

      <p v-if="errors.form" class="text-sm font-semibold text-danger-600">{{ errors.form }}</p>

      <div class="flex items-center justify-between gap-5 lg:gap-8">
        <RouterLink class="text-2xs font-medium text-subtle" to="/support">
          *Забыли пароль?
        </RouterLink>
        <BaseButton
          class="shrink-0"
          :disabled="!canSubmit"
          shape="pill"
          size="lg"
          type="submit"
          variant="dark"
        >
          {{ isSubmitting ? 'Входим…' : 'Продолжить' }}
        </BaseButton>
      </div>
    </form>
  </section>
</template>
