import { defineStore } from 'pinia'
import { api, type AuthResponse, type LoginPayload, type RegisterPayload, type UserInfo } from '../lib/api'
import { clearLoginVia, clearToken, clearUserInfo, getToken, getTokenExpMs, getUserInfoRaw, setLoginVia, setToken, setUserInfoRaw } from '../lib/storage'

function safeParseUser(raw: string): UserInfo | null {
  try {
    return raw ? (JSON.parse(raw) as UserInfo) : null
  } catch {
    return null
  }
}

/**
 * 无操作超过此时长则前端登出（与后端 JWT 最长有效期独立，见 _scheduleJwtExpiryLogout）。
 * 须与后端 Config.SESSION_IDLE_SECONDS（默认 900）一致。
 */
const IDLE_LOGOUT_MS = 15 * 60 * 1000

/** 向 /api/auth/session/touch 发请求的最小间隔，避免操作频繁时刷屏 */
const SERVER_SESSION_TOUCH_MIN_MS = 30 * 1000

let _idleTimer: ReturnType<typeof setTimeout> | null = null
let _jwtTimer: ReturnType<typeof setTimeout> | null = null
let _activityListenersBound = false
let _lastServerSessionTouchAttemptAt = 0

function clearIdleTimer() {
  if (_idleTimer !== null) {
    clearTimeout(_idleTimer)
    _idleTimer = null
  }
}

function clearJwtTimer() {
  if (_jwtTimer !== null) {
    clearTimeout(_jwtTimer)
    _jwtTimer = null
  }
}

