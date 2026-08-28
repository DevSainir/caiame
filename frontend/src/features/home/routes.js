import HomeView from '@/features/home/views/HomeView.vue'

export default [
  {
    path: '/',
    name: 'home',
    // Imported eagerly, unlike every other view. This is where nearly everyone lands, and
    // a lazy chunk here costs a whole extra round-trip before the catalogue can even be
    // requested — on a link with 150 ms latency that is half a second of blank page.
    component: HomeView,
  },
]
