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
    path: '/admin/submissions',
    name: 'admin-submissions',
    // Проверять работы может и преподаватель, не только администратор.
    meta: { requiresAuth: true, requiresRole: 'staff', headerTitle: 'Проверка работ' },
    component: () => import('@/features/admin/views/AdminSubmissionsView.vue'),
  },
  {
    path: '/admin/submissions/:id',
    name: 'admin-submission',
    meta: { requiresAuth: true, requiresRole: 'staff', headerTitle: 'Работа студента' },
    component: () => import('@/features/admin/views/AdminSubmissionView.vue'),
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
