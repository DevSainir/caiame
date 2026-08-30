export default [
  {
    path: '/modules/:id',
    name: 'module',
    // План модуля открыт всем: это витрина курса. Материал внутри — уже нет.
    meta: { headerTitle: 'Страница модуля' },
    component: () => import('@/features/learning/views/ModuleView.vue'),
  },
  {
    path: '/lessons/:id',
    name: 'lesson',
    meta: { headerTitle: 'Лекция', requiresAuth: true },
    component: () => import('@/features/learning/views/LessonView.vue'),
  },
  {
    path: '/tests/:id',
    name: 'test',
    meta: { headerTitle: 'Тестирование', requiresAuth: true },
    component: () => import('@/features/learning/views/TestView.vue'),
  },
]
