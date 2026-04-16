const REDIRECT_SESSION_KEY = 'github_oauth_redirect_uri_for_token'
const REDIRECT_LOCAL_KEY = 'github_oauth_redirect_uri_for_token'
const GITHUB_OAUTH_STATE_KEY = 'github_oauth_state'

export type GithubOAuthRedirectStashMode = 'same-tab' | 'popup'

/** 回调处理：登录走同标签 sessionStorage；绑定走 opener 与 popup 共用的 localStorage。 */
export type GithubOAuthCallbackKind = 'login' | 'bind'

/**
 * 从即将跳转的 GitHub 授权页 URL 中解析 redirect_uri（与换票参数必须一致）。
 * 须在跳转 GitHub 之前调用（登录弹窗 / 个人中心打开绑定窗口时）。
 * - same-tab：整页去 GitHub 再回本站，用 sessionStorage，避免其它标签页覆盖 stash。
 * - popup：新窗口回调与 opener 共用 localStorage。
 */
export function stashGithubOAuthRedirectUriFromAuthorizeUrl(
  authorizeUrl: string,
  mode: GithubOAuthRedirectStashMode = 'popup'
): void {
  try {
    const u = new URL(authorizeUrl)
    const ru = u.searchParams.get('redirect_uri')
    if (!ru) return
    if (mode === 'same-tab' && typeof sessionStorage !== 'undefined') {
      sessionStorage.setItem(REDIRECT_SESSION_KEY, ru)
      return
    }
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(REDIRECT_LOCAL_KEY, ru)
    }
  } catch {
    /* ignore */
  }
}

/** 取出并清除暂存的 redirect_uri（每次 OAuth 换票用一次） */
export function takeGithubOAuthRedirectUri(kind: GithubOAuthCallbackKind = 'login'): string | null {
  try {
    const takeLocal = (): string | null => {
      if (typeof localStorage === 'undefined') return null
      const v = localStorage.getItem(REDIRECT_LOCAL_KEY)
      localStorage.removeItem(REDIRECT_LOCAL_KEY)
      return v && v.trim() ? v.trim() : null
    }
    const takeSession = (): string | null => {
      if (typeof sessionStorage === 'undefined') return null
      const s = sessionStorage.getItem(REDIRECT_SESSION_KEY)
      if (!s) return null
      sessionStorage.removeItem(REDIRECT_SESSION_KEY)
      const t = s.trim()
      return t || null
    }
    if (kind === 'bind') {
      const fromLocal = takeLocal()
      if (fromLocal) return fromLocal
      return takeSession()
    }
    const fromSession = takeSession()
    if (fromSession) return fromSession
    return takeLocal()
  } catch {
    /* ignore */
  }
  return null
}

/** GitHub 登录（同标签整页跳转）：state 存 sessionStorage，避免其它标签 / 个人中心绑定流程改写 localStorage 导致回调校验失败。 */
export function setGithubOAuthStateForSameTabLogin(state: string): void {
  try {
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.setItem(GITHUB_OAUTH_STATE_KEY, state)
    }
  } catch {
    /* ignore */
  }
}

/** 个人中心弹窗绑定：回调在 popup 内读，需与 opener 共享，用 localStorage。 */
export function setGithubOAuthStateForBindPopup(state: string): void {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(GITHUB_OAUTH_STATE_KEY, state)
    }
  } catch {
    /* ignore */
  }
}

/** 读取待校验的 state（登录：先 session 再 local；绑定 popup：先 local 再 session，避免误用本窗口 session 里残留）。 */
export function readGithubOAuthState(kind: GithubOAuthCallbackKind = 'login'): string | null {
  try {
    const readLocal = (): string | null => {
      if (typeof localStorage === 'undefined') return null
      const l = localStorage.getItem(GITHUB_OAUTH_STATE_KEY)
      return l && l.trim() ? l.trim() : null
    }
    const readSession = (): string | null => {
      if (typeof sessionStorage === 'undefined') return null
      const s = sessionStorage.getItem(GITHUB_OAUTH_STATE_KEY)
      return s && s.trim() ? s.trim() : null
    }
    if (kind === 'bind') {
      return readLocal() || readSession()
    }
    return readSession() || readLocal()
  } catch {
    /* ignore */
  }
  return null
}

export function clearGithubOAuthState(): void {
  try {
    sessionStorage.removeItem(GITHUB_OAUTH_STATE_KEY)
    localStorage.removeItem(GITHUB_OAUTH_STATE_KEY)
  } catch {
    /* ignore */
  }
}

/** 从当前页 URL 推导 callback（去掉 code、state）；无 stash 时的兜底 */
export function githubOAuthRedirectUriForTokenExchange(): string {
  if (typeof window === 'undefined') return ''
  const u = new URL(window.location.href)
  u.searchParams.delete('code')
  u.searchParams.delete('state')
  const q = u.searchParams.toString()
  return u.origin + u.pathname + (q ? `?${q}` : '')
}

/** 优先使用跳转前暂存的 redirect_uri，避免查询参数顺序与授权时不一致 */
export function resolveGithubOAuthRedirectUriForTokenExchange(kind: GithubOAuthCallbackKind = 'login'): string {
  return takeGithubOAuthRedirectUri(kind) || githubOAuthRedirectUriForTokenExchange()
}
