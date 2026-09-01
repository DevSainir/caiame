<script setup>
import { reactive, ref } from 'vue'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseField from '@/core/components/BaseField.vue'
import BaseModal from '@/core/components/BaseModal.vue'

const props = defineProps({
  question: { type: Object, default: null },
  // Отвеченный вопрос не правится, а заменяется новым — форма та же, смысл другой,
  // и человек должен видеть, что именно произойдёт.
  isReplacement: { type: Boolean, default: false },
  isBusy: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['submit', 'close'])

const INPUT =
  'rounded-lg border border-neutral-400 bg-page px-5 py-4 text-sm font-medium text-ink outline-none'

const form = reactive({
  text: props.question?.text ?? '',
  kind: props.question?.kind ?? 'single',
  points: props.question?.points ?? 1,
  options: props.question?.options?.map((option) => ({
    text: option.text,
    is_correct: option.is_correct,
  })) ?? [
    { text: '', is_correct: true },
    { text: '', is_correct: false },
  ],
})
const localError = ref('')

function addOption() {
  form.options.push({ text: '', is_correct: false })
}

function removeOption(index) {
  if (form.options.length > 2) form.options.splice(index, 1)
}

/** Один верный вариант, когда ответ один: иначе балл начисляется по правилу, которого нет. */
function pick(index) {
  if (form.kind === 'single') {
    form.options.forEach((option, position) => {
      option.is_correct = position === index
    })
    return
  }
  form.options[index].is_correct = !form.options[index].is_correct
}

function submit() {
  const options = form.options.filter((option) => option.text.trim() !== '')
  if (!form.text.trim()) {
    localError.value = 'Вопрос без формулировки задать нельзя'
    return
  }
  if (options.length < 2) {
    localError.value = 'Нужно хотя бы два варианта ответа'
    return
  }
  if (!options.some((option) => option.is_correct)) {
    localError.value = 'Отметьте верный вариант — иначе на вопрос нельзя ответить правильно'
    return
  }
  localError.value = ''
  emit('submit', {
    text: form.text.trim(),
    kind: form.kind,
    points: Number(form.points) || 1,
    options: options.map((option) => ({ text: option.text.trim(), is_correct: option.is_correct })),
  })
}
</script>

<template>
  <BaseModal
    :title="
      props.isReplacement ? 'Новый вопрос взамен' : props.question ? 'Вопрос' : 'Новый вопрос'
    "
    @close="emit('close')"
  >
    <form class="flex flex-col gap-5" @submit.prevent="submit">
      <p v-if="props.isReplacement" class="text-xs font-medium leading-relaxed text-subtle">
        На прежний вопрос уже отвечали, поэтому он не меняется, а заменяется новым. Ответы студентов
        и их баллы останутся такими, какими были.
      </p>

      <BaseField label="Вопрос">
        <textarea v-model="form.text" :class="INPUT" rows="3"></textarea>
      </BaseField>

      <div class="grid grid-cols-2 gap-4">
        <BaseField label="Сколько ответов верных">
          <select v-model="form.kind" :class="INPUT">
            <option value="single">Один</option>
            <option value="multiple">Несколько</option>
          </select>
        </BaseField>
        <BaseField label="Баллов за вопрос">
          <input v-model="form.points" :class="INPUT" max="100" min="1" type="number" />
        </BaseField>
      </div>

      <div class="flex flex-col gap-3">
        <p class="text-xs font-semibold text-muted">Варианты ответа</p>
        <div v-for="(option, index) in form.options" :key="index" class="flex items-center gap-3">
          <button
            :aria-label="option.is_correct ? 'Верный вариант' : 'Отметить верным'"
            class="h-5 w-5 shrink-0 rounded-xs border"
            :class="option.is_correct ? 'border-accent bg-accent' : 'border-neutral-400'"
            type="button"
            @click="pick(index)"
          ></button>
          <input v-model="option.text" :class="[INPUT, 'flex-1']" type="text" />
          <button
            class="shrink-0 text-sm font-semibold text-danger-500 disabled:opacity-40"
            :disabled="form.options.length <= 2"
            type="button"
            @click="removeOption(index)"
          >
            Убрать
          </button>
        </div>
        <button
          class="self-start text-sm font-semibold text-accent"
          type="button"
          @click="addOption"
        >
          + Вариант
        </button>
      </div>

      <p v-if="localError || props.error" class="text-xs font-medium text-danger-600">
        {{ localError || props.error }}
      </p>

      <div class="flex items-center justify-end gap-3 pt-2">
        <button class="text-sm font-semibold text-subtle" type="button" @click="emit('close')">
          Отмена
        </button>
        <BaseButton :disabled="props.isBusy" size="sm" type="submit">
          {{ props.isReplacement ? 'Заменить' : 'Сохранить' }}
        </BaseButton>
      </div>
    </form>
  </BaseModal>
</template>
