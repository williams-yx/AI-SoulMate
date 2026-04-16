<template>
  <div class="min-h-screen flex flex-col overflow-x-hidden">
    <header class="sticky top-0 z-50 glass-panel border-b border-white/5 bg-[#0f172a]/80">
      <div class="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 h-16 grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 xl:gap-3 min-w-0 overflow-visible">
        <!-- Logo：改成旧版的小机器人 + 渐变文字 -->
        <RouterLink to="/" class="flex items-center gap-2 cursor-pointer group shrink-0">
          <div
            class="w-8 h-8 flex items-center justify-center bg-indigo-500/20 rounded-lg group-hover:bg-indigo-500/40 transition border border-indigo-500/40 shrink-0"
          >
            <i data-lucide="bot" class="w-5 h-5 text-indigo-400"></i>
          </div>
          <span class="font-bold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400 whitespace-nowrap hidden sm:block shrink-0">
            AI SoulMate
          </span>
          <span class="ml-1 sm:ml-2 px-2 py-0.5 mt-0.5 rounded-full border border-slate-700 bg-slate-900/50 text-white text-[10px] font-bold tracking-wide shrink-0">Beta</span>
          <span class="text-[10px] text-slate-500 font-mono mt-1 hidden sm:block shrink-0">v0.8.0</span>
        </RouterLink>

        <!-- 移动端汉堡菜单（lg 以上隐藏） -->
        <button class="lg:hidden p-2 rounded-md text-slate-200 hover:bg-white/5 mr-2" @click="mobileNavOpen = !mobileNavOpen" :aria-expanded="mobileNavOpen" aria-label="Toggle menu">
          <i :data-lucide="mobileNavOpen ? 'x' : 'menu'" class="w-5 h-5"></i>
        </button>

        <!-- 主导航：带图标，更靠近旧版 -->
        <nav class="hidden lg:flex items-center justify-center gap-4 xl:gap-6 min-w-0 overflow-x-auto">
          <RouterLink
            to="/"
            class="app-nav-link"
          >
            <span class="inline-block shrink-0"><i data-lucide="home" class="w-4 h-4"></i></span>
            <span class="min-w-0 truncate">{{ t('app.nav.home') }}</span>
          </RouterLink>
          <RouterLink
            to="/community"
            class="app-nav-link"
          >
            <span class="inline-block shrink-0"><i data-lucide="users" class="w-4 h-4"></i></span>
            <span class="min-w-0 truncate">{{ t('app.nav.community') }}</span>
          </RouterLink>
          <!--
          <RouterLink
            to="/courses"
            class="px-2 xl:px-4 py-2 text-base xl:text-lg font-semibold text-slate-300 hover:text-white transition flex items-center gap-1.5 whitespace-nowrap shrink-0"
          >
            <span class="inline-block shrink-0"><i data-lucide="book-open" class="w-4 h-4"></i></span> <span class="hidden xl:inline">课程中心</span><span class="xl:hidden">课程</span>
          </RouterLink>
          <RouterLink
            to="/workflow"
            class="px-2 xl:px-4 py-2 text-base xl:text-lg font-semibold text-slate-300 hover:text-white transition flex items-center gap-1.5 whitespace-nowrap shrink-0"
          >
            <span class="inline-block shrink-0"><i data-lucide="workflow" class="w-4 h-4"></i></span> <span class="hidden xl:inline">工作流搭建</span><span class="xl:hidden">工作流</span>
          </RouterLink>
          -->
          <RouterLink
            to="/market"
            class="app-nav-link"
          >
            <span class="inline-block shrink-0"><i data-lucide="store" class="w-4 h-4"></i></span>
            <span class="min-w-0 truncate">
              <span class="hidden xl:inline">{{ t('app.nav.market') }}</span>
              <span class="xl:hidden">{{ t('app.nav.marketShort') }}</span>
            </span>
          </RouterLink>
          <RouterLink
            to="/orders"
            class="app-nav-link"
          >
            <span class="inline-block shrink-0"><i data-lucide="receipt" class="w-4 h-4"></i></span>
            <span class="min-w-0 truncate">{{ t('app.nav.orders') }}</span>
          </RouterLink>
        </nav>

        <div class="flex items-center justify-end gap-2 xl:gap-3 shrink-0 header-right">
          <!-- 造梦按钮 -->
          <RouterLink
            to="/studio"
            class="hidden md:flex bg-indigo-600 hover:bg-indigo-500 text-white px-4 xl:px-5 py-2 rounded-full text-base xl:text-lg font-bold shadow-lg shadow-indigo-500/20 transition-all active:scale-95 items-center gap-2 shrink-0"
          >
            <span class="inline-block shrink-0"><i data-lucide="wand-2" class="w-4 h-4"></i></span> {{ t('app.nav.studio') }}
          </RouterLink>

          <!-- 购物车 -->
          <RouterLink
            to="/checkout"
            class="relative p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-lg text-base xl:text-lg flex items-center gap-1.5 shrink-0"
            :title="t('app.nav.cart')"
          >
            <span class="inline-block shrink-0"><i data-lucide="shopping-cart" class="w-5 h-5"></i></span>
            <span class="hidden xl:inline whitespace-nowrap text-base xl:text-lg">{{ t('app.nav.cart') }}</span>
            <span
              v-if="cart.count"
              class="absolute -top-1 -right-1 min-w-5 h-5 px-1 rounded-full bg-emerald-500 text-[10px] font-bold text-white flex items-center justify-center shrink-0"
            >{{ cart.count }}</span>
          </RouterLink>

          <div class="h-6 w-[1px] bg-slate-700 mx-1 shrink-0"></div>

          <button
            v-if="!auth.isAuthed"
            class="px-4 py-2 rounded-full bg-slate-800 hover:bg-slate-700 text-sm text-slate-200 border border-slate-600 flex items-center gap-2 shrink-0 whitespace-nowrap"
            @click="authModalOpen = true"
          >
            <span class="inline-block shrink-0"><i data-lucide="log-in" class="w-4 h-4"></i></span>
            {{ t('app.user.loginRegister') }}
          </button>

          <div v-else ref="userMenuEl" class="relative">
            <!--
            <button
              class="w-10 h-10 rounded-full bg-indigo-600 hover:bg-indigo-500 flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/20 transition"
              @click="menuOpen = !menuOpen"
            >
              {{ avatarText }}
            </button>
            -->
            <button
              type="button"
              class="w-8 h-8 p-0 rounded-full border border-slate-600 bg-slate-900/70 text-slate-100 hover:bg-slate-800 transition flex items-center justify-center"
              @click="menuOpen = !menuOpen"
              :aria-expanded="menuOpen"
              :title="t('app.user.menu')"
            >
              <!-- 勿对 PNG 使用 brightness-0 invert：filter 会破坏透明通道，整格会变成白块 -->
              <span
                class="inline-block h-5 w-5 shrink-0 bg-slate-200 opacity-95 pointer-events-none"
                style="
                  mask-image: url('/images/user-menu-icon.png');
                  mask-mode: alpha;
                  mask-size: contain;
                  mask-position: center;
                  mask-repeat: no-repeat;
                  -webkit-mask-image: url('/images/user-menu-icon.png');
                  -webkit-mask-size: contain;
                  -webkit-mask-position: center;
                  -webkit-mask-repeat: no-repeat;
                "
                role="presentation"
              />
              <span class="sr-only">{{ t('app.user.menu') }}</span>
            </button>
            <div
              v-if="menuOpen"
              class="absolute right-0 top-10 w-48 glass-dropdown rounded-xl shadow-2xl border border-slate-700 py-2 z-50"
            >
              <RouterLink
                class="block px-4 py-2 text-sm text-slate-300 hover:bg-indigo-600 hover:text-white transition"
                to="/profile"
                @click="menuOpen = false"
              >
                {{ t('app.user.profile') }}
              </RouterLink>
              <button class="w-full text-left px-4 py-2 text-sm text-red-300 hover:bg-slate-800 transition" @click="logout">
                {{ t('app.user.logout') }}
              </button>
            </div>
          </div>

          <div class="relative" ref="localeMenuRef">
            <button
              class="w-8 h-8 p-0 rounded-full border border-slate-600 bg-slate-900/70 text-slate-100 hover:bg-slate-800 transition flex items-center justify-center"
              @click="localeMenuOpen = !localeMenuOpen"
              :aria-expanded="localeMenuOpen"
              :title="locale === 'zh-CN' ? t('app.locale.switchToEnglish') : t('app.locale.switchToChinese')"
            >
                <span class="inline-block shrink-0"><i data-lucide="globe" class="w-5 h-5"></i></span>
                <!-- 视觉上只保留地球图标，次要文字对屏幕阅读器仍可见 -->
                <span class="sr-only">{{ locale === 'zh-CN' ? t('app.locale.switchToChinese') : t('app.locale.switchToEnglish') }}</span>
            </button>

            <div v-if="localeMenuOpen" class="absolute right-0 mt-2 w-40 glass-dropdown rounded-md shadow-lg z-50 overflow-hidden pointer-events-auto">
              <button class="w-full text-left px-3 py-2 hover:bg-slate-800 flex items-center justify-between" @click="setLocale('zh-CN')">
                <span>{{ t('app.locale.switchToChinese') }}</span>
                <span v-if="locale === 'zh-CN'" class="text-emerald-400 font-bold">✓</span>
              </button>
              <button class="w-full text-left px-3 py-2 hover:bg-slate-800 flex items-center justify-between" @click="setLocale('en-US')">
                <span>{{ t('app.locale.switchToEnglish') }}</span>
                <span v-if="locale === 'en-US'" class="text-emerald-400 font-bold">✓</span>
              </button>
            </div>
          </div>
        </div>
      </div>
      <!-- 移动端折叠菜单弹窗（在 header 内，sticky 下方） -->
      <div v-if="mobileNavOpen" ref="mobileNavRef" class="lg:hidden absolute left-0 right-0 top-full z-50 bg-[#0f172a]/95 glass-dropdown border-t border-slate-700 p-4">
        <nav class="flex flex-col gap-3">
          <RouterLink to="/" class="px-3 py-2 rounded-md text-slate-200 hover:bg-white/5" @click="mobileNavOpen = false">{{ t('app.nav.home') }}</RouterLink>
          <RouterLink to="/community" class="px-3 py-2 rounded-md text-slate-200 hover:bg-white/5" @click="mobileNavOpen = false">{{ t('app.nav.community') }}</RouterLink>
          <RouterLink to="/market" class="px-3 py-2 rounded-md text-slate-200 hover:bg-white/5" @click="mobileNavOpen = false">{{ t('app.nav.market') }}</RouterLink>
          <RouterLink to="/orders" class="px-3 py-2 rounded-md text-slate-200 hover:bg-white/5" @click="mobileNavOpen = false">{{ t('app.nav.orders') }}</RouterLink>
          <RouterLink to="/studio" class="px-3 py-2 rounded-md text-slate-200 hover:bg-white/5" @click="mobileNavOpen = false">{{ t('app.nav.studio') }}</RouterLink>
        </nav>
      </div>
    </header>

    <main class="flex-1 max-w-screen-2xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
      <RouterView />
    </main>

    <!-- GitHub 回调后的提示（成功 / 失败） -->
    <div
      v-if="loginSuccessMessage || loginErrorMessage"
      class="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] px-6 py-3 rounded-xl text-white text-sm font-medium shadow-lg flex items-center gap-2"
      :class="loginErrorMessage ? 'bg-red-600/95' : 'bg-emerald-600/95'"
    >
      <span :key="loginErrorMessage ? 'err' : 'ok'">
        <i :data-lucide="loginErrorMessage ? 'alert-circle' : 'check-circle'" class="w-5 h-5"></i>
      </span>
      {{ loginErrorMessage || loginSuccessMessage }}
    </div>

    <div
      v-if="studioNoticeMessage"
      class="fixed right-6 bottom-6 z-[110] max-w-sm px-5 py-3 rounded-xl text-white text-sm font-medium shadow-2xl flex items-start gap-2"
      :class="studioNoticeType === 'error' ? 'bg-red-600/95' : 'bg-emerald-600/95'"
    >
      <span :key="studioNoticeType" class="shrink-0 mt-0.5">
        <i :data-lucide="studioNoticeType === 'error' ? 'alert-circle' : 'check-circle'" class="w-5 h-5"></i>
      </span>
      <span class="leading-6">{{ formatMsg(studioNoticeMessage) }}</span>
    </div>

    <AuthModal :open="authModalOpen" @close="onAuthModalClose" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import AuthModal from './components/AuthModal.vue'
