export default [
  {
    path: '/admin',
    name: 'admin-courses',
    // Роль в meta — это удобство: она убирает мигание чужого экрана. Настоящая проверка
    // стоит на каждом роуте API и отвечает 403 независимо от того, что решил фронтенд.
    meta: { requiresAuth: true, requiresRole: 'admin', headerTitle: 'Администрирование' },
    component: () => import('@/features/admin/views/AdminCoursesView.vue'),
  },
  {
    path: '/admin/access',
    name: 'admin-access',
    meta: { requiresAuth: true, requiresRole: 'admin', headerTitle: 'Студенты и доступ' },
    component: () => import('@/features/admin/views/AdminAccessView.vue'),
  },
  {
    path: '/admin/courses/:id',
    name: 'admin-course',
    meta: { requiresAuth: true, requiresRole: 'admin', headerTitle: 'Программа курса' },
    component: () => import('@/features/admin/views/AdminCourseView.vue'),
  },
  {
    path: '/admin/courses/:courseId/tests/:unitId',
    name: 'admin-test',
    meta: { requiresAuth: true, requiresRole: 'admin', headerTitle: 'Вопросы тестирования' },
    component: () => import('@/features/admin/views/AdminTestView.vue'),
  },
  {
    path: '/admin/courses/:courseId/lessons/:lessonId',
    name: 'admin-lesson',
    meta: { requiresAuth: true, requiresRole: 'admin', headerTitle: 'Лекция' },
    component: () => import('@/features/admin/views/AdminLessonView.vue'),
  },
]
