<script setup>
import { computed, onMounted, ref } from 'vue'
import { describeError } from '@/core/api/messages'
import BaseButton from '@/core/components/BaseButton.vue'
import { formatDate, formatWorks } from '@/core/format'
import AdminShell from '@/features/admin/components/AdminShell.vue'
import { fetchSubmissions } from '@/features/admin/api'

const PAGE_SIZE = 20

const items = ref([])
const total = ref(0)
const isLoading = ref(true)
const loadError = ref('')

const hasMore = computed(() => items.value.length < total.value)
const subtitle = computed(() =>
  total.value
    ? `${formatWorks(total.value)} ${total.value === 1 ? 'ждёт' : 'ждут'} проверки`
    : 'Непроверенных работ нет',
)

async function load({ append = false } = {}) {
  isLoading.value = !append
  loadError.value = ''
  try {
    const page = await fetchSubmissions({
      limit: PAGE_SIZE,
      offset: append ? items.value.length : 0,
    })
    items.value = append ? [...items.value, ...page.items] : page.items
    total.value = page.total
  } catch (failure) {
    loadError.value = describeError(failure, 'Не удалось загрузить очередь')
  } finally {
    isLoading.value = false
  }
}

onMounted(load)
</script>

<template>
  <AdminShell :subtitle="subtitle" title="Проверка работ">
    <p v-if="isLoading" class="py-24 text-center text-sm font-semibold text-subtle">
      Загружаем очередь…
    </p>

    <p v-else-if="loadError" class="py-24 text-center text-sm font-semibold text-subtle">
      {{ loadError }}
    </p>

    <p v-else-if="items.length === 0" class="py-24 text-center text-sm font-medium text-subtle">
      Все работы проверены
    </p>

    <ul v-else class="flex flex-col">
      <li v-for="row in items" :key="row.id" class="border-b border-subtle">
        <RouterLink
          class="flex flex-wrap items-center justify-between gap-4 px-5 py-5"
          :to="`/admin/submissions/${row.id}`"
        >
          <div class="min-w-0">
            <p class="text-sm font-bold text-ink">{{ row.student_name || row.student_email }}</p>
            <p class="pt-2 text-2xs font-medium text-subtle">
              {{ row.assignment_title }} · попытка {{ row.attempt_no }}
              <template v-if="row.submitted_at">
                · сдано {{ formatDate(row.submitted_at) }}
              </template>
            </p>
          </div>
          <div class="flex items-center gap-4">
            <span v-if="row.is_late" class="text-2xs font-semibold text-danger-500">
              после срока
            </span>
            <span class="text-sm font-semibold text-accent">Проверить</span>
          </div>
        </RouterLink>
      </li>
    </ul>

    <div v-if="hasMore" class="flex justify-center p-5">
      <BaseButton size="sm" variant="dark" @click="load({ append: true })">Показать ещё</BaseButton>
    </div>

    <p class="border-t border-subtle px-5 py-4 text-xs font-medium leading-relaxed text-subtle">
      Первой стоит работа, которая ждёт дольше всех. Возврат на доработку не стирает присланное:
      студент увидит рецензию и пришлёт следующую попытку.
    </p>
  </AdminShell>
</template>