import { api } from './lib/api'
import {
  clearGithubOAuthState,
  readGithubOAuthState,
  resolveGithubOAuthRedirectUriForTokenExchange,
} from './lib/githubOAuth'
import { useAuthStore } from './stores/auth'
import { useCartStore } from './stores/cart'
import { toggleAppLocale, setAppLocale } from './locales'

declare const lucide: any

const { t, locale } = useI18n()

const auth = useAuthStore()
const cart = useCartStore()
const authModalOpen = ref(false)
const menuOpen = ref(false)
const userMenuEl = ref<HTMLElement | null>(null)
let userMenuOutsideClick: ((e: MouseEvent) => void) | null = null

function detachUserMenuOutsideClick() {
  if (userMenuOutsideClick) {
    document.removeEventListener('click', userMenuOutsideClick, true)
    userMenuOutsideClick = null
  }
}
const localeMenuOpen = ref(false)
const localeMenuRef = ref<HTMLElement | null>(null)
const mobileNavOpen = ref(false)
const mobileNavRef = ref<HTMLElement | null>(null)
const loginSuccessMessage = ref('')
const loginErrorMessage = ref('')
const studioNoticeMessage = ref('')
const studioNoticeType = ref<'ok' | 'error'>('ok')
const route = useRoute()
const router = useRouter()
let studioNoticeDismissTimer: number | null = null
let studioNoticePollTimer: number | null = null
let studioNoticeStartedAt = 0
const handledStudioNoticeJobIds = new Set<string>()

