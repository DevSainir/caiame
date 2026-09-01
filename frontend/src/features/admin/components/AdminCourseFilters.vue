<script setup>
defineProps({
  specializations: { type: Array, default: () => [] },
})
const filters = defineModel({ type: Object, required: true })

const CONTROL =
  'rounded-sm border border-subtle bg-page px-4 py-2 text-xs font-medium text-ink outline-none'
</script>

<template>
  <div class="flex flex-wrap gap-3 border-b border-subtle px-5 py-4">
    <select v-model="filters.status" :class="CONTROL">
      <option value="">Все статусы</option>
      <option value="draft">Черновики</option>
      <option value="published">Опубликованные</option>
      <option value="archived">В архиве</option>
    </select>

    <select v-model="filters.specializationId" :class="CONTROL">
      <option value="">Все направления</option>
      <option v-for="item in specializations" :key="item.id" :value="item.id">
        {{ item.name }}
      </option>
    </select>

    <input v-model="filters.query" :class="CONTROL" placeholder="Поиск по названию" type="search" />
  </div>
</template>
