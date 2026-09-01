<script setup>
import { computed, reactive, ref } from 'vue'
import { describeError } from '@/core/api/messages'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseInput from '@/core/components/BaseInput.vue'
import { useNotificationStore } from '@/core/notifications/store'
import { useAuthStore } from '@/core/session/store'

const auth = useAuthStore()
const notifications = useNotificationStore()

// Столько же, сколько при регистрации: одно правило на весь сайт, иначе о втором человек
// узнаёт в момент отказа.
const MIN_LENGTH = 8

const form = reactive({ current: '', next: '', repeat: '' })
const error = ref('')
const isSaving = ref(false)

const canSave = computed(
  () => form.current !== '' && form.next.length >= MIN_LENGTH && form.repeat !== '',
)

async function save() {
  error.value = ''
  if (form.next !== form.repeat) {
    error.value = 'Новый пароль и его повтор не совпадают'
    return
  }
  isSaving.value = true
  try {
    await auth.changePassword({ current_password: form.current, new_password: form.next })
    form.current = ''
    form.next = ''
    form.repeat = ''
    notifications.notify('Пароль изменён. Остальные устройства вышли из аккаунта')
  } catch (failure) {
    error.value =
      failure?.status === 401
        ? 'Текущий пароль введён неверно'
        : describeError(failure, 'Не получилось изменить пароль')
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <form class="flex w-full max-w-card flex-col gap-5" novalidate @submit.prevent="save">
    <h2 class="text-xl font-semibold text-ink lg:text-2xl">Пароль</h2>
    <p class="text-sm font-medium text-subtle">
      Текущий пароль нужен, чтобы никто не сменил его с чужого открытого компьютера. После смены
      остальные устройства выйдут из аккаунта — этот останется.
    </p>

    <BaseInput
      v-model="form.current"
      autocomplete="current-password"
      placeholder="Текущий пароль*"
      type="password"
    />
    <BaseInput
      v-model="form.next"
      autocomplete="new-password"
      placeholder="Новый пароль*"
      type="password"
    />
    <BaseInput
      v-model="form.repeat"
      autocomplete="new-password"
      :error="error"
      placeholder="Повторите новый пароль*"
      type="password"
    />

    <BaseButton
      class="self-start"
      :disabled="!canSave || isSaving"
      shape="pill"
      size="lg"
      type="submit"
      variant="dark"
    >
      {{ isSaving ? 'Сохраняем…' : 'Изменить пароль' }}
    </BaseButton>
  </form>
</template>
