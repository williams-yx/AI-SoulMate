import { getToken, clearToken } from './storage'

export type ApiError = { detail?: string; message?: string }

/** 解析 FastAPI 的 detail（字符串 / 校验错误数组 / 对象） */
function normalizeDetail(data: unknown): string {
  if (data == null || typeof data !== 'object') return ''
  const o = data as Record<string, unknown>
  const d = o.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    return d
      .map((x: unknown) => {
        if (x && typeof x === 'object' && 'msg' in (x as object)) return String((x as { msg: string }).msg)
        return JSON.stringify(x)
      })
      .join('; ')
  }
  if (d != null && typeof d === 'object') return JSON.stringify(d)
  if (typeof o.message === 'string') return o.message
  return ''
}

/** 401 回调：由 main.ts 注册，用于调用 auth.logout() 避免循环依赖 */
let _onUnauthorized: (() => void) | null = null
export function setOnUnauthorized(fn: () => void) {
  _onUnauthorized = fn
}

// API 统一走同源前缀：开发环境由 Vite 代理，生产环境由 Nginx 代理。
const API_BASE_URL = ''

// 静态资源（/uploads）和代理下载（/api/studio/model-proxy）统一走同源。
const BACKEND_ORIGIN = ''

/**
 * 将后端返回的资源地址标准化为可直接在前端使用的 URL。
 * 支持: http(s)、/uploads、本地相对路径、oss://（通过后端代理访问）。
 */
export function resolveMediaUrl(rawPath: string | null | undefined): string {
  if (!rawPath || typeof rawPath !== 'string') return ''
  const path = rawPath.trim()
  if (!path) return ''

  const lower = path.toLowerCase()
  if (lower.startsWith('javascript:') || lower.startsWith('data:') || lower.startsWith('vbscript:')) {
    return ''
  }

  if (lower.startsWith('http://') || lower.startsWith('https://')) {
    return path
  }

  if (lower.startsWith('oss://') || lower.startsWith('models/')) {
    const cleanPath = path.split('/').pop() || 'file.bin'
    const token = `v${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
    return `${BACKEND_ORIGIN}/api/studio/model-proxy/${token}/${encodeURIComponent(cleanPath)}?url=${encodeURIComponent(path)}`
  }

  if (path.startsWith('/')) {
    return `${BACKEND_ORIGIN}${path}`
  }

  return `${BACKEND_ORIGIN}/${path}`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers || {})
  // GET/HEAD 不应带 application/json，少数反向代理会异常；multipart 由浏览器自动带 boundary
  const method = (init?.method || 'GET').toUpperCase()
  if (method !== 'GET' && method !== 'HEAD' && !(init?.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  // 构建完整的请求URL
  const url = path.startsWith('http') ? path : `${API_BASE_URL}${path}`
  let res: Response
  try {
    res = await fetch(url, { ...init, headers })
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    throw new Error(
      `网络请求失败: ${msg}。请确认后端已启动（开发环境默认 http://localhost:3000，且 Vite 已代理 /api）。`
    )
  }
  const text = await res.text()
  // 安全地解析JSON，处理非JSON响应
  let data: any = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch (e) {
      // 如果不是JSON格式，可能是HTML错误页面或其他格式
      // 对于错误响应，尝试提取有用信息
      if (!res.ok) {
        throw new Error(`请求失败(${res.status}): ${text.substring(0, 100)}`)
      }
      // 如果响应成功但不是JSON，返回原始文本（这种情况很少见）
      data = text
    }
  }

  // 200 但拿到的是 HTML：常见于未走 Vite 代理、或 /api 被 SPA 回退成 index.html，会导致「无报错但不显示验证码」
  if (
    res.ok &&
    typeof data === 'string' &&
    /^\s*</.test(data)
  ) {
    throw new Error(
      '接口返回了 HTML 而非 JSON。请用 Vite 开发地址访问（如 http://localhost:8080），并确认 vite 已将 /api 代理到后端 3000；Docker 下 frontend 需设置 VITE_API_TARGET=http://backend:3000。'
    )
  }
  if (res.ok && data === null && (!text || !String(text).trim())) {
    throw new Error('接口返回 200 但响应体为空')
  }

  if (!res.ok) {
    // 401 未授权：token 失效，通过回调清除 auth 状态（Pinia 响应式驱动 UI 更新）
    if (res.status === 401) {
      if (_onUnauthorized) {
        _onUnauthorized()
      } else {
        clearToken()
      }
    }
    const detail = normalizeDetail(data)
    const fallback =
      detail ||
      (typeof text === 'string' && text.trim()
        ? `${text.slice(0, 400)}${text.length > 400 ? '…' : ''}`
        : `HTTP ${res.status}（无响应正文，多为后端未启动、代理未指向 3000 或网关错误）`)
    throw new Error(fallback)
  }

  return data as T
}

export type LoginPayload =
  | { username: string; password: string; one_time_token: string }
  | { username: string; password: string; login_code: string; captcha_id: string }
  | { phone: string; phone_code: string; one_time_token: string }
  | { email: string; email_code: string; one_time_token: string }
  | { github_code: string }
  | { wechat_code: string }

export type RegisterPayload = {
  username: string
  password: string
  password_confirm: string
  register_via?: 'account' | 'phone' | 'email'
  phone?: string
  phone_code?: string
  email?: string
  email_code?: string
  wechat_code?: string
  github_code?: string
}

export type UserInfo = {
  id?: string
  username: string
  email?: string | null
  phone?: string | null
  avatar?: string | null
  credits?: number
  free_credits?: number
  redeemed_credits?: number
  paid_credits?: number
  gift_credits?: number
  free_points_refreshed_at?: string | null
  role?: string
}

