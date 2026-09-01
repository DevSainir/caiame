<script setup>
import { computed, onMounted, ref } from 'vue'
import { describeError } from '@/core/api/messages'
import BaseButton from '@/core/components/BaseButton.vue'
import { useNotificationStore } from '@/core/notifications/store'
import AdminGrantForm from '@/features/admin/components/AdminGrantForm.vue'
import AdminShell from '@/features/admin/components/AdminShell.vue'
import { fetchAccess, fetchCourses, grantAccess, revokeAccess } from '@/features/admin/api'

const notifications = useNotificationStore()

const PAGE_SIZE = 20

const grants = ref([])
const courses = ref([])
const total = ref(0)
const isLoading = ref(true)
const isBusy = ref(false)
const loadError = ref('')
const formError = ref('')
const isFormOpen = ref(false)

const hasMore = computed(() => grants.value.length < total.value)

async function load({ append = false } = {}) {
  isLoading.value = !append
  loadError.value = ''
  try {
    const page = await fetchAccess({ limit: PAGE_SIZE, offset: append ? grants.value.length : 0 })
    grants.value = append ? [...grants.value, ...page.items] : page.items
    total.value = page.total
  } catch (failure) {
    loadError.value = describeError(failure, 'Не удалось загрузить список')
  } finally {
    isLoading.value = false
  }
}

async function grant(payload) {
  isBusy.value = true
  formError.value = ''
  try {
    await grantAccess(payload)
    isFormOpen.value = false
    await load()
    notifications.notify('Доступ выдан')
  } catch (failure) {
    formError.value = describeError(failure, 'Не удалось выдать доступ')
  } finally {
    isBusy.value = false
  }
}

async function revoke(grantRow) {
  if (!window.confirm(`Закрыть курс для ${grantRow.student_email}?`)) return
  isBusy.value = true
  try {
    await revokeAccess(grantRow.id)
    await load()
    notifications.notify('Доступ закрыт')
  } catch (failure) {
    notifications.notify(describeError(failure, 'Не удалось закрыть доступ'), 'error')
  } finally {
    isBusy.value = false
  }
}

onMounted(async () => {
  await load()
  try {
    courses.value = await fetchCourses()
  } catch {
    // Список курсов нужен только форме выдачи; без него таблица всё равно работает.
  }
})
</script>

<template>
  <AdminShell
    subtitle="Пока оплата не подключена, доступ открывает администратор"
    title="Студенты и доступ"
  >
    <template #actions>
      <BaseButton :disabled="isBusy" size="sm" @click="isFormOpen = true">Выдать доступ</BaseButton>
    </template>

    <p v-if="isLoading" class="py-24 text-center text-sm font-semibold text-subtle">
      Загружаем список…
    </p>

    <p v-else-if="loadError" class="py-24 text-center text-sm font-semibold text-subtle">
      {{ loadError }}
    </p>

    <p v-else-if="grants.length === 0" class="py-24 text-center text-sm font-medium text-subtle">
      Пока никому не открыт ни один курс
    </p>

    <template v-else>
      <ul class="flex flex-col gap-3 p-4 lg:hidden">
        <li v-for="row in grants" :key="row.id" class="rounded-lg border border-subtle p-4">
          <p class="text-sm font-bold text-ink">{{ row.student_name || row.student_email }}</p>
          <p class="pt-2 text-2xs font-medium text-subtle">
            {{ row.course_title || 'Все курсы' }} · {{ row.progress_percent }} %
          </p>
          <div class="flex items-center justify-between gap-4 pt-3">
            <span
              class="text-2xs font-semibold"
              :class="row.revoked_at ? 'text-subtle' : 'text-success-600'"
            >
              {{ row.revoked_at ? 'закрыт' : 'открыт' }}
            </span>
            <button
              v-if="!row.revoked_at"
              class="text-sm font-semibold text-danger-500"
              type="button"
              @click="revoke(row)"
            >
              Закрыть
            </button>
          </div>
        </li>
      </ul>

      <table class="hidden w-full text-left lg:table">
        <thead>
          <tr class="border-b border-subtle bg-subtle">
            <th class="px-5 py-3 text-2xs font-semibold uppercase text-subtle">Студент</th>
            <th class="px-4 py-3 text-2xs font-semibold uppercase text-subtle">Курс</th>
            <th class="px-4 py-3 text-2xs font-semibold uppercase text-subtle">Доступ</th>
            <th class="px-4 py-3 text-2xs font-semibold uppercase text-subtle">Прогресс</th>
            <th class="px-5 py-3"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in grants" :key="row.id" class="border-b border-subtle">
            <td class="px-5 py-5">
              <p class="text-sm font-bold text-ink">{{ row.student_name || '—' }}</p>
              <p class="pt-2 text-2xs font-medium text-subtle">{{ row.student_email }}</p>
            </td>
            <td class="px-4 py-5 text-sm font-medium text-muted">
              {{ row.course_title || 'Все курсы' }}
            </td>
            <td class="px-4 py-5">
              <span
                class="rounded-sm px-3 py-2 text-2xs font-semibold"
                :class="
                  row.revoked_at
                    ? 'border border-neutral-400 text-subtle'
                    : 'bg-success-500 text-inverse'
                "
              >
                {{ row.revoked_at ? 'закрыт' : 'открыт' }}
              </span>
              <p v-if="row.reason" class="pt-2 text-2xs font-medium text-subtle">
                {{ row.reason }}
              </p>
            </td>
            <td class="px-4 py-5">
              <div class="flex items-center gap-3">
                <span class="h-2 w-25 rounded-full bg-neutral-100">
                  <span
                    class="block h-full rounded-full bg-accent"
                    :style="{ width: `${row.progress_percent}%` }"
                  ></span>
                </span>
                <span class="text-xs font-medium text-muted">{{ row.progress_percent }} %</span>
              </div>
            </td>
            <td class="px-5 py-5 text-right">
              <button
                v-if="!row.revoked_at"
                class="text-sm font-semibold text-danger-500 disabled:opacity-50"
                :disabled="isBusy"
                type="button"
                @click="revoke(row)"
              >
                Закрыть
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="hasMore" class="flex justify-center p-5">
        <BaseButton size="sm" variant="dark" @click="load({ append: true })">
          Показать ещё
        </BaseButton>
      </div>
    </template>

    <p class="border-t border-subtle px-5 py-4 text-xs font-medium leading-relaxed text-subtle">
      Закрытый доступ не стирает прогресс: студент просто не сможет открыть лекции, а если доступ
      вернуть — продолжит с того же места.
    </p>

    <AdminGrantForm
      v-if="isFormOpen"
      :courses="courses"
      :error="formError"
      :is-busy="isBusy"
      @close="isFormOpen = false"
      @submit="grant"
    />
  </AdminShell>
</template>
