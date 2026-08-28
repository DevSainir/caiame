export default [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/features/auth/views/LoginView.vue'),
    meta: { headerTitle: 'Войти в личный аккаунт', guestOnly: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/features/auth/views/RegisterView.vue'),
    meta: { headerTitle: 'Регистрация', guestOnly: true },
  },
]
