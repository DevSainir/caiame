<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import HomeAbout from '@/features/home/components/HomeAbout.vue'
import HomeCourses from '@/features/home/components/HomeCourses.vue'
import HomeHero from '@/features/home/components/HomeHero.vue'
import { fetchCatalogFilters, fetchCourses } from '@/features/catalog/api'

const PAGE_SIZE = 6

const courses = ref([])
const total = ref(0)
const page = ref(1)
const filters = ref({ specializations: [], accreditations: [], audiences: [] })
const selected = ref({ specialization: '', audience: '', accreditation: '' })
const isLoading = ref(true)
const isLoadingMore = ref(false)
const error = ref(null)

const hasMore = computed(() => courses.value.length < total.value)

/** Drop empty controls, so the API is not asked to filter by an empty string. */
function activeParams() {
  return Object.fromEntries(Object.entries(selected.value).filter(([, value]) => value !== ''))
}

function applyFilter(field, value) {
  selected.value = { ...selected.value, [field]: value }
}

async function loadCourses() {
  isLoading.value = true
  error.value = null
  page.value = 1
  try {
    const result = await fetchCourses({ ...activeParams(), page: 1, size: PAGE_SIZE })
    courses.value = result.items
    total.value = result.total
  } catch (failure) {
    error.value = failure
    courses.value = []
    total.value = 0
  } finally {
    isLoading.value = false
  }
}

/**
 * Догрузить следующую страницу каталога.
 *
 * Страницы складываются: «Посмотреть больше курсов» стоит под сеткой, и подменять уже
 * прочитанные карточки следующими значило бы отправлять читателя искать их заново.
 */
async function loadMore() {
  if (isLoadingMore.value) return
  isLoadingMore.value = true
  try {
    const result = await fetchCourses({
      ...activeParams(),
      page: page.value + 1,
      size: PAGE_SIZE,
    })
    courses.value = [...courses.value, ...result.items]
    total.value = result.total
    page.value += 1
  } catch {
    // Сетка уже показана: кнопка остаётся на месте, чтобы попробовать ещё раз.
  } finally {
    isLoadingMore.value = false
  }
}

async function loadFilters() {
  try {
    filters.value = await fetchCatalogFilters()
  } catch {
    // The filter bar degrades to placeholders; the catalogue itself still renders.
    filters.value = { specializations: [], accreditations: [], audiences: [] }
  }
}

onMounted(() => {
  loadFilters()
  loadCourses()
})

watch(selected, loadCourses, { deep: true })
</script>

<template>
  <div>
    <HomeHero />
    <HomeCourses
      :courses="courses"
      :error="error"
      :filters="filters"
      :has-more="hasMore"
      :is-loading="isLoading"
      :is-loading-more="isLoadingMore"
      :selected="selected"
      @change="applyFilter"
      @more="loadMore"
      @retry="loadCourses"
    />
    <HomeAbout />
  </div>
</template>