/** 从当前 URL 获取 GitHub 回调的 code（兼容 route.query 与 window.location.search） */
function getGitHubCodeFromUrl(): string | null {
  const fromQuery = route.query.code
  if (fromQuery && typeof fromQuery === 'string') return fromQuery
  const params = new URLSearchParams(window.location.search)
  return params.get('code')
}

/** 是否为「绑定 GitHub」回调（必须与登录回调区分：绑定只调 bind-github，保持当前登录用户） */
function isBindGithubCallback(): boolean {
  if (route.query.bind === 'github') return true
  return new URLSearchParams(window.location.search).get('bind') === 'github'
}
function renderIcons() {
  if (typeof lucide !== 'undefined' && lucide?.createIcons) {
    lucide.createIcons()
  }
}

function toggleLocale() {
  toggleAppLocale()
}

function setLocale(loc: 'zh-CN' | 'en-US') {
  setAppLocale(loc)
  localeMenuOpen.value = false
}

function showStudioNotice(message: string, type: 'ok' | 'error') {
  studioNoticeType.value = type
  studioNoticeMessage.value = message
  if (studioNoticeDismissTimer !== null) {
    window.clearTimeout(studioNoticeDismissTimer)
  }
  studioNoticeDismissTimer = window.setTimeout(() => {
    studioNoticeMessage.value = ''
    studioNoticeDismissTimer = null
  }, type === 'ok' ? 6000 : 7000)
  setTimeout(() => renderIcons(), 30)
}

