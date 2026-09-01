<script setup>
import { reactive, ref } from 'vue'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseField from '@/core/components/BaseField.vue'
import BaseModal from '@/core/components/BaseModal.vue'

const props = defineProps({
  courses: { type: Array, default: () => [] },
  isBusy: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['submit', 'close'])

const INPUT =
  'rounded-lg border border-neutral-400 bg-page px-5 py-4 text-sm font-medium text-ink outline-none'

const form = reactive({ email: '', course_id: props.courses[0]?.id ?? '', reason: '' })
const emailError = ref('')

function submit() {
  emailError.value = form.email.includes('@') ? '' : 'Укажите почту, с которой студент вошёл'
  if (emailError.value) return
  emit('submit', {
    email: form.email.trim().toLowerCase(),
    course_id: form.course_id || null,
    reason: form.reason.trim(),
  })
}
</script>

<template>
  <BaseModal title="Выдать доступ" @close="emit('close')">
    <form class="flex flex-col gap-5" @submit.prevent="submit">
      <BaseField hint="Та самая, с которой студент зарегистрировался" label="Почта студента">
        <input v-model="form.email" :class="INPUT" type="email" />
        <span v-if="emailError" class="text-2xs font-medium text-danger-600">{{ emailError }}</span>
      </BaseField>

      <BaseField label="Курс">
        <select v-model="form.course_id" :class="INPUT">
          <option v-for="course in props.courses" :key="course.id" :value="course.id">
            {{ course.title }}
          </option>
          <option value="">Все курсы</option>
        </select>
      </BaseField>

      <BaseField hint="Останется в записи: по нему потом видно, за что открыли" label="Основание">
        <input v-model="form.reason" :class="INPUT" placeholder="Оплата в кассе" type="text" />
      </BaseField>

      <p v-if="props.error" class="text-xs font-medium text-danger-600">{{ props.error }}</p>

      <div class="flex items-center justify-end gap-3 pt-2">
        <button class="text-sm font-semibold text-subtle" type="button" @click="emit('close')">
          Отмена
        </button>
        <BaseButton :disabled="props.isBusy" size="sm" type="submit">Выдать</BaseButton>
      </div>
    </form>
  </BaseModal>
</template>
