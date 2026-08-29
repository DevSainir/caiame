import client from '@/core/api/client'

/** One page of published courses, filtered by the catalogue controls. */
export async function fetchCourses(params = {}) {
  const { data } = await client.get('/courses', { params })
  return data
}

/** Every value the filter bar offers: specializations, accreditations, audiences. */
export async function fetchCatalogFilters() {
  const { data } = await client.get('/catalog/filters')
  return data
}

/** One published course for its own page. 404 means there is no such course, not an empty one. */
export async function fetchCourse(slug) {
  const { data } = await client.get(`/courses/${slug}`)
  return data
}

/** Modules and works of one course, with the caller's own progress in them. */
export async function fetchSyllabus(slug) {
  const { data } = await client.get(`/courses/${slug}/syllabus`)
  return data
}

/** One page of reviews plus the rating summary of all of them. */
export async function fetchReviews(slug, params = {}) {
  const { data } = await client.get(`/courses/${slug}/reviews`, { params })
  return data
}

/** Every question shown in the discussion block. */
export async function fetchQuestions(slug) {
  const { data } = await client.get(`/courses/${slug}/questions`)
  return data
}