async function pollStudioJobNotifications() {
  if (!auth.isAuthed) return
  try {
    const res = await api.studio.getJobNotifications(10)
    const items = res?.items || []
    for (const item of items) {
      const eventTimeText = item.finished_at || item.created_at || ''
      const eventTime = eventTimeText ? new Date(eventTimeText).getTime() : Number.NaN
      const shouldToast = !studioNoticeStartedAt
        || Number.isNaN(eventTime)
        || eventTime >= (studioNoticeStartedAt - 2000)
      if (!handledStudioNoticeJobIds.has(item.job_id) && shouldToast) {
        if (item.status === 'COMPLETED') {
          showStudioNotice(item.message || 'app.notifications.studioCompleted', 'ok')
        } else if (item.status === 'CANCELLED') {
          showStudioNotice(item.message || 'app.notifications.studioCancelled', 'error')
        } else {
          showStudioNotice(item.message || 'app.notifications.studioFailed', 'error')
        }
      }
      handledStudioNoticeJobIds.add(item.job_id)
      await api.studio.ackJobNotification(item.job_id)
    }
  } catch {
    // ignore
  }
}

function startStudioNoticePolling() {
  if (studioNoticePollTimer !== null) return
  studioNoticeStartedAt = Date.now()
  studioNoticePollTimer = window.setInterval(() => {
    void pollStudioJobNotifications()
  }, 15000)
}

