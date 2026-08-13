import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', name: 'dashboard', component: () => import('../views/DashboardView.vue') },
    { path: '/log', name: 'log', component: () => import('../views/DataLogView.vue') },
    { path: '/map', name: 'map', component: () => import('../views/MapView.vue') },
    { path: '/find-places', name: 'find-places', component: () => import('../views/GuideView.vue') },
  ],
})

export default router