/** 登录方式或 JWT 变化时通知个人中心等刷新绑定列表（避免仅 user.id 不变时不拉 identities） */
function emitAuthSessionChanged() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('auth-session-changed'))
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: getToken(),
    user: safeParseUser(getUserInfoRaw())
  }),
  getters: {
    isAuthed: (s) => !!s.token
  },
  actions: {
    /** 重置前端无操作倒计时，并节流刷新后端 Redis 滑动会话（与 SESSION_IDLE_SECONDS 对齐） */
    touchSessionActivity() {
      if (!this.token) return
      this._resetIdleLogoutTimer()
      this._maybeTouchServerSessionIdle()
    },

    _maybeTouchServerSessionIdle() {
      const now = Date.now()
      if (now - _lastServerSessionTouchAttemptAt < SERVER_SESSION_TOUCH_MIN_MS) return
      _lastServerSessionTouchAttemptAt = now
      void api.auth.sessionTouch().catch(() => {
        /* 网络失败不重置节流，下次操作再试 */
      })
    },

    /** 无操作 IDLE_LOGOUT_MS 后登出 */
    _resetIdleLogoutTimer() {
      clearIdleTimer()
      if (!getToken()) return
      _idleTimer = setTimeout(() => {
        _idleTimer = null
        this.logout()
      }, IDLE_LOGOUT_MS)
    },

    /** JWT 到期兜底登出（签发后绝对时间，由后端 ACCESS_TOKEN_EXPIRE_MINUTES 决定） */
    _scheduleJwtExpiryLogout() {
      clearJwtTimer()
      const expMs = getTokenExpMs()
      if (!expMs || !getToken()) return
      const remaining = expMs - Date.now()
      if (remaining <= 0) {
        this.logout()
        return
      }
      _jwtTimer = setTimeout(() => {
        _jwtTimer = null
        this.logout()
      }, remaining)
    },

    /** 登录 / hydrate 时：启动空闲计时 + JWT 到期计时 */
    _scheduleSessionTimers() {
      this._resetIdleLogoutTimer()
      this._scheduleJwtExpiryLogout()
    },

    /**
     * 在应用入口调用一次：监听全局交互，将切页、点击按钮、滚动等视为「有活动」并重置会话生命周期。
     * main.ts 中 router.afterEach 亦会 touchSessionActivity（切页）。
     */
    installSessionActivityListeners() {
      if (_activityListenersBound || typeof window === 'undefined') return
      _activityListenersBound = true
      const bump = () => {
        this.touchSessionActivity()
      }
      window.addEventListener('pointerdown', bump, true)
      window.addEventListener('keydown', bump, true)
      window.addEventListener('click', bump, true)
      window.addEventListener('wheel', bump, { passive: true, capture: true })
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') bump()
      })
    },

    /**
     * 仅从 localStorage 同步 token/user（供路由守卫、多标签页等）。
     * 不重置空闲/JWT 定时器，避免轮询与每次路由都打断「无操作登出」倒计时。
     */
    hydrate() {
      const t = getToken()
      if (this.token && !t) {
        this.logout()
        return
      }
      this.token = t
      this.user = safeParseUser(getUserInfoRaw())
    },
    async login(payload: LoginPayload) {
      const res: AuthResponse = await api.auth.login(payload)
      this.token = res.access_token
      setToken(res.access_token)
      const via = 'username' in payload && payload.username ? 'account' : 'phone' in payload && payload.phone ? 'phone' : 'email'
      setLoginVia(via)
      if (res.user) {
        this.user = res.user
        setUserInfoRaw(JSON.stringify(res.user))
      }
      this._scheduleSessionTimers()
      emitAuthSessionChanged()
      return res
    },
    /** 登录（支持 401 时返回新 one_time_token）：成功写入 token/user，失败返回 detail + one_time_token */
    async loginWithOTT(payload: LoginPayload): Promise<
      | { success: true; data: AuthResponse }
      | { success: false; detail: string; one_time_token?: string }
    > {
      const result = await api.auth.requestLogin(payload)
      if (result.success) {
        this.token = result.data.access_token
        setToken(result.data.access_token)
        const via = 'username' in payload && payload.username ? 'account' : 'phone' in payload && payload.phone ? 'phone' : 'email'
        setLoginVia(via)
        if (result.data.user) {
          this.user = result.data.user
          setUserInfoRaw(JSON.stringify(result.data.user))
        }
        this._scheduleSessionTimers()
        emitAuthSessionChanged()
      }
      return result
    },
    async register(payload: RegisterPayload) {
      const res: AuthResponse = await api.auth.register(payload)
      this.token = res.access_token
      setToken(res.access_token)
      const via: 'account' | 'phone' | 'email' = payload.phone ? 'phone' : payload.email ? 'email' : 'account'
      setLoginVia(via)
      if (res.user) {
        this.user = res.user
        setUserInfoRaw(JSON.stringify(res.user))
      }
      this._scheduleSessionTimers()
      emitAuthSessionChanged()
      return res
    },
    async githubLogin(code: string, redirectUri?: string) {
      const res: AuthResponse = await api.auth.githubLogin(code, redirectUri)
      this.token = res.access_token
      setToken(res.access_token)
      setLoginVia('github')
      if (res.user) {
        this.user = res.user
        setUserInfoRaw(JSON.stringify(res.user))
      }
      this._scheduleSessionTimers()
      emitAuthSessionChanged()
      return res
    },
    async wechatLogin(code: string) {
      const res: AuthResponse = await api.auth.wechatLogin(code)
      this.token = res.access_token
      setToken(res.access_token)
      setLoginVia('wechat')
      if (res.user) {
        this.user = res.user
        setUserInfoRaw(JSON.stringify(res.user))
      }
      this._scheduleSessionTimers()
      emitAuthSessionChanged()
      return res
    },
    async logout() {
      await api.auth.logoutServer().catch(() => {})
      clearIdleTimer()
      clearJwtTimer()
      _lastServerSessionTouchAttemptAt = 0
      this.token = ''
      this.user = null
      clearToken()
      clearUserInfo()
      clearLoginVia()
      emitAuthSessionChanged()
      
      // 清空购物车
      const { useCartStore } = await import('./cart')
      const cart = useCartStore()
      cart.clear()
    },

    /** 拉取 /api/user/profile 并合并到当前 user（充值成功等场景） */
    async refreshUser() {
      if (!this.token) return
      try {
        const profile = await api.user.getProfile()
        const merged = { ...(this.user || {}), ...profile } as UserInfo
        this.user = merged
        setUserInfoRaw(JSON.stringify(merged))
      } catch {
        /* ignore */
      }
    },
  }
})
