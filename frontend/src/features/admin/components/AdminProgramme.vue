<script setup>
import AdminUnitRow from '@/features/admin/components/AdminUnitRow.vue'

const props = defineProps({
  course: { type: Object, required: true },
  courseId: { type: String, required: true },
  isBusy: { type: Boolean, default: false },
})

const emit = defineEmits([
  'add-unit',
  'add-lesson',
  'edit-unit',
  'move-unit',
  'move-lesson',
  'remove-unit',
  'remove-lesson',
  'material-uploaded',
])
</script>

<template>
  <section class="p-4 lg:p-5">
    <div class="flex items-center justify-between gap-4 pb-4">
      <h2 class="text-lg font-bold text-ink">Модули</h2>
      <button
        class="text-sm font-semibold text-accent disabled:opacity-50"
        :disabled="props.isBusy"
        type="button"
        @click="emit('add-unit', 'module')"
      >
        + Модуль
      </button>
    </div>

    <div class="rounded-lg border border-subtle">
      <AdminUnitRow
        v-for="unit in props.course.modules"
        :key="unit.id"
        :course-id="props.courseId"
        :is-busy="props.isBusy"
        :unit="unit"
        @add-lesson="emit('add-lesson', unit)"
        @material-uploaded="emit('material-uploaded')"
        @move="emit('move-unit', unit, $event)"
        @move-lesson="(lesson, direction) => emit('move-lesson', lesson, direction)"
        @remove="emit('remove-unit', unit)"
        @remove-lesson="emit('remove-lesson', $event)"
        @rename="emit('edit-unit', unit)"
      />
      <p
        v-if="props.course.modules.length === 0"
        class="px-5 py-8 text-center text-sm font-medium text-subtle"
      >
        В курсе пока нет модулей
      </p>
    </div>

    <div class="flex items-center justify-between gap-4 pb-4 pt-8">
      <h2 class="text-lg font-bold text-ink">Работы курса</h2>
      <div class="flex gap-4">
        <button
          class="text-sm font-semibold text-accent disabled:opacity-50"
          :disabled="props.isBusy"
          type="button"
          @click="emit('add-unit', 'assignment')"
        >
          + Задание
        </button>
        <button
          class="text-sm font-semibold text-accent disabled:opacity-50"
          :disabled="props.isBusy"
          type="button"
          @click="emit('add-unit', 'test')"
        >
          + Тестирование
        </button>
      </div>
    </div>

    <div class="rounded-lg border border-subtle">
      <AdminUnitRow
        v-for="unit in props.course.activities"
        :key="unit.id"
        :course-id="props.courseId"
        :is-busy="props.isBusy"
        :unit="unit"
        @move="emit('move-unit', unit, $event)"
        @remove="emit('remove-unit', unit)"
        @rename="emit('edit-unit', unit)"
      />
      <p
        v-if="props.course.activities.length === 0"
        class="px-5 py-8 text-center text-sm font-medium text-subtle"
      >
        В курсе пока нет работ
      </p>
    </div>
  </section>
</template>
