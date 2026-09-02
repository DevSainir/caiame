<script setup>
import AdminLessonUploadButton from '@/features/admin/components/AdminLessonUploadButton.vue'
import { lessonKindLabel } from '@/features/learning/labels'

const props = defineProps({
  unit: { type: Object, required: true },
  isBusy: { type: Boolean, default: false },
  courseId: { type: String, default: '' },
})

const emit = defineEmits([
  'move',
  'rename',
  'remove',
  'add-lesson',
  'move-lesson',
  'remove-lesson',
  'material-uploaded',
])

const KIND_LABELS = { module: 'модуль', assignment: 'задание', test: 'тест' }
</script>

<template>
  <div class="border-b border-subtle last:border-b-0">
    <div class="flex flex-wrap items-center gap-3 px-4 py-4 lg:gap-4 lg:px-5">
      <span class="rounded-xs bg-neutral-100 px-2 py-1 text-2xs font-semibold text-muted">
        {{ KIND_LABELS[props.unit.kind] }}
      </span>

      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-bold text-ink">
          {{ props.unit.position }}. {{ props.unit.title }}
        </p>
        <p v-if="props.unit.summary" class="truncate pt-2 text-2xs font-medium text-subtle">
          {{ props.unit.summary }}
        </p>
      </div>

      <span v-if="props.unit.kind === 'module'" class="text-2xs font-medium text-subtle">
        {{ props.unit.lessons.length }} лекций
      </span>

      <!-- Перестановка кнопками, а не перетаскиванием: один шаг — это один обмен
           позициями в одной транзакции, и его видно по номеру. -->
      <div class="flex items-center gap-2">
        <button
          class="rounded-sm border border-subtle px-3 py-2 text-2xs font-semibold text-muted disabled:opacity-50"
          :disabled="props.isBusy"
          type="button"
          @click="emit('move', -1)"
        >
          ↑
        </button>
        <button
          class="rounded-sm border border-subtle px-3 py-2 text-2xs font-semibold text-muted disabled:opacity-50"
          :disabled="props.isBusy"
          type="button"
          @click="emit('move', 1)"
        >
          ↓
        </button>
        <RouterLink
          v-if="props.unit.kind === 'test'"
          class="text-sm font-semibold text-accent"
          :to="`/admin/courses/${props.courseId}/tests/${props.unit.id}`"
        >
          Вопросы
        </RouterLink>
        <button
          class="text-sm font-semibold text-accent disabled:opacity-50"
          :disabled="props.isBusy"
          type="button"
          @click="emit('rename')"
        >
          Переименовать
        </button>
        <button
          class="text-sm font-semibold text-danger-500 disabled:opacity-50"
          :disabled="props.isBusy"
          type="button"
          @click="emit('remove')"
        >
          Удалить
        </button>
      </div>
    </div>

    <div v-if="props.unit.kind === 'module'" class="bg-subtle">
      <div
        v-for="lesson in props.unit.lessons"
        :key="lesson.id"
        class="flex flex-wrap items-center gap-3 border-t border-subtle px-4 py-3 lg:gap-4 lg:pl-12 lg:pr-5"
      >
        <span class="rounded-xs bg-primary-50 px-2 py-1 text-2xs font-semibold text-accent">
          {{ lessonKindLabel(lesson.kind) }}
        </span>
        <!-- На телефоне название занимает строку целиком: рядом со значком вида, минутами
             и отметкой о материале оно ужимается до «1. …», и строка перестаёт говорить,
             о какой лекции она. -->
        <span
          class="order-first w-full truncate text-sm font-medium text-ink lg:order-none lg:w-auto lg:min-w-0 lg:flex-1"
        >
          {{ lesson.position }}. {{ lesson.title }}
        </span>
        <span class="text-2xs font-medium text-subtle">{{ lesson.duration_minutes }} мин</span>
        <span v-if="!lesson.is_required" class="text-2xs font-medium text-subtle">
          необязательная
        </span>
        <span
          class="text-2xs font-semibold"
          :class="lesson.has_material ? 'text-success-600' : 'text-danger-500'"
        >
          {{ lesson.has_material ? 'материал загружен' : 'без материала' }}
        </span>
        <div class="flex items-center gap-3">
          <AdminLessonUploadButton
            :course-id="props.courseId"
            :lesson="lesson"
            @uploaded="emit('material-uploaded')"
          />
          <button
            class="rounded-sm border border-subtle px-3 py-2 text-2xs font-semibold text-muted disabled:opacity-50"
            :disabled="props.isBusy"
            type="button"
            @click="emit('move-lesson', lesson, -1)"
          >
            ↑
          </button>
          <button
            class="rounded-sm border border-subtle px-3 py-2 text-2xs font-semibold text-muted disabled:opacity-50"
            :disabled="props.isBusy"
            type="button"
            @click="emit('move-lesson', lesson, 1)"
          >
            ↓
          </button>
          <RouterLink
            class="text-sm font-semibold text-accent"
            :to="`/admin/courses/${props.courseId}/lessons/${lesson.id}`"
          >
            Открыть
          </RouterLink>
          <button
            class="text-sm font-semibold text-danger-500 disabled:opacity-50"
            :disabled="props.isBusy"
            type="button"
            @click="emit('remove-lesson', lesson)"
          >
            Убрать
          </button>
        </div>
      </div>

      <button
        class="border-t border-subtle px-4 py-3 text-sm font-semibold text-accent disabled:opacity-50 lg:pl-12"
        :disabled="props.isBusy"
        type="button"
        @click="emit('add-lesson')"
      >
        + Лекция
      </button>
    </div>
  </div>
</template>
