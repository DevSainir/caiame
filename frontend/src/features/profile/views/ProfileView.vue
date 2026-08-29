<script setup>
import { computed, ref, watch } from 'vue'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseContainer from '@/core/components/BaseContainer.vue'
import BaseInput from '@/core/components/BaseInput.vue'
import { updateProfile } from '@/features/profile/api'
import { initialsFor } from '@/core/initials'
import { useAuthStore } from '@/core/session/store'
import { useNotificationStore } from '@/core/notifications/store'

const auth = useAuthStore()
const notifications = useNotificationStore()

const fullName = ref('')
const error = ref('')
const isSaving = ref(false)

watch(
  () => auth.user,
  (user) => {
    fullName.value = user?.full_name ?? ''
  },
  { immediate: true },
)

const initials = computed(() =>
  initialsFor({ fullName: fullName.value, email: auth.user?.email ?? '' }),
)
const canSave = computed(
  () => fullName.value.trim() !== '' && fullName.value.trim() !== auth.user?.full_name,
)

async function save() {
  error.value = ''
  if (!canSave.value) return
  isSaving.value = true
  try {
    auth.applyUser(await updateProfile({ full_name: fullName.value.trim() }))
    notifications.notify('Данные обновлены')
  } catch {
    error.value = 'Не получилось сохранить. Попробуйте ещё раз'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <section class="py-10 lg:py-25">
    <BaseContainer>
      <div class="flex flex-col gap-8 lg:flex-row lg:gap-25">
        <div class="flex flex-col items-center gap-5 lg:items-start">
          <div
            class="flex h-25 w-25 items-center justify-center rounded-full bg-subtle text-4xl font-semibold text-subtle"
          >
            {{ initials }}
          </div>
          <p class="text-xl font-bold text-ink lg:text-2xl">
            {{ auth.user?.full_name || 'Без имени' }}
          </p>
        </div>

        <form class="flex w-full max-w-card flex-col gap-5" novalidate @submit.prevent="save">
          <h1 class="text-2xl font-semibold text-ink lg:text-3xl">Мой профиль</h1>
          <p class="text-sm font-medium text-subtle lg:text-base">
            Управление вашим профилем. Имя видно в сертификатах и в переписке с преподавателями.
          </p>

          <div class="flex flex-col gap-2">
            <p class="text-xs font-semibold text-subtle">Почта</p>
            <p class="text-base font-medium text-ink">{{ auth.user?.email }}</p>
          </div>

          <BaseInput
            v-model="fullName"
            autocomplete="name"
            :error="error"
            placeholder="Имя и фамилия"
          />

          <BaseButton
            class="self-start"
            :disabled="!canSave || isSaving"
            shape="pill"
            size="lg"
            type="submit"
            variant="dark"
          >
            {{ isSaving ? 'Сохраняем…' : 'Обновить данные' }}
          </BaseButton>
        </form>
      </div>
    </BaseContainer>
  </section>
</template>
