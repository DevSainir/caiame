import client from '@/core/api/client'

/** One page of published courses, filtered by the catalogue controls. */
export async function fetchCourses(params = {}) {
  const { data } = await client.get('/courses', { params })
  return data
}

/** Every value the filter bar offers: specializations, accreditations, difficulty levels. */
export async function fetchCatalogFilters() {
  const { data } = await client.get('/catalog/filters')
  return data
}
