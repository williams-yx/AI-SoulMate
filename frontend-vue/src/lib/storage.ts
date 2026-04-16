export const STORAGE_KEYS = {
  TOKEN: 'auth_token',
  USER_INFO: 'user_info',
  LOGIN_VIA: 'login_via' // 当前登录方式：account | phone | email | wechat | github，用于个人中心不显示该方式的解绑按钮
} as const

export function getToken(): string {
  return localStorage.getItem(STORAGE_KEYS.TOKEN) || ''
}

export function setToken(token: string) {
  localStorage.setItem(STORAGE_KEYS.TOKEN, token)
}

export function clearToken() {
  localStorage.removeItem(STORAGE_KEYS.TOKEN)
}

/**
 * 从已存储的 JWT 中解码 exp 字段，返回毫秒时间戳；token 缺失或格式异常时返回 null。
 */
export function getTokenExpMs(): number | null {
  const token = getToken()
  if (!token) return null
  try {
    const payloadB64 = token.split('.')[1]
    if (!payloadB64) return null
    const json = atob(payloadB64.replace(/-/g, '+').replace(/_/g, '/'))
    const payload = JSON.parse(json)
    if (typeof payload.exp === 'number') return payload.exp * 1000
    return null
  } catch {
    return null
  }
}

export function getUserInfoRaw(): string {
  return localStorage.getItem(STORAGE_KEYS.USER_INFO) || ''
}

export function setUserInfoRaw(v: string) {
  localStorage.setItem(STORAGE_KEYS.USER_INFO, v)
}

export function clearUserInfo() {
  localStorage.removeItem(STORAGE_KEYS.USER_INFO)
}

export type LoginVia = 'account' | 'phone' | 'email' | 'wechat' | 'github'

export function getLoginVia(): LoginVia | '' {
  return (localStorage.getItem(STORAGE_KEYS.LOGIN_VIA) as LoginVia) || ''
}

export function setLoginVia(v: LoginVia) {
  localStorage.setItem(STORAGE_KEYS.LOGIN_VIA, v)
}

export function clearLoginVia() {
  localStorage.removeItem(STORAGE_KEYS.LOGIN_VIA)
}
