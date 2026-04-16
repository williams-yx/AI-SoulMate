import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import { routes } from './router/routes'
import { useAuthStore } from './stores/auth'
import { setOnUnauthorized } from './lib/api'
import './styles/community-overrides.css'
import { i18n } from './locales'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(i18n as any)

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局路由守卫：未登录禁止访问 requiresAuth 页面，并自动弹登录框
const auth = useAuthStore(pinia)

// API 401 时通过 Pinia store 正确清除 auth 状态
setOnUnauthorized(() => auth.logout())
auth.installSessionActivityListeners()
auth.hydrate()
if (auth.isAuthed) {
  auth._scheduleSessionTimers()
}
router.beforeEach((to) => {
  auth.hydrate()
  const need = Boolean(to.meta?.requiresAuth)
  if (!need) return true
  if (auth.isAuthed) return true
  return { path: '/', query: { login: '1', redirect: to.fullPath } }
})
router.afterEach(() => {
  auth.touchSessionActivity()
})
app.use(router)

app.mount('#app')

