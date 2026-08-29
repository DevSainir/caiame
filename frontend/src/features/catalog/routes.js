export default [
  {
    path: '/courses/:slug',
    name: 'course',
    // Lazy: the course page is the second screen of the visit, not the first one, and its
    // syllabus and reviews have no business in the bundle the main page waits for.
    component: () => import('@/features/catalog/views/CourseView.vue'),
  },
]
