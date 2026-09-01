<script setup>
import { reactive, ref } from 'vue'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseField from '@/core/components/BaseField.vue'
import BaseModal from '@/core/components/BaseModal.vue'

const props = defineProps({
  question: { type: Object, default: null },
  isBusy: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['submit', 'close'])

const INPUT =
  'rounded-lg border border-neutral-400 bg-page px-5 py-4 text-sm font-medium text-ink outline-none'

const form = reactive({
  question: props.question?.question ?? '',
  answer: props.question?.answer ?? '',
})
const localError = ref('')

function submit() {
  if (!form.question.trim() || !form.answer.trim()) {
    localError.value = 'Вопрос без ответа на странице курса выглядит как недоделка'
    return
  }
  localError.value = ''
  emit('submit', { question: form.question.trim(), answer: form.answer.trim() })
}
</script>

<template>
  <BaseModal
    :title="props.question ? 'Вопрос о курсе' : 'Новый вопрос о курсе'"
    @close="emit('close')"
  >
    <form class="flex flex-col gap-5" @submit.prevent="submit">
      <BaseField hint="Так, как его задал бы человек, выбирающий курс" label="Вопрос">
        <input v-model="form.question" :class="INPUT" type="text" />
      </BaseField>

      <BaseField label="Ответ">
        <textarea v-model="form.answer" :class="INPUT" rows="5"></textarea>
      </BaseField>

      <p v-if="localError || props.error" class="text-xs font-medium text-danger-600">
        {{ localError || props.error }}
      </p>

      <div class="flex items-center justify-end gap-3 pt-2">
        <button class="text-sm font-semibold text-subtle" type="button" @click="emit('close')">
          Отмена
        </button>
        <BaseButton :disabled="props.isBusy" size="sm" type="submit">Сохранить</BaseButton>
      </div>
    </form>
  </BaseModal>
</template>