function stopStudioNoticePolling() {
  if (studioNoticePollTimer !== null) {
    window.clearInterval(studioNoticePollTimer)
    studioNoticePollTimer = null
  }
  studioNoticeStartedAt = 0
}

function setupIconRetry() {
  // 解决首屏脚本加载顺序问题：lucide 可能比 Vue 晚加载，这里多次重试
  let tries = 0
  const timer = setInterval(() => {
    tries += 1
    if (typeof lucide !== 'undefined' && lucide?.createIcons) {
      lucide.createIcons()
      clearInterval(timer)
    }
    if (tries > 10) {
      clearInterval(timer)
    }
  }, 150)
}

onMounted(async () => {
  auth.hydrate()
  cart.hydrate()
  if (auth.isAuthed) {
    startStudioNoticePolling()
    void pollStudioJobNotifications()
  }
  const onFocus = () => { void pollStudioJobNotifications() }
  const onVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      void pollStudioJobNotifications()
    }
  }
  window.addEventListener('focus', onFocus)
  document.addEventListener('visibilitychange', onVisibilityChange)
  setupIconRetry()
  renderIcons()
  const onBindMessage = (e: MessageEvent) => {
    if (e.origin !== window.location.origin || e.data?.type !== 'github-bound') return
    window.dispatchEvent(new CustomEvent('github-bound'))
  }
  window.addEventListener('message', onBindMessage)

  const onGlobalPointer = (ev: PointerEvent) => {
    // close locale menu when clicking outside
    if (localeMenuOpen.value) {
      const root = localeMenuRef.value as HTMLElement | null
      if (root && ev.target instanceof Node && !root.contains(ev.target as Node)) {
        localeMenuOpen.value = false
      }
    }

    // close mobile nav when clicking outside
    if (mobileNavOpen.value) {
      const mroot = mobileNavRef.value as HTMLElement | null
      if (mroot && ev.target instanceof Node && !mroot.contains(ev.target as Node)) {
        mobileNavOpen.value = false
      }
    }
  }

  const onGlobalKey = (ev: KeyboardEvent) => {
    if (ev.key === 'Escape') {
      localeMenuOpen.value = false
    }
  }

  window.addEventListener('pointerdown', onGlobalPointer)
  window.addEventListener('keydown', onGlobalKey)

  onUnmounted(() => {
    window.removeEventListener('message', onBindMessage)
    window.removeEventListener('focus', onFocus)
    document.removeEventListener('visibilitychange', onVisibilityChange)
    window.removeEventListener('pointerdown', onGlobalPointer)
    window.removeEventListener('keydown', onGlobalKey)
  })
  // GitHub OAuth 回调：严格区分「登录」与「绑定」。绑定必须调 bind-github 并保持当前用户，绝不能调 github-login
  const code = getGitHubCodeFromUrl()
  const isBindGithub = isBindGithubCallback()
  const ghOAuthKind = isBindGithub ? 'bind' : 'login'
  const urlState = new URLSearchParams(window.location.search).get('state') || route.query.state || ''
  const qClean = () => {
    const q = { ...route.query }
    delete q.code
    delete q.state
    delete q.bind
    return q
  }

  // 防范幽灵复苏 / 静默刷新的核心逻辑
  if (code) {
    const savedState = readGithubOAuthState(ghOAuthKind)

    // 如果没有合法的本地记录，或者 URL 里的 state 不匹配，说明这是过时历史 / 非法请求，直接截断
    if (!savedState || savedState !== urlState) {
      clearGithubOAuthState()
      router.replace({ path: route.path, query: qClean() })
      window.history.replaceState({}, '', window.location.pathname)
      loginErrorMessage.value = t('authModal.githubOAuthStateInvalid')
      setTimeout(() => {
        loginErrorMessage.value = ''
      }, 8000)
      setTimeout(() => {
        renderIcons()
      }, 50)
      return
    }

    // 状态安全匹配，一次性燃烧掉（防重用）
    clearGithubOAuthState()
  }

  if (code && isBindGithub) {
    // 绑定 GitHub：用当前登录用户调 bind-github，成功后仍为原账号，并清理 URL
    loginErrorMessage.value = ''
    loginSuccessMessage.value = ''
    try {
      const res = await api.auth.bindGitHub({
        code,
        use_other_nickname: false,
        redirect_uri: resolveGithubOAuthRedirectUriForTokenExchange(ghOAuthKind),
      })
      if (res.user) {
        auth.$patch({ user: res.user })
        const { setUserInfoRaw } = await import('./lib/storage')
        setUserInfoRaw(JSON.stringify(res.user))
      }
      auth.hydrate()
      router.replace({ path: route.path, query: qClean() })
      loginSuccessMessage.value = 'app.notifications.githubBound'
      window.dispatchEvent(new CustomEvent('github-bound'))
      if (window.opener) {
        window.opener.postMessage({ type: 'github-bound' }, window.location.origin)
        setTimeout(() => window.close(), 150)
      }
      setTimeout(() => { renderIcons() }, 50)
      setTimeout(() => { loginSuccessMessage.value = '' }, 3000)
    } catch (e: any) {
      console.error('绑定 GitHub 失败:', e)
      router.replace({ path: route.path, query: qClean() })
      const msg = e?.message || e?.detail || 'app.notifications.githubBindFailed'
      loginErrorMessage.value = msg
      setTimeout(() => { renderIcons() }, 50)
      setTimeout(() => { loginErrorMessage.value = '' }, 5000)
    }
    return
  }
  if (code && !isBindGithub) {
    loginErrorMessage.value = ''
    loginSuccessMessage.value = ''
    try {
      await auth.githubLogin(code, resolveGithubOAuthRedirectUriForTokenExchange(ghOAuthKind))
      router.replace({ path: route.path, query: qClean() })
      loginSuccessMessage.value = 'app.notifications.loginSuccess'
      setTimeout(() => { renderIcons() }, 50)
      setTimeout(() => { loginSuccessMessage.value = '' }, 3000)
    } catch (e: any) {
      console.error('GitHub 登录失败:', e)
      router.replace({ path: route.path, query: qClean() })
      const msg = e?.message || e?.detail || 'app.notifications.githubLoginFailed'
      loginErrorMessage.value = msg
      setTimeout(() => { renderIcons() }, 50)
      setTimeout(() => { loginErrorMessage.value = '' }, 5000)
    }
  }
})