export type AuthResponse = {
  access_token: string
  token_type: string
  user?: UserInfo
  _dev_mode?: boolean
}

export type OrderItem = {
  id: string
  name?: string
  price: number
  quantity: number
}

export type OrderCreatePayload = {
  items: OrderItem[]
  total_amount: number
  address_id?: string | null
  payment_method?: string | null
  shipping_address?: Record<string, any> | null
}

export type OrderListItem = {
  id: string
  items: any
  total_amount: number
  status: string
  created_at: string
}

export const api = {
  auth: {
    /** 账号登录第一步：图形验证通过后获取 one_time_token */
    loginAccountRequest: (username: string, captcha_id: string, captcha_code: string) =>
      request<{ one_time_token: string }>('/api/auth/login/account-request', {
        method: 'POST',
        body: JSON.stringify({ username, captcha_id, captcha_code }),
      }),
    /** 服务端清除 Redis 滑动会话；不走通用 request，避免 401 时触发全局登出回调 */
    logoutServer: async (): Promise<void> => {
      const token = getToken()
      if (!token) return
      const url = (API_BASE_URL || '') + '/api/auth/logout'
      try {
        await fetch(url, { method: 'POST', headers: { Authorization: `Bearer ${token}` } })
      } catch {
        /* ignore */
      }
    },
    /** 刷新服务端 Redis 滑动会话 TTL，与无操作 15 分钟对齐；应节流调用 */
    sessionTouch: () => request<{ ok: boolean }>('/api/auth/session/touch', { method: 'GET' }),
    /** 登录：成功返回 JWT；验证失败时返回 401 且 body 含 one_time_token，需用 requestLogin 以拿到完整 body */
    login: (payload: LoginPayload) =>
      request<AuthResponse>('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
    /** 登录并处理 401：成功返回 { success: true, data }，验证失败返回 { success: false, detail, one_time_token } */
    requestLogin: async (payload: LoginPayload): Promise<
      | { success: true; data: AuthResponse }
      | { success: false; detail: string; one_time_token?: string }
    > => {
      const url = (API_BASE_URL || '') + '/api/auth/login'
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}) },
        body: JSON.stringify(payload),
      })
      const data = await res.json().catch(() => ({})) as AuthResponse & { detail?: string; one_time_token?: string }
      if (res.ok) return { success: true, data: data as AuthResponse }
      return { success: false, detail: data.detail || '登录失败', one_time_token: data.one_time_token }
    },
    register: (payload: RegisterPayload) =>
      request<AuthResponse>('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
    getGitHubAuthUrl: (redirectUri: string) =>
      request<{ url: string; state?: string }>(`/api/auth/github-auth-url?redirect_uri=${encodeURIComponent(redirectUri)}`, { method: 'GET' }),
    githubLogin: (code: string, redirectUri?: string) =>
      request<AuthResponse>('/api/auth/github-login', {
        method: 'POST',
        body: JSON.stringify({
          code,
          ...(redirectUri ? { redirect_uri: redirectUri } : {}),
        }),
      }),
    getWechatAuthUrl: (redirectUri: string) =>
      request<{ url: string; state?: string }>(`/api/auth/wechat-auth-url?redirect_uri=${encodeURIComponent(redirectUri)}`, { method: 'GET' }),
    wechatLogin: (code: string) =>
      request<AuthResponse>('/api/auth/wechat-login', { method: 'POST', body: JSON.stringify({ code }) }),
    getCaptcha: () =>
      request<{ image: string; captcha_id: string }>('/api/auth/captcha', { method: 'GET' }),
    getCaptchaLockState: () =>
      request<{ locked: boolean; locked_until_utc?: string }>('/api/auth/captcha-lock-state', { method: 'GET' }),
    sendPhoneCode: (phone: string, captcha_id: string, captcha_code: string, scene: 'login' | 'register' = 'login') =>
      request<{ code?: string; message: string; one_time_token: string }>(
        `/api/auth/send-code?phone=${encodeURIComponent(phone)}&captcha_id=${encodeURIComponent(captcha_id)}&captcha_code=${encodeURIComponent(captcha_code)}&scene=${encodeURIComponent(scene)}`,
        { method: 'POST' }
      ),
    sendEmailCode: (email: string, captcha_id: string, captcha_code: string, scene: 'login' | 'register' = 'login') =>
      request<{ code?: string; message: string; one_time_token: string }>(
        `/api/auth/send-email-code?email=${encodeURIComponent(email)}&captcha_id=${encodeURIComponent(captcha_id)}&captcha_code=${encodeURIComponent(captcha_code)}&scene=${encodeURIComponent(scene)}`,
        { method: 'POST' }
      ),
    getIdentities: () =>
      request<{ items: Array<{ provider: string; provider_label: string; identifier_masked: string; linked_at: string }> }>('/api/auth/identities', { method: 'GET' }),
    updateProfile: (body: { nickname?: string; display_name_from?: string }) =>
      request<{ user: UserInfo }>('/api/auth/profile', { method: 'PATCH', body: JSON.stringify(body) }),
    bindPhone: (body: { phone: string; phone_code: string; use_other_nickname?: boolean }) =>
      request<{ phone: string; user?: UserInfo; merged?: boolean }>('/api/auth/bind-phone', { method: 'POST', body: JSON.stringify(body) }),
    bindEmail: (body: { email: string; email_code: string; use_other_nickname?: boolean }) =>
      request<{ email: string; user?: UserInfo; merged?: boolean }>('/api/auth/bind-email', { method: 'POST', body: JSON.stringify(body) }),
    bindWechat: (body: { code: string; use_other_nickname?: boolean }) =>
      request<{ user?: UserInfo; merged?: boolean }>('/api/auth/bind-wechat', { method: 'POST', body: JSON.stringify(body) }),
    bindGitHub: (body: { code: string; use_other_nickname?: boolean; redirect_uri?: string }) =>
      request<{ user?: UserInfo; merged?: boolean }>('/api/auth/bind-github', { method: 'POST', body: JSON.stringify(body) }),
    bindAccount: (body: { username: string; password: string; use_other_nickname?: boolean }) =>
      request<{ username: string; user?: UserInfo; merged?: boolean }>('/api/auth/bind-account', { method: 'POST', body: JSON.stringify(body) }),
    unbindAccount: () => request<{ user?: UserInfo }>('/api/auth/unbind-account', { method: 'POST' }),
    sendUnbindPhoneCode: (body: { captcha_id: string; captcha_code: string }) =>
      request<{ message: string }>('/api/auth/send-unbind-phone-code', { method: 'POST', body: JSON.stringify(body) }),
    sendUnbindEmailCode: (body: { captcha_id: string; captcha_code: string }) =>
      request<{ message: string }>('/api/auth/send-unbind-email-code', { method: 'POST', body: JSON.stringify(body) }),
    unbindPhone: (body: { phone_code: string }) =>
      request<{ user?: UserInfo }>('/api/auth/unbind-phone', { method: 'POST', body: JSON.stringify(body) }),
    unbindEmail: (body: { email_code: string }) =>
      request<{ user?: UserInfo }>('/api/auth/unbind-email', { method: 'POST', body: JSON.stringify(body) }),
    unbindWechat: () => request<{ user?: UserInfo }>('/api/auth/unbind-wechat', { method: 'POST' }),
    unbindGitHub: () => request<{ user?: UserInfo }>('/api/auth/unbind-github', { method: 'POST' })
  },
  user: {
    getProfile: () =>
      request<{ id: string; username: string; email?: string; phone?: string; credits?: number; free_credits?: number; redeemed_credits?: number; paid_credits?: number; gift_credits?: number; free_points_refreshed_at?: string | null; avatar?: string; role?: string; assets_count?: number }>('/api/user/profile', { method: 'GET' })
  },
  studio: {
    submitText3D: (payload: {
      prompt: string
      lora?: string
      model_config_id?: string
      with_texture?: boolean
      model?: '3.0' | '3.1'
      generate_type?: 'Normal' | 'LowPoly' | 'Geometry' | 'Sketch'
      face_count?: number
      enable_pbr?: boolean
      polygon_type?: 'triangle' | 'quadrilateral'
      result_format?: 'STL' | 'GLB'
      multi_view_images?: string[]
    }) =>
      request<{
        job_id: string
        status: string
        mode: 'text23d'
        texture_mode?: 'color' | 'white'
        generation_params?: Record<string, any>
        param_notes?: string[]
        credit_notes?: string[]
        status_endpoint?: string
        credits_used?: number
      }>(
        '/api/studio/submit-text-3d',
        { method: 'POST', body: JSON.stringify(payload) }
      ),
    submitImage3D: (payload: {
      image_base64: string
      lora?: string
      prompt?: string
      model_config_id?: string
      with_texture?: boolean
      model?: '3.0' | '3.1'
      generate_type?: 'Normal' | 'LowPoly' | 'Geometry' | 'Sketch'
      face_count?: number
      enable_pbr?: boolean
      polygon_type?: 'triangle' | 'quadrilateral'
      result_format?: 'STL' | 'GLB'
      multi_view_images?: string[]
    }) =>
      request<{
        job_id: string
        status: string
        mode: 'image23d'
        texture_mode?: 'color' | 'white'
        generation_params?: Record<string, any>
        param_notes?: string[]
        credit_notes?: string[]
        /** 与后端一致的参数摘要，用于侧栏/历史展示（非上游提示词） */
        display_prompt?: string
        status_endpoint?: string
        credits_used?: number
      }>(
        '/api/studio/submit-image-3d',
        { method: 'POST', body: JSON.stringify(payload) }
      ),
    getJobNotifications: (limit = 10) =>
      request<{
        items: Array<{
          job_id: string
          mode: 'text23d' | 'image23d'
          status: 'COMPLETED' | 'FAILED' | 'CANCELLED'
          message: string
          prompt: string
          asset_id?: string | null
          created_at?: string | null
          finished_at?: string | null
        }>
      }>(`/api/studio/job-notifications?limit=${encodeURIComponent(String(limit))}`, { method: 'GET' }),
    ackJobNotification: (jobId: string) =>
      request<{ ok: boolean; job_id: string }>(
        `/api/studio/job-notifications/${encodeURIComponent(jobId)}/ack`,
        { method: 'POST' }
      ),
    getSidebarJobs: (limit = 20) =>
      request<{
        items: Array<{
          job_id: string
          mode: 'text23d' | 'image23d'
          status: 'SUBMITTED' | 'PENDING' | 'QUEUED' | 'WAITING' | 'RUNNING' | 'PROCESSING' | 'IN_PROGRESS' | 'FAILED' | 'CANCELLED'
          progress: number
          message: string
          prompt: string
          preview_url?: string | null
          asset_id?: string | null
          created_at?: string | null
          finished_at?: string | null
          expires_at?: string | null
          texture_mode?: 'color' | 'white'
          generation_params?: Record<string, any> | null
          param_notes?: string[] | null
          credits_used?: number
        }>
      }>(`/api/studio/sidebar-jobs?limit=${encodeURIComponent(String(limit))}`, { method: 'GET' }),
    getPendingJobs: () =>
      request<{ job_ids: string[] }>('/api/studio/pending-jobs', { method: 'GET' }),
    queryJob: (jobId: string) =>
      request<{
        job_id: string
        status: 'SUBMITTED' | 'PENDING' | 'QUEUED' | 'WAITING' | 'RUNNING' | 'PROCESSING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
        progress: number
        message: string
        retryable?: boolean
        mode: 'text23d' | 'image23d' | null
        prompt?: string | null
        created_at?: string | null
        model_url?: string | null
        download_model_url?: string | null
        download_model_format?: string | null
        selected_model_url?: string | null
        selected_model_format?: string | null
        render_model_url?: string | null
        render_model_format?: string | null
        gcode_source_model_url?: string | null
        gcode_source_model_format?: string | null
        preview_url?: string | null
        asset_id?: string | null
        texture_mode?: 'color' | 'white'
        generation_params?: Record<string, any> | null
        param_notes?: string[] | null
        credits_used?: number
      }>(`/api/studio/job/${encodeURIComponent(jobId)}`, { method: 'GET' }),
    getHistory: (params?: { page?: number; page_size?: number }) =>
      request<{
        items: Array<{
          id: string
          mode: string
          prompt: string
          params: Record<string, unknown>
          preview_url: string | null
          model_url?: string | null
          download_model_url?: string | null
          download_model_format?: string | null
          selected_model_url?: string | null
          selected_model_format?: string | null
          render_model_url?: string | null
          render_model_format?: string | null
          gcode_source_model_url?: string | null
          gcode_source_model_format?: string | null
          asset_id: string | null
          is_published?: boolean
          created_at: string
        }>
        total: number
        page: number
        page_size: number
      }>(
        `/api/studio/history?page=${params?.page ?? 1}&page_size=${params?.page_size ?? 30}`,
        { method: 'GET' }
      ),
    deleteHistory: (id: string) =>
      request<{ ok: boolean }>(`/api/studio/history/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    translatePrompt: (payload: {
      text: string
      source_lang?: 'auto' | 'zh' | 'en'
      target_lang: 'zh' | 'en'
    }) =>
      request<{
        translated_text: string
        source_lang: 'auto' | 'zh' | 'en'
        target_lang: 'zh' | 'en'
        note?: string
      }>(
        '/api/studio/translate-prompt',
        { method: 'POST', body: JSON.stringify(payload) }
      ),
    optimizePrompt: (payload: {
      text: string
      mode: 'text2image' | 'text23d'
      source_lang?: 'auto' | 'zh' | 'en'
    }) =>
      request<{
        optimized_text: string
        mode: 'text2image' | 'text23d'
        source_lang: 'auto' | 'zh' | 'en'
      }>(
        '/api/studio/optimize-prompt',
        { method: 'POST', body: JSON.stringify(payload) }
      ),
    uploadLocalPreview: async (files: File[], primaryFileName?: string) => {
      const formData = new FormData()
      files.forEach((file) => formData.append('files', file))
      if (primaryFileName) {
        formData.append('primary_file_name', primaryFileName)
      }
      const headers = new Headers()
      const token = getToken()
      if (token) headers.set('Authorization', `Bearer ${token}`)

      const url = `${API_BASE_URL}/api/studio/local-preview/upload`
      const res = await fetch(url, {
        method: 'POST',
        headers,
        body: formData
      })
      const text = await res.text()
      let data: any = null
      if (text) {
        try {
          data = JSON.parse(text)
        } catch {
          data = { message: text }
        }
      }
      if (!res.ok) {
        const err = (data || {}) as ApiError
        throw new Error(err.detail || err.message || `上传失败(${res.status})`)
      }
      return data as {
        mode: 'local3dpreview'
        bundle_id: string
        model_url: string
        preview_url?: string | null
        primary_file: string
        files_count: number
      }
    },
    generate: (payload: {
      prompt: string
      lora?: string
      model_config_id?: string
      with_texture?: boolean
      model?: '3.0' | '3.1'
      generate_type?: 'Normal' | 'LowPoly' | 'Geometry' | 'Sketch'
      face_count?: number
      enable_pbr?: boolean
      polygon_type?: 'triangle' | 'quadrilateral'
      result_format?: 'STL' | 'GLB'
      multi_view_images?: string[]
      aspect_ratio?: '1:1' | '3:4' | '4:3' | '16:9' | '9:16'
      resolution_level?: '720p' | '1k' | '2k'
      image_size?: string
      style?: 'auto' | 'cinematic' | 'photoreal' | 'anime' | 'illustration' | 'watercolor' | 'pixel'
      quality?: 'standard' | 'hd' // 兼容旧端，可不传
    }) =>
      request<{
        credits_used?: number
        model_url?: string
        preview_url?: string
        asset_id?: string
        texture_mode?: 'color' | 'white'
        output_size?: string
        aspect_ratio?: string
        resolution_level?: '720p' | '1k' | '2k'
        style?: string
        quality?: 'standard' | 'hd'
        spec_note?: string
        generation_params?: Record<string, any>
        param_notes?: string[]
        credit_notes?: string[]
        message?: string
      }>(
        '/api/studio/generate',
        { method: 'POST', body: JSON.stringify(payload) }
      ),
    imageTo3D: (payload: {
      image_base64: string
      lora?: string
      prompt?: string
      model_config_id?: string
      with_texture?: boolean
      model?: '3.0' | '3.1'
      generate_type?: 'Normal' | 'LowPoly' | 'Geometry' | 'Sketch'
      face_count?: number
      enable_pbr?: boolean
      polygon_type?: 'triangle' | 'quadrilateral'
      result_format?: 'STL' | 'GLB'
      multi_view_images?: string[]
    }) =>
      request<{
        credits_used?: number
        model_url?: string
        preview_url?: string
        asset_id?: string
        texture_mode?: 'color' | 'white'
        generation_params?: Record<string, any>
        param_notes?: string[]
        credit_notes?: string[]
        message?: string
      }>(
        '/api/studio/image-to-3d',
        { method: 'POST', body: JSON.stringify(payload) }
      )
  }
  ,
  courses: {
    list: () =>
      request<Array<{ id: string; title: string; description: string; level: string; price: number; duration_hours: number }>>(
        '/api/courses',
        { method: 'GET' }
      )
  }
  ,
  assets: {
    list: (params?: { page?: number; page_size?: number; sort?: 'hot' | 'new' | 'popular' }) => {
      const q = new URLSearchParams()
      if (params?.page) q.set('page', String(params.page))
      if (params?.page_size) q.set('page_size', String(params.page_size))
      if (params?.sort) q.set('sort', params.sort)
      const qs = q.toString()
      return request<{ items: Array<{ id: string; image_url: string; prompt: string; base_model: string; tags: string[]; stats: { likes: number; downloads: number }; author_name: string; author_id?: string; liked_by_me?: boolean }>; total: number }>(
        `/api/assets${qs ? `?${qs}` : ''}`,
        { method: 'GET' }
      )
    },
    detail: (id: string) => request<any>(`/api/assets/${encodeURIComponent(id)}`, { method: 'GET' }),
    previewUrl: (id: string) =>
      request<{ asset_id: string; url: string }>(
        `/api/assets/${encodeURIComponent(id)}/preview-url`,
        { method: 'GET' },
      ),
    referenceImageUrl: (id: string) =>
      request<{ asset_id: string; url: string }>(
        `/api/assets/${encodeURIComponent(id)}/reference-image-url`,
        { method: 'GET' },
      ),
    modelUrl: (id: string) =>
      request<{ asset_id: string; url: string }>(
        `/api/assets/${encodeURIComponent(id)}/model-url`,
        { method: 'GET' },
      ),
    like: (id: string) => request<{ message: string; likes: number }>(`/api/assets/${encodeURIComponent(id)}/like`, { method: 'POST' }),
    unlike: (id: string) => request<{ message: string; likes: number }>(`/api/assets/${encodeURIComponent(id)}/unlike`, { method: 'POST' }),
    download: (id: string) => request<{ model_url: string; downloads: number }>(`/api/assets/${encodeURIComponent(id)}/download`, { method: 'POST' }),
    publish: (id: string) => request<{ message: string; asset_id: string; is_published: boolean }>(`/api/assets/${encodeURIComponent(id)}/publish`, { method: 'POST' }),
    delete: (id: string) => request<{ message: string; asset_id: string }>(`/api/assets/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    comments: (assetId: string, params?: { page?: number; page_size?: number; sort?: 'new' | 'liked' | 'replied' }) => {
      const q = new URLSearchParams()
      if (params?.page) q.set('page', String(params.page))
      if (params?.page_size) q.set('page_size', String(params.page_size))
      if (params?.sort) q.set('sort', params.sort)
      const qs = q.toString()
      return request<{
        items: Array<{
          id: string
          asset_id: string
          author_id: string
          author_name: string
          author_avatar?: string | null
          parent_id?: string | null
          content: string
          images?: string[]
          videos?: string[]
          like_count: number
          reply_count: number
          created_at: string
          liked_by_me?: boolean
          replies?: Array<{
            id: string
            author_name: string
            author_avatar?: string | null
            content: string
            images?: string[]
            videos?: string[]
            like_count: number
            created_at: string
            liked_by_me?: boolean
          }>
        }>
        total: number
        page: number
        page_size: number
      }>(`/api/assets/${encodeURIComponent(assetId)}/comments${qs ? `?${qs}` : ''}`, { method: 'GET' })
    },
    createComment: (assetId: string, payload: { content: string; parent_id?: string | null; images?: string[]; videos?: string[] }) =>
      request<{ comment_id: string; created_at?: string }>(
        `/api/assets/${encodeURIComponent(assetId)}/comments`,
        { method: 'POST', body: JSON.stringify(payload) }
      ),
    uploadCommentImage: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const headers = new Headers()
      const token = getToken()
      if (token) headers.set('Authorization', `Bearer ${token}`)
      const res = await fetch(`${API_BASE_URL}/api/assets/comments/upload-image`, {
        method: 'POST',
        headers,
        body: formData
      })
      const text = await res.text()
      const data = text ? JSON.parse(text) : null
      if (!res.ok) {
        // 401 统一处理：清 auth 状态，保持与 request() 一致
        if (res.status === 401) {
          if (_onUnauthorized) {
            _onUnauthorized()
          } else {
            clearToken()
          }
        }
        const err = (data || {}) as ApiError
        throw new Error(err.detail || err.message || `上传失败(${res.status})`)
      }
      return data as { url: string; filename: string }
    },
    uploadCommentVideo: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const headers = new Headers()
      const token = getToken()
      if (token) headers.set('Authorization', `Bearer ${token}`)
      const res = await fetch(`${API_BASE_URL}/api/assets/comments/upload-video`, {
        method: 'POST',
        headers,
        body: formData
      })
      const text = await res.text()
      const data = text ? JSON.parse(text) : null
      if (!res.ok) {
        if (res.status === 401) {
          if (_onUnauthorized) {
            _onUnauthorized()
          } else {
            clearToken()
          }
        }
        const err = (data || {}) as ApiError
        throw new Error(err.detail || err.message || `上传失败(${res.status})`)
      }
      return data as { url: string; filename: string }
    },
    likeComment: (assetId: string, commentId: string) =>
      request<{ liked: boolean }>(
        `/api/assets/${encodeURIComponent(assetId)}/comments/${encodeURIComponent(commentId)}/like`,
        { method: 'POST' }
      ),
    unlikeComment: (assetId: string, commentId: string) =>
      request<{ liked: boolean }>(
        `/api/assets/${encodeURIComponent(assetId)}/comments/${encodeURIComponent(commentId)}/like`,
        { method: 'DELETE' }
      ),
    deleteComment: (assetId: string, commentId: string) =>
      request<{ ok: boolean }>(
        `/api/assets/${encodeURIComponent(assetId)}/comments/${encodeURIComponent(commentId)}`,
        { method: 'DELETE' }
      )
  }
  ,
  community: {
    feed: (params?: { page?: number; page_size?: number; sort?: 'hot' | 'new' | 'popular' }) => {
      const q = new URLSearchParams()
      if (params?.page) q.set('page', String(params.page))
      if (params?.page_size) q.set('page_size', String(params.page_size))
      if (params?.sort) q.set('sort', params.sort)
      const qs = q.toString()
      return request<{
        items: Array<
          | {
              item_type: 'asset'
              id: string
              created_at?: string | null
              author_id?: string | null
              author_name: string
              liked_by_me?: boolean
              prompt: string
              image_url: string
              base_model: string
              tags: string[]
              stats: { likes: number; downloads: number }
            }
          | {
              item_type: 'post'
              id: string
              created_at?: string | null
              author_id?: string | null
              author_name: string
              liked_by_me?: boolean
              content: string
              images: string[]
              models: string[]
              videos: string[]
              stats: { likes: number }
            }
        >
        total: number
        page: number
        page_size: number
      }>(`/api/community/feed${qs ? `?${qs}` : ''}`, { method: 'GET' })
    },
    getPostDetail: (postId: string) =>
      request<{
        id: string
        author_id?: string | null
        author_name: string
        author_avatar?: string | null
        content: string
        images: string[]
        models: string[]
        videos: string[]
        created_at?: string | null
        updated_at?: string | null
        liked_by_me?: boolean
        stats: { likes: number }
      }>(`/api/community/posts/${encodeURIComponent(postId)}`, { method: 'GET' }),
    getPostComments: (postId: string, params?: { page?: number; page_size?: number; sort?: 'new' | 'liked' | 'replied' }) => {
      const q = new URLSearchParams()
      if (params?.page) q.set('page', String(params.page))
      if (params?.page_size) q.set('page_size', String(params.page_size))
      if (params?.sort) q.set('sort', params.sort)
      const qs = q.toString()
      return request<{
        items: Array<{
          id: string
          post_id: string
          author_id?: string | null
          author_name: string
          author_avatar?: string | null
          parent_id?: string | null
          content: string
          images?: string[]
          videos?: string[]
          like_count: number
          reply_count: number
          created_at: string
          liked_by_me?: boolean
          replies?: Array<{
            id: string
            post_id: string
            author_id?: string | null
            author_name: string
            author_avatar?: string | null
            parent_id?: string | null
            content: string
            images?: string[]
            videos?: string[]
            like_count: number
            reply_count: number
            created_at: string
            liked_by_me?: boolean
            replies?: any[]
          }>
        }>
        total: number
        page: number
        page_size: number
      }>(`/api/community/posts/${encodeURIComponent(postId)}/comments${qs ? `?${qs}` : ''}`, { method: 'GET' })
    },
    createPostComment: (postId: string, payload: { content?: string; parent_id?: string | null; images?: string[]; videos?: string[] }) =>
      request<{ comment_id: string; created_at?: string | null }>(
        `/api/community/posts/${encodeURIComponent(postId)}/comments`,
        { method: 'POST', body: JSON.stringify(payload) }
      ),
    uploadPostCommentImage: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const headers = new Headers()
      const token = getToken()
      if (token) headers.set('Authorization', `Bearer ${token}`)
      const res = await fetch(`${API_BASE_URL}/api/community/posts/comments/upload-image`, {
        method: 'POST',
        headers,
        body: formData
      })
      const text = await res.text()
      const data = text ? JSON.parse(text) : null
      if (!res.ok) {
        if (res.status === 401) {
          if (_onUnauthorized) {
            _onUnauthorized()
          } else {
            clearToken()
          }
        }
        const err = (data || {}) as ApiError
        throw new Error(err.detail || err.message || `上传失败(${res.status})`)
      }
      return data as { url: string; filename: string }
    },
    uploadPostCommentVideo: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const headers = new Headers()
      const token = getToken()
      if (token) headers.set('Authorization', `Bearer ${token}`)
      const res = await fetch(`${API_BASE_URL}/api/community/posts/comments/upload-video`, {
        method: 'POST',
        headers,
        body: formData
      })
      const text = await res.text()
      const data = text ? JSON.parse(text) : null
      if (!res.ok) {
        if (res.status === 401) {
          if (_onUnauthorized) {
            _onUnauthorized()
          } else {
            clearToken()
          }
        }
        const err = (data || {}) as ApiError
        throw new Error(err.detail || err.message || `上传失败(${res.status})`)
      }
      return data as { url: string; filename: string }
    },
    likePostComment: (postId: string, commentId: string) =>
      request<{ liked: boolean }>(
        `/api/community/posts/${encodeURIComponent(postId)}/comments/${encodeURIComponent(commentId)}/like`,
        { method: 'POST' }
      ),
    unlikePostComment: (postId: string, commentId: string) =>
      request<{ liked: boolean }>(
        `/api/community/posts/${encodeURIComponent(postId)}/comments/${encodeURIComponent(commentId)}/like`,
        { method: 'DELETE' }
      ),
    deletePostComment: (postId: string, commentId: string) =>
      request<{ ok: boolean }>(
        `/api/community/posts/${encodeURIComponent(postId)}/comments/${encodeURIComponent(commentId)}`,
        { method: 'DELETE' }
      ),
    createPost: (payload: { content?: string; images?: string[]; models?: string[]; videos?: string[] }) =>
      request<{ post_id: string; created_at?: string | null }>(
        '/api/community/posts',
        { method: 'POST', body: JSON.stringify(payload) }
      ),
    uploadPostImage: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const headers = new Headers()
      const token = getToken()
      if (token) headers.set('Authorization', `Bearer ${token}`)
      const res = await fetch(`${API_BASE_URL}/api/community/posts/upload-image`, {
        method: 'POST',
        headers,
        body: formData
      })
      const text = await res.text()
      const data = text ? JSON.parse(text) : null
      if (!res.ok) {
        if (res.status === 401) {
          if (_onUnauthorized) {
            _onUnauthorized()
          } else {
            clearToken()
          }
        }
        const err = (data || {}) as ApiError
        throw new Error(err.detail || err.message || `上传失败(${res.status})`)
      }
      return data as { url: string; filename: string }
    },
    uploadPostModel: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const headers = new Headers()
      const token = getToken()
      if (token) headers.set('Authorization', `Bearer ${token}`)
      const res = await fetch(`${API_BASE_URL}/api/community/posts/upload-model`, {
        method: 'POST',
        headers,
        body: formData
      })
      const text = await res.text()
      const data = text ? JSON.parse(text) : null
      if (!res.ok) {
        if (res.status === 401) {
          if (_onUnauthorized) {
            _onUnauthorized()
          } else {
            clearToken()
          }
        }
        const err = (data || {}) as ApiError
        throw new Error(err.detail || err.message || `上传失败(${res.status})`)
      }
      return data as { url: string; filename: string }
    },
    uploadPostVideo: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const headers = new Headers()
      const token = getToken()
      if (token) headers.set('Authorization', `Bearer ${token}`)
      const res = await fetch(`${API_BASE_URL}/api/community/posts/upload-video`, {
        method: 'POST',
        headers,
        body: formData
      })
      const text = await res.text()
      const data = text ? JSON.parse(text) : null
      if (!res.ok) {
        if (res.status === 401) {
          if (_onUnauthorized) {
            _onUnauthorized()
          } else {
            clearToken()
          }
        }
        const err = (data || {}) as ApiError
        throw new Error(err.detail || err.message || `上传失败(${res.status})`)
      }
      return data as { url: string; filename: string }
    },
    likePost: (postId: string) =>
      request<{ liked: boolean; likes: number }>(
        `/api/community/posts/${encodeURIComponent(postId)}/like`,
        { method: 'POST' }
      ),
    unlikePost: (postId: string) =>
      request<{ liked: boolean; likes: number }>(
        `/api/community/posts/${encodeURIComponent(postId)}/like`,
        { method: 'DELETE' }
      ),
    deletePost: (postId: string) =>
      request<{ ok: boolean; post_id: string }>(
        `/api/community/posts/${encodeURIComponent(postId)}`,
        { method: 'DELETE' }
      )
  }
  ,
  orders: {
    create: (payload: OrderCreatePayload) =>
      request<{ order_id: string; total_amount: number }>('/api/orders', { method: 'POST', body: JSON.stringify(payload) }),
    list: () => request<OrderListItem[]>('/api/orders', { method: 'GET' }),
    detail: (orderId: string) => request<any>(`/api/orders/${encodeURIComponent(orderId)}`, { method: 'GET' }),
    items: (orderId: string) => request<Array<any>>(`/api/orders/${encodeURIComponent(orderId)}/items`, { method: 'GET' }),
    cancel: (orderId: string) =>
      request<{ message: string }>(`/api/orders/${encodeURIComponent(orderId)}/cancel`, { method: 'POST' })
  },
  products: {
    categories: () => request<Array<{ id: string; name: string; description?: string; icon?: string }>>('/api/products/categories', { method: 'GET' }),
    list: (params?: { category_id?: string; status_filter?: string; page?: number; page_size?: number }) => {
      const q = new URLSearchParams()
      if (params?.category_id) q.set('category_id', params.category_id)
      if (params?.status_filter) q.set('status_filter', params.status_filter)
      if (params?.page) q.set('page', String(params.page))
      if (params?.page_size) q.set('page_size', String(params.page_size))
      const qs = q.toString()
      return request<{ items: Array<any>; total: number; page: number; page_size: number; total_pages: number }>(
        `/api/products${qs ? `?${qs}` : ''}`,
        { method: 'GET' }
      )
    },
    detail: (id: string) => request<any>(`/api/products/${encodeURIComponent(id)}`, { method: 'GET' })
  },
  printOrders: {
    create: (payload: { asset_id: string; height: string; material?: string; estimated_weight?: number }) =>
      request<{ order_id: string; print_job_id: string; total_amount: number; estimated_weight: number; price_per_gram: number; message: string }>(
        '/api/print-orders',
        { method: 'POST', body: JSON.stringify(payload) }
      ),
    getPrintJob: (orderId: string) => request<any>(`/api/print-orders/${encodeURIComponent(orderId)}/print-job`, { method: 'GET' }),
    estimateWeight: (payload: { height?: string; material?: string; model_volume?: number }) =>
      request<{
        estimated_weight: number;
        estimated_volume: number;
        material: string;
        density: number;
        height: string;
        price_per_gram: number;
        total_price: number;
        note?: string;
      }>(
        '/api/print-orders/estimate-weight',
        { method: 'POST', body: JSON.stringify(payload) }
      )
  },
  payments: {
    getMethods: (orderId?: string) => {
      const url = orderId 
        ? `/api/payments/methods?order_id=${encodeURIComponent(orderId)}`
        : '/api/payments/methods'
      return request<{ methods: Array<{ id: string; name: string; description: string; icon: string; test_mode: boolean; source?: string }>; default_currency: string; source?: string }>(url, { method: 'GET' })
    },
    getConfig: () => request<{ stripe_publishable_key?: string; paypal_client_id?: string }>('/api/payments/config', { method: 'GET' }),
    create: (payload: { order_id: string; payment_method: string; amount: number; currency?: string }) =>
      request<{ message: string; payment_method: string; payment_intent_id?: string; client_secret?: string; order_id?: string; approval_url?: string; checkout_url?: string; payment_url?: string; }>(
        '/api/payments/create',
        { method: 'POST', body: JSON.stringify(payload) }
      ),
    confirm: (payload: { order_id: string; payment_method: string; payment_id: string }) =>
      request<{ message: string; order_id: string; status: string }>(
        '/api/payments/confirm',
        { method: 'POST', body: JSON.stringify(payload) }
      )
  },
  print: {
    createJob: (assetId: string) =>
      request<{ job_id: string; status: string }>(
        `/api/print/jobs?asset_id=${encodeURIComponent(assetId)}`,
        { method: 'POST' }
      ),
    list: () =>
      request<Array<{ id: string; asset_id: string; status: string; credits_used: number; created_at: string; image_url?: string; prompt?: string }>>(
        '/api/print/jobs',
        { method: 'GET' }
      ),
    detail: (jobId: string) =>
      request<{ id: string; asset_id: string; status: string; credits_used: number; created_at: string }>(
        `/api/print/jobs/${encodeURIComponent(jobId)}`,
        { method: 'GET' }
      )
  },
  credits: {
    recharge: (payload: { amount: number; payment_method: string; return_url?: string }) =>
      request<{ recharge_id: string; amount: number; bonus_amount: number; total_amount: number; payment_method: string; payment_url?: string; message?: string }>(
        '/api/credits/recharge',
        { method: 'POST', body: JSON.stringify(payload) }
      ),
    getRechargeHistory: () =>
      request<{ records: Array<{ id: string; amount: number; bonus_amount?: number; total_amount?: number; amount_yuan: number; payment_method: string; status: string; created_at: string; paid_at?: string }> }>(
        '/api/credits/recharge-history',
        { method: 'GET' }
      ),
    getRechargeOrders: (params?: { page?: number; page_size?: number; status?: string }) => {
      const q = new URLSearchParams()
      if (params?.page) q.set('page', String(params.page))
      if (params?.page_size) q.set('page_size', String(params.page_size))
      if (params?.status) q.set('status', params.status)
      const qs = q.toString()
      return request<{
        orders: Array<{
          id: string
          amount: number
          bonus_amount: number
          total_amount: number
          amount_yuan: number
          remaining_credits: number
          credit_price: number
          payment_method: string
          status: string
          can_refund: boolean
          refund_deadline: string | null
          created_at: string
          paid_at: string | null
          refunded_at: string | null
          refund_amount: number | null
        }>
        total: number
        page: number
        page_size: number
        total_pages: number
      }>(`/api/credits/recharge-orders${qs ? `?${qs}` : ''}`, { method: 'GET' })
    },
    refundRechargeOrder: (rechargeId: string) =>
      request<{ success: boolean; message: string; refund_amount: number }>(
        `/api/credits/recharge-orders/${encodeURIComponent(rechargeId)}/refund`,
        { method: 'POST' }
      ),
    cancelRechargeOrder: (rechargeId: string) =>
      request<{ success: boolean; message: string }>(
        `/api/credits/recharge-orders/${encodeURIComponent(rechargeId)}/cancel`,
        { method: 'POST' }
      ),
    payRechargeOrder: (rechargeId: string, returnUrl?: string) => {
      const url = returnUrl 
        ? `/api/credits/recharge-orders/${encodeURIComponent(rechargeId)}/pay?return_url=${encodeURIComponent(returnUrl)}`
        : `/api/credits/recharge-orders/${encodeURIComponent(rechargeId)}/pay`
      return request<{ success: boolean; payment_url?: string; message: string }>(url, { method: 'POST' })
    },
    getRechargeTiers: () =>
      request<Array<{ id: number; min_amount: number; bonus_rate: number; bonus_fixed: number; description: string; sort_order: number; amount_yuan: number }>>(
        '/api/credits/recharge-tiers',
        { method: 'GET' }
      ),
    redeemCDK: (payload: { code: string }) =>
      request<{ points_awarded?: number; points?: number; free_credits?: number; redeemed_credits: number; gift_credits?: number; paid_credits?: number; credits?: number; message: string }>(
        '/api/credits/redeem-cdk',
        { method: 'POST', body: JSON.stringify(payload) }
      ),
    redeemCdk: (payload: { code: string }) =>
      request<{ points_awarded?: number; points?: number; free_credits?: number; redeemed_credits: number; gift_credits?: number; paid_credits?: number; credits?: number; message: string }>(
        '/api/credits/redeem-cdk',
        { method: 'POST', body: JSON.stringify(payload) }
      )
  }
}
