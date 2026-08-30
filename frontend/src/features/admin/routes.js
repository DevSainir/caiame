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
    path: '/admin/courses/:id',
    name: 'admin-course',
    meta: { requiresAuth: true, requiresRole: 'admin', headerTitle: 'Программа курса' },
    component: () => import('@/features/admin/views/AdminCourseView.vue'),
  },
]
