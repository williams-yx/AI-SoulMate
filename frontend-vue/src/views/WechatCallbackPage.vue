<template>
  <div class="min-h-screen flex items-center justify-center bg-[#0f172a] text-white p-4">
    <div class="text-center">
      <p v-if="status === 'loading'" class="text-slate-300">{{ t('wechatCallback.loading') }}</p>
      <p v-else-if="status === 'success'" class="text-emerald-400 font-medium">{{ t('wechatCallback.success') }}</p>
      <p v-else class="text-red-300">{{ formatMsg(errorMsg) || t('wechatCallback.failed') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { api } from '../lib/api'
import { setLoginVia, setToken, setUserInfoRaw } from '../lib/storage'

const route = useRoute()
const status = ref<'loading' | 'success' | 'error'>('loading')
const errorMsg = ref('')

const { t } = useI18n()

const formatMsg = (v: unknown) => {
  if (typeof v !== 'string') return v
  if (v.startsWith('wechatCallback.')) return t(v)
  return v
}

onMounted(async () => {
  const code = route.query.code as string | undefined
  if (!code) {
    status.value = 'error'
    errorMsg.value = 'wechatCallback.noCode'
    return
  }
  try {
    const res = await api.auth.wechatLogin(code)
    setToken(res.access_token)
    setLoginVia('wechat')
    if (res.user) setUserInfoRaw(JSON.stringify(res.user))
    window.dispatchEvent(new CustomEvent('auth-session-changed'))
    status.value = 'success'
    const payload = { type: 'wechat-login-success', access_token: res.access_token, user: res.user }
    if (window.parent !== window) {
      window.parent.postMessage(payload, window.location.origin)
    }
    if (window.opener) {
      window.opener.postMessage(payload, window.location.origin)
    }
  } catch (e: any) {
    status.value = 'error'
    errorMsg.value = e?.message || 'wechatCallback.wechatLoginFailed'
  }
})
</script>