onUnmounted(() => {
  detachUserMenuOutsideClick()
  stopStudioNoticePolling()
  if (studioNoticeDismissTimer !== null) {
    window.clearTimeout(studioNoticeDismissTimer)
    studioNoticeDismissTimer = null
  }
})

const avatarText = computed(() => (auth.user?.username?.[0] || 'U').toUpperCase())
function logout() {
  auth.logout()
  menuOpen.value = false
}

function onAuthModalClose() {
  authModalOpen.value = false
  loginSuccessMessage.value = ''
  loginErrorMessage.value = ''
}
// 路由守卫跳转到 /?login=1 时自动打开弹窗；登录成功后自动回跳 redirect
watch(
  () => route.query.login,
  (v) => {
    if (String(v || '') === '1') authModalOpen.value = true
    renderIcons()
  },
  { immediate: true }
)

// 登录后用户菜单区域才挂载，Lucide 不会自动扫到新节点，需再次 createIcons（否则汉堡图标空白）
watch(
  () => auth.isAuthed,
  (authed) => {
    if (!authed) return
    void nextTick(() => {
      renderIcons()
      setTimeout(() => renderIcons(), 100)
    })
  },
  { immediate: true }
)

// 菜单展开时：点击页面其它区域收起（queueMicrotask 避免与打开菜单的同一次 click 冲突）
watch(menuOpen, (open) => {
  detachUserMenuOutsideClick()
  if (!open) return
  userMenuOutsideClick = (e: MouseEvent) => {
    if (userMenuEl.value?.contains(e.target as Node)) return
    menuOpen.value = false
  }
  queueMicrotask(() => {
    if (menuOpen.value && userMenuOutsideClick) {
      document.addEventListener('click', userMenuOutsideClick, true)
    }
  })
})

