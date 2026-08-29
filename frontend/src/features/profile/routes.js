export default [
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/features/profile/views/ProfileView.vue'),
    meta: { headerTitle: 'Личный кабинет', requiresAuth: true },
  },
]
