<script setup>
import { reactive, ref } from 'vue'
import BaseButton from '@/core/components/BaseButton.vue'
import BaseField from '@/core/components/BaseField.vue'
import BaseModal from '@/core/components/BaseModal.vue'

const props = defineProps({
  course: { type: Object, default: null },
  specializations: { type: Array, default: () => [] },
  accreditations: { type: Array, default: () => [] },
  isBusy: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['submit', 'close'])

const INPUT =
  'rounded-lg border border-neutral-400 bg-page px-5 py-4 text-sm font-medium text-ink outline-none'

const form = reactive({
  title: props.course?.title ?? '',
  summary: props.course?.summary ?? '',
  description: props.course?.description ?? '',
  specialization_id: props.course?.specialization_id ?? props.specializations[0]?.id ?? '',
  accreditation_id: props.course?.accreditation_id ?? '',
  credit_hours: props.course?.credit_hours ?? 0,
  duration_hours: props.course?.duration_hours ?? 0,
  // Цена в сомах — в минорные единицы её переводит эта форма, чтобы дальше по всему пути
  // ходило целое число и нигде не появилось дробное.
  price: (props.course?.price_minor ?? 0) / 100,
})
const titleError = ref('')
const fieldError = ref('')

function submit() {
  titleError.value = form.title.trim() ? '' : 'Без названия курс не создать'
  fieldError.value = form.specialization_id ? '' : 'Выберите направление'
  if (titleError.value || fieldError.value) return
  emit('submit', {
    title: form.title.trim(),
    summary: form.summary.trim(),
    description: form.description.trim(),
    specialization_id: form.specialization_id,
    accreditation_id: form.accreditation_id || null,
    credit_hours: Number(form.credit_hours) || 0,
    duration_hours: Number(form.duration_hours) || 0,
    price_minor: Math.round(Number(form.price) * 100) || 0,
  })
}
</script>

<template>
  <BaseModal :title="props.course ? 'Курс' : 'Новый курс'" @close="emit('close')">
    <form class="flex flex-col gap-5" @submit.prevent="submit">
      <BaseField label="Название">
        <input v-model="form.title" :class="INPUT" type="text" />
        <span v-if="titleError" class="text-2xs font-medium text-danger-600">{{ titleError }}</span>
      </BaseField>

      <BaseField hint="Одна строка, которую видно на карточке курса" label="Краткое описание">
        <input v-model="form.summary" :class="INPUT" type="text" />
      </BaseField>

      <BaseField label="Описание">
        <textarea v-model="form.description" :class="INPUT" rows="4"></textarea>
      </BaseField>

      <div class="grid gap-4 lg:grid-cols-2">
        <BaseField label="Направление">
          <select v-model="form.specialization_id" :class="INPUT">
            <option v-for="item in props.specializations" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>
        </BaseField>

        <BaseField label="Вид удостоверения">
          <select v-model="form.accreditation_id" :class="INPUT">
            <option value="">Не указан</option>
            <option v-for="item in props.accreditations" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>
        </BaseField>
      </div>

      <div class="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <BaseField label="Часов по программе">
          <input v-model="form.credit_hours" :class="INPUT" min="0" type="number" />
        </BaseField>
        <BaseField label="Длительность, часов">
          <input v-model="form.duration_hours" :class="INPUT" min="0" type="number" />
        </BaseField>
        <BaseField label="Стоимость, сом">
          <input v-model="form.price" :class="INPUT" min="0" type="number" />
        </BaseField>
      </div>

      <p v-if="fieldError || props.error" class="text-xs font-medium text-danger-600">
        {{ fieldError || props.error }}
      </p>

      <div class="flex flex-wrap items-center justify-end gap-3 pt-2">
        <button class="text-sm font-semibold text-subtle" type="button" @click="emit('close')">
          Отмена
        </button>
        <BaseButton :disabled="props.isBusy" size="sm" type="submit">Сохранить</BaseButton>
      </div>
    </form>
  </BaseModal>
</template>