// 任意路由切换后，重新渲染一次图标，避免从其他页面返回首页时样式丢失
watch(
  () => route.fullPath,
  () => {
    menuOpen.value = false
    renderIcons()
    if (auth.isAuthed) {
      void pollStudioJobNotifications()
    }
  }
)
// 注意：已移除误插入到 <script> 中的模板 HTML（语言切换按钮）
// 以及孤立的 `if (ok) { ... }` 逻辑，避免模板出现在脚本区导致的编译错误。
// 相关逻辑已在模板或其它位置保留/合并。

const formatMsg = (v: unknown) => {
  if (typeof v !== 'string') return v
  if (v.startsWith('app.') || v.startsWith('studio.') || v.startsWith('authModal.') || v.startsWith('wechatCallback.')) return t(v)
  return v
}
</script>

<style>
/* 对齐旧版整体视觉：深色背景 + 中英文字体 */
body {
  font-family: 'Inter', 'Noto Sans SC', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background-color: #0f172a;
  color: #f8fafc;
}

/* 旧版的玻璃面板效果（导航等可复用） */
.glass-panel {
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(148, 163, 184, 0.35);
}

.glass-dropdown {
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(148, 163, 184, 0.45);
}

.page-transition {
  animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(15px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 旧版的输入框样式 */
.input-dark {
  background: #0f172a;
  border: 1px solid #334155;
  color: white;
  padding: 0.75rem;
  border-radius: 0.5rem;
  width: 100%;
  outline: none;
  transition: border-color 0.2s;
}

.input-dark:focus {
  border-color: #6366f1;
}

/* 浏览器自动填充账号/邮箱/密码时，取消默认浅色底，保持与 .input-dark 一致的深色（Chrome / Edge / Safari） */
.input-dark:-webkit-autofill,
.input-dark:-webkit-autofill:hover,
.input-dark:-webkit-autofill:focus,
.input-dark:-webkit-autofill:active {
  -webkit-text-fill-color: #ffffff !important;
  caret-color: #ffffff;
  box-shadow: 0 0 0 1000px #0f172a inset !important;
  -webkit-box-shadow: 0 0 0 1000px #0f172a inset !important;
  border: 1px solid #334155 !important;
  transition: background-color 99999s ease-out 0s;
}

.input-dark:-webkit-autofill:focus {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 1000px #0f172a inset !important;
  -webkit-box-shadow: 0 0 0 1000px #0f172a inset !important;
}

/* 标准 :autofill（Firefox 等，能力因浏览器而异） */
.input-dark:autofill,
.input-dark:autofill:hover,
.input-dark:autofill:focus {
  box-shadow: 0 0 0 1000px #0f172a inset;
  -webkit-text-fill-color: #ffffff;
  color: #ffffff;
}

.app-nav-link {
  min-width: 64px;
  /* 英文「Hardware Market」等较长；左对齐 + 文字区 truncate，避免居中溢出时盖住左侧图标 */
  max-width: 13rem;
  padding: 0.5rem 0.375rem;
  font-size: clamp(0.9rem, 1.05vw, 1.1rem);
  font-weight: 600;
  color: rgb(203 213 225);
  transition: color 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.375rem;
  white-space: nowrap;
  overflow: hidden;
}

/* 保证头部右侧在切换语言时宽度稳定，避免中间导航被推移或遮挡 */
.header-right {
  min-width: 14rem;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

@media (max-width: 1024px) {
  .header-right {
    min-width: 9rem;
  }
}

.app-nav-link:hover {
  color: rgb(248 250 252);
}

/* removed app-nav-link-wide (reverted widening) */

/* 移动端折叠菜单样式优化 */
.mobile-nav-overlay {
  padding: 0.5rem;
}

/* 全局媒体优化：内容图片与视频自适应。组件内可加 class `content-responsive` 包裹内容 */
.content-responsive img,
.content-responsive video {
  max-width: 100%;
  height: auto;
  display: block;
}
</style>
