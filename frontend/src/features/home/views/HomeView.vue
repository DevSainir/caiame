<script setup>
import { onMounted, ref, watch } from 'vue'
import HomeAbout from '@/features/home/components/HomeAbout.vue'
import HomeCourses from '@/features/home/components/HomeCourses.vue'
import HomeHero from '@/features/home/components/HomeHero.vue'
import { fetchCatalogFilters, fetchCourses } from '@/features/catalog/api'

const PAGE_SIZE = 6

const courses = ref([])
const filters = ref({ specializations: [], accreditations: [], difficulties: [] })
const selected = ref({ specialization: '', difficulty: '', accreditation: '' })
const isLoading = ref(true)
const error = ref(null)

/** Drop empty controls, so the API is not asked to filter by an empty string. */
function activeParams() {
  return Object.fromEntries(
    Object.entries(selected.value).filter(([, value]) => value !== ''),
  )
}

function applyFilter(field, value) {
  selected.value = { ...selected.value, [field]: value }
}

async function loadCourses() {
  isLoading.value = true
  error.value = null
  try {
    const page = await fetchCourses({ ...activeParams(), size: PAGE_SIZE })
    courses.value = page.items
  } catch (failure) {
    error.value = failure
    courses.value = []
  } finally {
    isLoading.value = false
  }
}

async function loadFilters() {
  try {
    filters.value = await fetchCatalogFilters()
  } catch {
    // The filter bar degrades to placeholders; the catalogue itself still renders.
    filters.value = { specializations: [], accreditations: [], difficulties: [] }
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
      :is-loading="isLoading"
      :selected="selected"
      @change="applyFilter"
      @retry="loadCourses"
    />
    <HomeAbout />
  </div>
</template>
