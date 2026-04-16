<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <div class="rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur p-6">
      <div class="text-2xl font-bold mb-4">{{ t('profile.title') }}</div>

      <div v-if="!auth.isAuthed" class="text-slate-300">
        {{ t('profile.notLoggedIn') }}
      </div>

      <template v-else>
        <!-- 基础信息：显示名称、联系方式等为当前账号（所有已绑定身份合计）的最新数据 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm mb-6">
          <div><div class="text-xs text-slate-500">{{ t('profile.fields.displayName') }}</div><div class="mt-1">{{ (auth.user?.username ?? auth.user?.nickname) || '-' }}</div></div>
          <div><div class="text-xs text-slate-500">{{ t('profile.fields.email') }}</div><div class="mt-1">{{ auth.user?.email || t('profile.notBound') }}</div></div>
          <div class="md:col-span-2"><div class="text-xs text-slate-500">{{ t('profile.fields.phone') }}</div><div class="mt-1">{{ auth.user?.phone || t('profile.notBound') }}</div></div>
          <div v-if="showProfileRole" class="md:col-span-2"><div class="text-xs text-slate-500">{{ t('profile.fields.role') }}</div><div class="mt-1">{{ auth.user?.role || 'student' }}</div></div>
        </div>

        <!-- 积分查看：与「显示名称设置」「已绑定账号」等同级区块 -->
        <div class="border-t border-white/10 pt-4 mb-6">
          <div class="flex items-center justify-between mb-3">
            <div>
              <div class="text-sm font-medium text-slate-300">{{ t('profile.creditsSection.title') }}</div>
              <p class="text-xs text-slate-500 mt-1">{{ t('profile.creditsSection.desc') }}</p>
            </div>
            <div class="flex items-center gap-2">
              <button
                type="button"
                @click="showRedeemCdkPanel = !showRedeemCdkPanel"
                class="text-xs px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
              >
                {{ t('profile.redeemCdk.button') }}
              </button>
              <button
                type="button"
                @click="showRechargeModal = true"
                class="text-xs px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
              >
                {{ t('profile.recharge') }}
              </button>
            </div>
          </div>
          
          <div class="grid grid-cols-3 gap-4 text-sm">
            <!-- 免费积分 -->
            <div
              class="relative"
              @mouseenter="freeCreditsTipOpen = true"
              @mouseleave="freeCreditsTipOpen = false"
            >
              <div class="text-xs text-slate-500 mb-1">{{ t('profile.fields.freeCredits') }}</div>
              <div class="text-lg font-bold">{{ auth.user?.free_credits ?? auth.user?.credits ?? 0 }}</div>
              <div
                v-show="freeCreditsTipOpen"
                class="absolute z-10 top-full left-0 mt-1 min-w-[240px] max-w-[min(100vw-2rem,320px)] rounded-lg border border-white/20 bg-slate-800 p-3 text-xs text-left shadow-xl"
              >
                <div class="font-medium text-slate-300 mb-2">{{ t('profile.freeCreditsRules.title') }}</div>
                <p class="text-slate-400 leading-relaxed">{{ t('profile.freeCreditsRules.body') }}</p>
                <div class="mt-2 pt-2 border-t border-white/10 text-slate-300">
                  {{ freeCreditsCountdownText }}
                </div>
              </div>
            </div>
            
            <!-- 付费积分 -->
            <div>
              <div class="text-xs text-slate-500 mb-1">{{ t('profile.fields.paidCredits') }}</div>
              <div class="text-lg font-bold">{{ auth.user?.paid_credits ?? 0 }}</div>
            </div>
            
            <!-- 兑换积分 -->
            <div>
              <div class="text-xs text-slate-500 mb-1">{{ t('profile.fields.redeemedCredits') }}</div>
              <div class="text-lg font-bold">{{ auth.user?.redeemed_credits ?? 0 }}</div>
            </div>
          </div>
          
          <p class="text-xs text-slate-500 mt-3">{{ t('profile.creditsNote') }}</p>
          <p class="text-xs text-amber-400 mt-2">提示：早期充值的积分会优先被使用，可能影响退款。充值订单可在"订单"页面查看和管理。</p>
        </div>

        <div v-if="showRedeemCdkPanel" class="mb-5 rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4">
          <div class="text-sm font-medium text-emerald-200 mb-2">{{ t('profile.redeemCdk.title') }}</div>
          <p class="text-xs text-emerald-100/70 mb-3">{{ t('profile.redeemCdk.desc') }}</p>
          <div class="flex flex-col sm:flex-row gap-2 sm:items-center">
            <input
              v-model="redeemCdkInput"
              type="text"
              :placeholder="t('profile.redeemCdk.placeholder')"
              maxlength="80"
              class="rounded-lg bg-slate-800 border border-white/10 px-3 py-2 text-sm text-white placeholder-slate-500 sm:flex-1"
            />
            <button
              type="button"
              @click="redeemCdk"
              :disabled="redeemingCdk"
              class="rounded-lg bg-emerald-600 hover:bg-emerald-500 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              {{ redeemingCdk ? t('profile.redeemCdk.redeeming') : t('profile.redeemCdk.confirm') }}
            </button>
          </div>
          <p v-if="redeemCdkError" class="text-xs text-red-400 mt-2">{{ formatMsg(redeemCdkError) }}</p>
          <p v-else-if="redeemCdkSuccess" class="text-xs text-emerald-300 mt-2">{{ redeemCdkSuccess }}</p>
        </div>

        <!-- 个人中心显示哪个名字 -->
        <div class="border-t border-white/10 pt-4 mb-6">
          <div class="text-sm font-medium text-slate-300 mb-2">{{ t('profile.displayName.title') }}</div>
          <p class="text-xs text-slate-500 mb-2">{{ t('profile.displayName.desc') }}</p>
          <div class="flex flex-wrap gap-2 items-center">
            <input
              v-model="profileNickname"
              type="text"
              :placeholder="t('profile.placeholders.nickname')"
              class="rounded-lg bg-slate-800 border border-white/10 px-3 py-2 text-sm text-white placeholder-slate-500 w-40"
            />
            <span class="text-slate-500 text-sm">{{ t('profile.displayName.syncHint') }}</span>
            <select
              v-model="displayNameFrom"
              @change="onDisplayNameFromChange"
              class="rounded-lg bg-slate-800 border border-white/10 px-3 py-2 text-sm text-white"
            >
              <option value="">{{ t('profile.displayName.notSync') }}</option>
              <option v-for="item in identityOptions" :key="item.value" :value="item.value">{{ item.label }} ({{ item.masked }})</option>
            </select>
            <button
              type="button"
              @click="saveProfile"
              :disabled="savingProfile"
              class="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              {{ savingProfile ? t('profile.save.saving') : t('profile.save.save') }}
            </button>
            <p v-if="profileSaveError" class="text-xs text-red-400 mt-1">{{ formatMsg(profileSaveError) }}</p>
          </div>
        </div>

        <!-- 已绑定账号 -->
        <div class="border-t border-white/10 pt-4 mb-6">
          <div class="text-sm font-medium text-slate-300 mb-2">{{ t('profile.boundAccounts.title') }}</div>
          <p class="text-xs text-slate-500 mb-2">{{ t('profile.boundAccounts.desc') }}</p>
          <ul v-if="identities.length" class="space-y-1 text-sm">
            <li v-for="(item, i) in identities" :key="i" class="flex items-center gap-2 text-slate-300">
              <span class="text-slate-500 w-12">{{ item.provider_label }}</span>
              <span>{{ item.identifier_masked }}</span>
            </li>
          </ul>
          <p v-else-if="identitiesLoading" class="text-slate-500 text-sm">{{ t('profile.boundAccounts.loading') }}</p>
          <p v-else-if="identitiesLoadError" class="text-red-400 text-sm">{{ t('profile.boundAccounts.loadFailed') }}</p>
          <p v-else class="text-slate-500 text-sm">{{ t('profile.boundAccounts.empty') }}</p>
        </div>

        <!-- 绑定更多 / 解绑 -->
        <div class="border-t border-white/10 pt-4">
          <div class="text-sm font-medium text-slate-300 mb-2">{{ t('profile.binding.title') }}</div>
          <p class="text-xs text-slate-500 mb-3">{{ t('profile.binding.desc') }}<strong class="text-slate-400">{{ t('profile.binding.currentCannotUnbind') }}</strong></p>
          <p v-if="bindCodeError" class="text-xs text-red-400 mb-2">{{ formatMsg(bindCodeError) }}</p>

          <!-- 手机 -->
          <div class="mb-4">
            <div v-if="identityByProvider('phone')" class="flex items-center gap-2 flex-wrap">
              <span class="text-slate-300 text-sm">{{ t('profile.boundLabel', { provider: t('profile.fields.phone') }) }} {{ identityByProvider('phone')?.identifier_masked }}</span>
              <button v-if="canUnbind('phone')" type="button" @click="openUnbindModal('phone')" class="rounded px-3 py-1.5 text-xs text-amber-400 hover:bg-white/5 border border-amber-500/50">{{ t('profile.actions.unbind') }}</button>
              <span v-else class="text-xs text-slate-500">（{{ t('profile.binding.currentCannotUnbind') }}）</span>
            </div>
            <template v-else>
            <button
              v-if="!bindPhoneOpen"
              type="button"
              @click="bindPhoneOpen = true"
              class="rounded-lg border border-white/20 px-3 py-2 text-sm text-slate-300 hover:bg-white/5"
            >
              {{ t('profile.actions.bindPhone') }}
            </button>
            <div v-else class="rounded-lg bg-slate-800/80 p-3 space-y-2 max-w-sm">
              <input v-model="bindPhoneNumber" type="text" :placeholder="t('profile.placeholders_extra.phone')" class="rounded bg-slate-700 border border-white/10 px-3 py-2 text-sm text-white w-full" />
              <div class="flex gap-2 items-center">
                <input v-model="bindCaptchaInput" type="text" :placeholder="t('profile.placeholders_extra.captcha')" maxlength="6" class="rounded bg-slate-700 border border-white/10 px-3 py-2 text-sm text-white flex-1" />
                <img v-if="bindCaptchaImage" :src="bindCaptchaImage" :alt="t('profile.placeholders_extra.captcha')" class="w-24 h-9 rounded border border-white/10 object-contain cursor-pointer" :title="t('authModal.captchaClickRefresh')" @click="fetchBindCaptcha" />
              </div>
              <div class="flex gap-2">
                <input v-model="bindPhoneCode" type="text" :placeholder="t('profile.placeholders_extra.code')" class="rounded bg-slate-700 border border-white/10 px-3 py-2 text-sm text-white flex-1" />
                <button type="button" @click="sendPhoneCode" :disabled="sendingPhoneCode" class="rounded px-3 py-2 text-sm bg-slate-600 text-white disabled:opacity-50">
                  {{ sendingPhoneCode ? t('profile.actions.sending') : t('profile.actions.getCode') }}
                </button>
              </div>
              <p v-if="bindCodeError" class="text-xs text-red-400">{{ formatMsg(bindCodeError) }}</p>
              <p v-else-if="bindCodeSuccess" class="text-xs text-emerald-400">{{ formatMsg(bindCodeSuccess) }}</p>
              <label class="flex items-center gap-2 text-xs text-slate-400">
                <input type="checkbox" v-model="bindUseOtherNickname" />
                {{ t('profile.mergeHint') }}
              </label>
              <div class="flex gap-2">
                <button type="button" @click="bindPhone" :disabled="bindingPhone" class="rounded px-3 py-2 text-sm bg-indigo-600 text-white disabled:opacity-50">{{ t('profile.actions.confirmBind') }}</button>
                <button type="button" @click="bindPhoneOpen = false" class="rounded px-3 py-2 text-sm text-slate-400 hover:bg-white/5">{{ t('profile.actions.cancel') }}</button>
              </div>
            </div>
            </template>
          </div>

          <!-- 邮箱 -->
          <div class="mb-4">
            <div v-if="identityByProvider('email')" class="flex items-center gap-2 flex-wrap">
              <span class="text-slate-300 text-sm">{{ t('profile.boundLabel', { provider: t('profile.fields.email') }) }} {{ identityByProvider('email')?.identifier_masked }}</span>
              <button v-if="canUnbind('email')" type="button" @click="openUnbindModal('email')" class="rounded px-3 py-1.5 text-xs text-amber-400 hover:bg-white/5 border border-amber-500/50">{{ t('profile.actions.unbind') }}</button>
              <span v-else class="text-xs text-slate-500">（{{ t('profile.binding.currentCannotUnbind') }}）</span>
            </div>
            <template v-else>
            <button
              v-if="!bindEmailOpen"
              type="button"
              @click="bindEmailOpen = true"
              class="rounded-lg border border-white/20 px-3 py-2 text-sm text-slate-300 hover:bg-white/5"
            >
              {{ t('profile.actions.bindEmail') }}
            </button>
            <div v-else class="rounded-lg bg-slate-800/80 p-3 space-y-2 max-w-sm">
              <input v-model="bindEmailAddr" type="email" :placeholder="t('profile.placeholders_extra.email')" class="rounded bg-slate-700 border border-white/10 px-3 py-2 text-sm text-white w-full" />
              <div class="flex gap-2 items-center">
                <input v-model="bindCaptchaInput" type="text" :placeholder="t('profile.placeholders_extra.captcha')" maxlength="6" class="rounded bg-slate-700 border border-white/10 px-3 py-2 text-sm text-white flex-1" />
                <img v-if="bindCaptchaImage" :src="bindCaptchaImage" :alt="t('profile.placeholders_extra.captcha')" class="w-24 h-9 rounded border border-white/10 object-contain cursor-pointer" :title="t('authModal.captchaClickRefresh')" @click="fetchBindCaptcha" />
              </div>
              <div class="flex gap-2">
                <input v-model="bindEmailCode" type="text" :placeholder="t('profile.placeholders_extra.code')" class="rounded bg-slate-700 border border-white/10 px-3 py-2 text-sm text-white flex-1" />
                <button type="button" @click="sendEmailCode" :disabled="sendingEmailCode" class="rounded px-3 py-2 text-sm bg-slate-600 text-white disabled:opacity-50">
                  {{ sendingEmailCode ? t('profile.actions.sending') : t('profile.actions.getCode') }}
                </button>
              </div>
              <p v-if="bindCodeError" class="text-xs text-red-400">{{ formatMsg(bindCodeError) }}</p>
              <p v-else-if="bindCodeSuccess" class="text-xs text-emerald-400">{{ formatMsg(bindCodeSuccess) }}</p>
              <label class="flex items-center gap-2 text-xs text-slate-400">
                <input type="checkbox" v-model="bindUseOtherNickname" />
                {{ t('profile.mergeHint') }}
              </label>
              <div class="flex gap-2">
                <button type="button" @click="bindEmail" :disabled="bindingEmail" class="rounded px-3 py-2 text-sm bg-indigo-600 text-white disabled:opacity-50">{{ t('profile.actions.confirmBind') }}</button>
                <button type="button" @click="bindEmailOpen = false" class="rounded px-3 py-2 text-sm text-slate-400 hover:bg-white/5">{{ t('profile.actions.cancel') }}</button>
              </div>
            </div>
            </template>
          </div>

          <!-- 账号 -->
          <div class="mb-4">
            <div v-if="identityByProvider('account')" class="flex items-center gap-2 flex-wrap">
              <span class="text-slate-300 text-sm">{{ t('profile.boundLabel', { provider: t('profile.fields.account') }) }} {{ identityByProvider('account')?.identifier_masked }}</span>
              <button v-if="canUnbind('account')" type="button" @click="unbindAccount" :disabled="unbindingAccount" class="rounded px-3 py-1.5 text-xs text-amber-400 hover:bg-white/5 border border-amber-500/50 disabled:opacity-50">{{ t('profile.actions.unbind') }}</button>
              <span v-else class="text-xs text-slate-500">（{{ t('profile.binding.currentCannotUnbind') }}）</span>
            </div>
            <template v-else>
            <button
              v-if="!bindAccountOpen"
              type="button"
              @click="bindAccountOpen = true"
              class="rounded-lg border border-white/20 px-3 py-2 text-sm text-slate-300 hover:bg-white/5"
            >
              {{ t('profile.actions.bindAccount') }}
            </button>
            <div v-else class="rounded-lg bg-slate-800/80 p-3 space-y-2 max-w-sm">
              <input v-model="bindAccountUsername" type="text" :placeholder="t('profile.placeholders_extra.accountInput')" class="rounded bg-slate-700 border border-white/10 px-3 py-2 text-sm text-white w-full" />
              <PasswordInput
                v-model="bindAccountPassword"
                :placeholder="t('profile.placeholders_extra.password')"
                autocomplete="current-password"
                input-class="rounded bg-slate-700 border border-white/10 px-3 py-2 pr-10 text-sm text-white w-full outline-none focus:border-indigo-500"
              />
              <label class="flex items-center gap-2 text-xs text-slate-400">
                <input type="checkbox" v-model="bindUseOtherNickname" />
                {{ t('profile.mergeHint') }}
              </label>
              <p v-if="bindAccountError" class="text-xs text-red-400">{{ formatMsg(bindAccountError) }}</p>
              <div class="flex gap-2">
                <button type="button" @click="bindAccount" :disabled="bindingAccount" class="rounded px-3 py-2 text-sm bg-indigo-600 text-white disabled:opacity-50">{{ t('profile.actions.confirmBind') }}</button>
                <button type="button" @click="bindAccountOpen = false" class="rounded px-3 py-2 text-sm text-slate-400 hover:bg-white/5">{{ t('profile.actions.cancel') }}</button>
              </div>
            </div>
            </template>
          </div>

          <!-- 微信 / GitHub -->
          <div class="flex flex-wrap gap-2 items-center">
            <template v-if="identityByProvider('wechat')">
              <span class="text-slate-300 text-sm">{{ t('profile.boundLabel', { provider: t('profile.fields.wechat') }) }} {{ identityByProvider('wechat')?.identifier_masked }}</span>
              <button v-if="canUnbind('wechat')" type="button" @click="unbindWechat" :disabled="unbindingWechat" class="rounded px-3 py-1.5 text-xs text-amber-400 hover:bg-white/5 border border-amber-500/50 disabled:opacity-50">{{ t('profile.actions.unbind') }}</button>
              <span v-else class="text-xs text-slate-500">（{{ t('profile.binding.currentCannotUnbind') }}）</span>
            </template>
            <a v-else :href="wechatAuthUrl" target="_blank" rel="noopener" class="rounded-lg border border-white/20 px-3 py-2 text-sm text-slate-300 hover:bg-white/5">{{ t('profile.actions.bindWechat') }}</a>
            <template v-if="identityByProvider('github')">
              <span class="text-slate-300 text-sm">{{ t('profile.boundLabel', { provider: t('profile.fields.github') }) }} {{ identityByProvider('github')?.identifier_masked }}</span>
              <button v-if="canUnbind('github')" type="button" @click="unbindGitHub" :disabled="unbindingGitHub" class="rounded px-3 py-1.5 text-xs text-amber-400 hover:bg-white/5 border border-amber-500/50 disabled:opacity-50">{{ t('profile.actions.unbind') }}</button>
              <span v-else class="text-xs text-slate-500">（{{ t('profile.binding.currentCannotUnbind') }}）</span>
            </template>
            <template v-else>
              <button type="button" @click="openGitHubBindWindow" class="rounded-lg border border-white/20 px-3 py-2 text-sm text-slate-300 hover:bg-white/5">{{ t('profile.actions.bindGitHub') }}</button>
              <p class="text-xs text-slate-500 mt-1">{{ t('profile.githubBindHint') }}</p>
            </template>
          </div>
          <p class="text-xs text-slate-500 mt-2">{{ t('profile.bindReturnHint') }}</p>
        </div>
      </template>
    </div>

    <!-- 解绑验证弹窗（手机/邮箱） -->
    <div v-if="unbindModal" class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" @click.self="unbindModal = null">
      <div class="rounded-xl bg-slate-800 border border-slate-600 p-5 max-w-sm w-full shadow-xl">
        <h3 class="text-base font-medium text-white mb-3">{{ unbindModal === 'phone' ? t('profile.unbindModal.titlePhone') : t('profile.unbindModal.titleEmail') }}</h3>
        <p class="text-xs text-slate-400 mb-3">{{ t('profile.unbindModal.captchaHint', { target: unbindModal === 'phone' ? t('profile.fields.phone') : t('profile.fields.email') }) }}</p>
        <div class="flex gap-2 items-center mb-2">
          <input v-model="unbindCaptchaInput" type="text" :placeholder="t('profile.placeholders_extra.captcha')" maxlength="6" class="rounded bg-slate-700 border border-white/10 px-3 py-2 text-sm text-white flex-1" />
          <img v-if="unbindCaptchaImage" :src="unbindCaptchaImage" :alt="t('profile.placeholders_extra.captcha')" class="w-24 h-9 rounded border border-white/10 object-contain cursor-pointer" :title="t('authModal.captchaClickRefresh')" @click="fetchUnbindCaptcha" />
        </div>
        <button type="button" @click="sendUnbindCode" :disabled="sendingUnbindCode" class="mb-3 w-full rounded py-2 text-sm bg-slate-600 text-white disabled:opacity-50">
          {{ sendingUnbindCode ? t('profile.actions.sending') : (unbindModal === 'phone' ? t('profile.unbindModal.sendPhone') : t('profile.unbindModal.sendEmail')) }}
        </button>
        <input v-model="unbindCodeInput" type="text" :placeholder="unbindModal === 'phone' ? t('authModal.smsCodePlaceholder') : t('authModal.emailCodePlaceholder')" class="rounded bg-slate-700 border border-white/10 px-3 py-2 text-sm text-white w-full mb-3" />
          <p v-if="unbindModalError" class="text-xs text-red-400 mb-2">{{ formatMsg(unbindModalError) }}</p>
        <div class="flex gap-2">
          <button type="button" @click="confirmUnbind" :disabled="unbindingPhone || unbindingEmail || !unbindCodeInput.trim()" class="flex-1 rounded py-2 text-sm bg-amber-600 text-white disabled:opacity-50">{{ t('profile.actions.confirmUnbind') }}</button>
          <button type="button" @click="unbindModal = null" class="rounded py-2 text-sm text-slate-400 hover:bg-white/5 px-4">{{ t('profile.actions.cancel') }}</button>
        </div>
      </div>
    </div>

    <!-- 充值弹窗 -->
    <RechargeModal
      :open="showRechargeModal"
      @close="showRechargeModal = false"
      @success="handleRechargeSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { api } from '../lib/api'
import {
  setGithubOAuthStateForBindPopup,
  stashGithubOAuthRedirectUriFromAuthorizeUrl,
} from '../lib/githubOAuth'
import { getLoginVia, setUserInfoRaw } from '../lib/storage'
import RechargeModal from '../components/RechargeModal.vue'
import PasswordInput from '../components/PasswordInput.vue'

const auth = useAuthStore()
const { t } = useI18n()
const formatMsg = (v: unknown) => {
  if (typeof v !== 'string') return v
  if (
    v.startsWith('authModal.') ||
    v.startsWith('profile.') ||
    v.startsWith('community.') ||
    v.startsWith('postDetail.') ||
    v.startsWith('assetDetail.')
  ) {
    return t(v)
  }
  return v
}
const loginVia = ref(getLoginVia())
const showRechargeModal = ref(false)
const showRedeemCdkPanel = ref(false)
const redeemCdkInput = ref('')
const redeemingCdk = ref(false)
const redeemCdkError = ref('')
const redeemCdkSuccess = ref('')
/** 角色能力未就绪，个人中心暂不展示；就绪后改为 true */
const showProfileRole = false

function canUnbind(provider: string) {
  return loginVia.value !== provider
}

const identities = ref<Array<{ provider: string; provider_label: string; identifier_masked: string; linked_at: string }>>([])
const identitiesLoading = ref(false)
const identitiesLoadError = ref(false)
const profileNickname = ref('')
const displayNameFrom = ref('')
const savingProfile = ref(false)
const profileSaveError = ref('')
const identityOptions = computed(() =>
  identities.value.map((i) => ({ value: i.provider, label: i.provider_label, masked: i.identifier_masked }))
)
function identityByProvider(provider: string) {
  return identities.value.find((i) => i.provider === provider)
}

const bindPhoneOpen = ref(false)
const bindPhoneNumber = ref('')
const bindPhoneCode = ref('')
const sendingPhoneCode = ref(false)
const bindingPhone = ref(false)
const bindEmailOpen = ref(false)
const bindEmailAddr = ref('')
const bindEmailCode = ref('')
const sendingEmailCode = ref(false)
const bindingEmail = ref(false)
const bindUseOtherNickname = ref(false)
const bindCaptchaImage = ref('')
const bindCaptchaId = ref('')
const bindCaptchaInput = ref('')
const bindCodeError = ref('')
const bindCodeSuccess = ref('')
const bindAccountOpen = ref(false)
const bindAccountUsername = ref('')
const bindAccountPassword = ref('')
const bindAccountError = ref('')
const bindingAccount = ref(false)
const unbindingPhone = ref(false)
const unbindingEmail = ref(false)
const unbindingAccount = ref(false)
const unbindingWechat = ref(false)
const unbindingGitHub = ref(false)

const unbindModal = ref<'phone' | 'email' | null>(null)
const unbindCaptchaImage = ref('')
const unbindCaptchaId = ref('')
const unbindCaptchaInput = ref('')
const unbindCodeInput = ref('')
const unbindModalError = ref('')
const sendingUnbindCode = ref(false)

const wechatAuthUrl = ref('')
const githubAuthUrl = ref('')
const freeCreditsTipOpen = ref(false)

const freeCreditsRefreshedAt = computed(() => {
  const raw = auth.user?.free_points_refreshed_at
  if (raw == null || raw === '') return null
  const t = new Date(String(raw)).getTime()
  return Number.isFinite(t) ? t : null
})
const freeCreditsCurrent = computed(() => {
  const u = auth.user
  if (!u) return 0
  if (u.free_credits != null && u.free_credits !== undefined) return Number(u.free_credits)
  const fp = (u as { free_points?: number }).free_points
  if (fp != null && fp !== undefined) return Number(fp)
  return Number(u.credits ?? 0)
})
/** 本轮已因使用免费积分而写入计时起点，且当前未满 100，显示距「起点+24h」的倒计时 */
const freeCreditsCountdownActive = computed(
  () => freeCreditsRefreshedAt.value != null && freeCreditsCurrent.value < 100
)
const FREE_REFRESH_MS = 24 * 60 * 60 * 1000
const freeCreditsNextRefreshAt = computed(() => {
  if (!freeCreditsCountdownActive.value) return null
  const at = freeCreditsRefreshedAt.value
  return at != null ? at + FREE_REFRESH_MS : null
})
const freeCreditsCountdownText = computed(() => {
  if (!freeCreditsCountdownActive.value) {
    return freeCreditsCurrent.value >= 100
      ? t('profile.freeCreditsRules.countdown.atFull')
      : t('profile.freeCreditsRules.countdown.needRefresh')
  }
  const next = freeCreditsNextRefreshAt.value
  if (next == null) return ''
  const now = Date.now()
  if (now >= next) {
    return t('profile.freeCreditsRules.countdown.pastDue')
  }
  const d = new Date(next)
  const pad = (n: number) => String(n).padStart(2, '0')
  const remain = next - now
  const h = Math.floor(remain / 3600000)
  const m = Math.floor((remain % 3600000) / 60000)
  const datetime = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  return t('profile.freeCreditsRules.countdown.active', { datetime, hours: h, minutes: m })
})

function applyUser(u: typeof auth.user) {
  if (u) {
    const merged = { ...auth.user, ...u }
    auth.$patch({ user: merged })
    setUserInfoRaw(JSON.stringify(merged))
  }
}

/** 清除个人中心缓存（切换账号或重新进入时用），避免显示上一账号的绑定信息 */
function clearProfileCache() {
  identities.value = []
  identitiesLoadError.value = false
  loginVia.value = getLoginVia()
  displayNameFrom.value = ''
}

async function loadIdentities() {
  if (!auth.isAuthed) {
    identities.value = []
    identitiesLoading.value = false
    identitiesLoadError.value = false
    return
  }
  identitiesLoading.value = true
  identitiesLoadError.value = false
  try {
    const res = await api.auth.getIdentities()
    identities.value = res.items || []
  } catch {
    identities.value = []
    identitiesLoadError.value = true
  } finally {
    identitiesLoading.value = false
  }
}

/** JWT / 登录方式变化时刷新绑定列表（GitHub 登录后 user.id 可能不变，仅靠 id 的 watch 不会拉 identities） */
function refreshBoundIdentitiesAndProfile() {
  if (!auth.isAuthed) {
    clearProfileCache()
    return
  }
  clearProfileCache()
  void loadIdentities()
  void refreshProfileAndNickname()
}

async function saveProfile(mode: 'manual' | 'sync' = 'manual') {
  savingProfile.value = true
  profileSaveError.value = ''
  try {
    const body: { nickname?: string; display_name_from?: string } = {}
    if (mode === 'sync') {
      if (displayNameFrom.value) body.display_name_from = displayNameFrom.value
    } else {
      const manualNickname = profileNickname.value.trim()
      if (manualNickname) {
        body.nickname = manualNickname
        // 手动保存时退出“从绑定账号同步”模式，避免后端优先用 display_name_from 覆盖昵称。
        displayNameFrom.value = ''
      }
    }
    if (!body.nickname && !body.display_name_from) return
    const res = await api.auth.updateProfile(body)
    if (res.user) {
      applyUser(res.user)
      const u = res.user as { username?: string; nickname?: string }
      const displayName = u.username ?? u.nickname ?? profileNickname.value.trim()
      profileNickname.value = displayName
      if (displayName && auth.user) {
        const merged = { ...auth.user, username: displayName, nickname: displayName }
        auth.$patch({ user: merged })
        setUserInfoRaw(JSON.stringify(merged))
      }
    }
    await refreshProfileAndNickname()
  } catch (e: any) {
    profileSaveError.value = e?.message || e?.detail || 'profile.save.failed'
  } finally {
    savingProfile.value = false
  }
}

function handleRechargeSuccess() {
  showRechargeModal.value = false
  // 刷新用户信息以更新积分
  void refreshProfileAndNickname()
}

async function redeemCdk() {
  redeemCdkError.value = ''
  redeemCdkSuccess.value = ''
  const code = redeemCdkInput.value.trim()
  if (!code) {
    redeemCdkError.value = 'profile.redeemCdk.empty'
    return
  }
  redeemingCdk.value = true
  try {
    const res = await api.credits.redeemCDK({ code })
    redeemCdkSuccess.value = res.message || t('profile.redeemCdk.success', { points: res.points_awarded })
    redeemCdkInput.value = ''
    await refreshProfileAndNickname()
  } catch (e: any) {
    redeemCdkError.value = e?.message || 'profile.redeemCdk.failed'
  } finally {
    redeemingCdk.value = false
  }
}

function onDisplayNameFromChange() {
  if (displayNameFrom.value) saveProfile('sync')
}

async function fetchBindCaptcha() {
  try {
    const res = await api.auth.getCaptcha()
    bindCaptchaImage.value = res.image
    bindCaptchaId.value = res.captcha_id
    bindCaptchaInput.value = ''
  } catch (e: any) {
    console.error(e)
  }
}

watch([bindPhoneOpen, bindEmailOpen], ([phone, email]) => {
  if (phone || email) {
    if (!bindCaptchaImage.value) fetchBindCaptcha()
    bindCodeSuccess.value = ''
    bindCodeError.value = ''
  }
})

async function sendPhoneCode() {
  bindCodeError.value = ''
  bindCodeSuccess.value = ''
  if (!bindPhoneNumber.value.trim()) return
    if (!/^1[3-9]\d{9}$/.test(bindPhoneNumber.value.trim())) {
    bindCodeError.value = 'authModal.invalidMainlandPhone'
    return
  }
  if (!bindCaptchaId.value || !bindCaptchaInput.value.trim()) {
    bindCodeError.value = 'authModal.inputGraphicCaptchaFirst'
    return
  }
  sendingPhoneCode.value = true
  try {
    const res = await api.auth.sendPhoneCode(bindPhoneNumber.value.trim(), bindCaptchaId.value, bindCaptchaInput.value.trim())
    bindCodeSuccess.value = (res as { message?: string })?.message || 'authModal.codeSent'
  } catch (e: any) {
    const msg = e?.message || 'authModal.sendFailed'
    bindCodeError.value = msg
    if (
      msg.includes('图形验证码') ||
      msg.includes('验证码错误') ||
      msg.includes('请先获取') ||
      msg.includes('过期') ||
      msg.toLowerCase().includes('captcha')
    )
      fetchBindCaptcha()
  } finally {
    sendingPhoneCode.value = false
  }
}

async function sendEmailCode() {
  bindCodeError.value = ''
  bindCodeSuccess.value = ''
  if (!bindEmailAddr.value.trim()) return
  if (!bindCaptchaId.value || !bindCaptchaInput.value.trim()) {
    bindCodeError.value = 'authModal.inputGraphicCaptchaFirst'
    return
  }
  sendingEmailCode.value = true
  try {
    const res = await api.auth.sendEmailCode(bindEmailAddr.value.trim(), bindCaptchaId.value, bindCaptchaInput.value.trim())
    bindCodeSuccess.value = (res as { message?: string })?.message || 'authModal.codeSentToEmail'
  } catch (e: any) {
    const msg = e?.message || 'authModal.sendFailed'
    bindCodeError.value = msg
    if (
      msg.includes('图形验证码') ||
      msg.includes('验证码错误') ||
      msg.includes('请先获取') ||
      msg.includes('过期') ||
      msg.toLowerCase().includes('captcha')
    )
      fetchBindCaptcha()
  } finally {
    sendingEmailCode.value = false
  }
}

async function bindPhone() {
  if (!bindPhoneNumber.value.trim() || !bindPhoneCode.value.trim()) return
  bindCodeError.value = ''
  bindCodeSuccess.value = ''
  bindingPhone.value = true
  try {
    const res = await api.auth.bindPhone({
      phone: bindPhoneNumber.value.trim(),
      phone_code: bindPhoneCode.value.trim(),
      use_other_nickname: bindUseOtherNickname.value
    })
    if (res.user) applyUser(res.user)
    loadIdentities()
    bindPhoneOpen.value = false
    bindPhoneNumber.value = ''
    bindPhoneCode.value = ''
  } catch (e: any) {
    bindCodeError.value = e?.message || 'profile.errors.bindFailed'
  } finally {
    bindingPhone.value = false
  }
}

async function bindAccount() {
  bindAccountError.value = ''
  const u = bindAccountUsername.value.trim()
  const p = bindAccountPassword.value
  if (!u || !p) {
    bindAccountError.value = 'authModal.fillAccountPassword'
    return
  }
  bindingAccount.value = true
  try {
    const res = await api.auth.bindAccount({
      username: u,
      password: p,
      use_other_nickname: bindUseOtherNickname.value
    })
    if (res.user) applyUser(res.user)
    loadIdentities()
    bindAccountOpen.value = false
    bindAccountUsername.value = ''
    bindAccountPassword.value = ''
  } catch (e: any) {
    bindAccountError.value = e?.message || 'profile.errors.bindFailed'
  } finally {
    bindingAccount.value = false
  }
}

async function bindEmail() {
  if (!bindEmailAddr.value.trim() || !bindEmailCode.value.trim()) return
  bindCodeError.value = ''
  bindCodeSuccess.value = ''
  bindingEmail.value = true
  try {
    const res = await api.auth.bindEmail({
      email: bindEmailAddr.value.trim(),
      email_code: bindEmailCode.value.trim(),
      use_other_nickname: bindUseOtherNickname.value
    })
    if (res.user) applyUser(res.user)
    loadIdentities()
    bindEmailOpen.value = false
    bindEmailAddr.value = ''
    bindEmailCode.value = ''
  } catch (e: any) {
    bindCodeError.value = e?.message || 'profile.errors.bindFailed'
  } finally {
    bindingEmail.value = false
  }
}

async function fetchUnbindCaptcha() {
  try {
    const res = await api.auth.getCaptcha()
    unbindCaptchaImage.value = res.image
    unbindCaptchaId.value = res.captcha_id
    unbindCaptchaInput.value = ''
  } catch (e: any) {
    unbindModalError.value = e?.message || 'authModal.graphicCaptchaFetchFailed'
  }
}

function openUnbindModal(type: 'phone' | 'email') {
  unbindModal.value = type
  unbindModalError.value = ''
  unbindCodeInput.value = ''
  unbindCaptchaImage.value = ''
  unbindCaptchaId.value = ''
  unbindCaptchaInput.value = ''
  fetchUnbindCaptcha()
}

async function sendUnbindCode() {
  unbindModalError.value = ''
  if (!unbindCaptchaId.value || !unbindCaptchaInput.value.trim()) {
    unbindModalError.value = 'authModal.inputGraphicCaptchaFirst'
    return
  }
  sendingUnbindCode.value = true
  try {
    if (unbindModal.value === 'phone') {
      await api.auth.sendUnbindPhoneCode({ captcha_id: unbindCaptchaId.value, captcha_code: unbindCaptchaInput.value.trim() })
    } else {
      await api.auth.sendUnbindEmailCode({ captcha_id: unbindCaptchaId.value, captcha_code: unbindCaptchaInput.value.trim() })
    }
    unbindModalError.value = ''
  } catch (e: any) {
    unbindModalError.value = e?.message || 'authModal.sendFailed'
    fetchUnbindCaptcha()
  } finally {
    sendingUnbindCode.value = false
  }
}

async function confirmUnbind() {
  if (!unbindModal.value || !unbindCodeInput.value.trim()) return
  unbindModalError.value = ''
  if (unbindModal.value === 'phone') {
    unbindingPhone.value = true
    try {
      const res = await api.auth.unbindPhone({ phone_code: unbindCodeInput.value.trim() })
      if (res.user) applyUser(res.user)
      loadIdentities()
      unbindModal.value = null
    } catch (e: any) {
      unbindModalError.value = e?.message || 'profile.errors.unbindFailed'
    } finally {
      unbindingPhone.value = false
    }
  } else {
    unbindingEmail.value = true
    try {
      const res = await api.auth.unbindEmail({ email_code: unbindCodeInput.value.trim() })
      if (res.user) applyUser(res.user)
      loadIdentities()
      unbindModal.value = null
    } catch (e: any) {
      unbindModalError.value = e?.message || 'profile.errors.unbindFailed'
    } finally {
      unbindingEmail.value = false
    }
  }
}

async function unbindAccount() {
  unbindingAccount.value = true
  try {
    const res = await api.auth.unbindAccount()
    if (res.user) applyUser(res.user)
    loadIdentities()
  } catch (e: any) {
    bindAccountError.value = e?.message || 'profile.errors.unbindFailed'
  } finally {
    unbindingAccount.value = false
  }
}

async function unbindWechat() {
  bindCodeError.value = ''
  unbindingWechat.value = true
  try {
    const res = await api.auth.unbindWechat()
    if (res.user) applyUser(res.user)
    loadIdentities()
  } catch (e: any) {
    bindCodeError.value = e?.message || 'profile.errors.unbindFailed'
  } finally {
    unbindingWechat.value = false
  }
}

async function unbindGitHub() {
  bindCodeError.value = ''
  unbindingGitHub.value = true
  try {
    const res = await api.auth.unbindGitHub()
    if (res.user) applyUser(res.user)
    loadIdentities()
  } catch (e: any) {
    bindCodeError.value = e?.message || 'profile.errors.unbindFailed'
  } finally {
    unbindingGitHub.value = false
  }
}

function initAuthUrls() {
  const base = window.location.origin + (window.location.pathname || '/')
  const wechatRedirect = base + (base.includes('?') ? '&' : '?') + 'bind=wechat'
  const githubRedirect = base + (base.includes('?') ? '&' : '?') + 'bind=github'
  api.auth.getWechatAuthUrl(wechatRedirect).then((r) => { wechatAuthUrl.value = r.url || '#' }).catch(() => { wechatAuthUrl.value = '#' })
  api.auth.getGitHubAuthUrl(githubRedirect).then((r) => { githubAuthUrl.value = r.url || '#' }).catch(() => { githubAuthUrl.value = '#' })
}

function openGitHubBindWindow() {
  if (!githubAuthUrl.value || githubAuthUrl.value === '#') return
  try {
    stashGithubOAuthRedirectUriFromAuthorizeUrl(githubAuthUrl.value, 'popup')
    const urlParams = new URL(githubAuthUrl.value).searchParams
    const state = urlParams.get('state')
    if (state) setGithubOAuthStateForBindPopup(state)
  } catch (e) {
    // Ignore URL parsing errors
  }
  window.open(githubAuthUrl.value, '_blank', 'noopener,noreferrer')
}

async function handleBindCallback(): Promise<void> {
  const params = new URLSearchParams(window.location.search)
  const bind = params.get('bind')
  const code = params.get('code')
  if (!bind || !code) return
  if (bind === 'wechat') {
    await api.auth.bindWechat({ code, use_other_nickname: bindUseOtherNickname.value }).then((res) => {
      if (res.user) applyUser(res.user)
      loadIdentities()
      window.history.replaceState({}, '', window.location.pathname || '/')
    }).catch((e: any) => { bindCodeError.value = e?.message || 'profile.errors.bindFailed' })
  }
  // GitHub 绑定回调必须由 App.vue 统一处理（见 App.vue onMounted：bind=github 分支）。
  // 此处若再 bind-github，会与 App 并发两次换票：stash 的 redirect_uri 仅够一次，第二次必失败或 code 已用尽。
}

async function refreshProfileAndNickname() {
  try {
    const profile = await api.user.getProfile()
    if (profile && auth.user) {
      const merged = { ...auth.user, ...profile }
      auth.$patch({ user: merged })
      setUserInfoRaw(JSON.stringify(merged))
    }
    profileNickname.value = auth.user?.username ?? auth.user?.nickname ?? ''
  } catch {
    // 忽略
  }
}

onMounted(async () => {
  clearProfileCache()
  if (auth.isAuthed) {
    loadIdentities()
    initAuthUrls()
    await handleBindCallback()
    await refreshProfileAndNickname()
    
    // 检查是否是充值成功返回
    const urlParams = new URLSearchParams(window.location.search)
    if (urlParams.get('recharge_success') === '1') {
      // 显示充值成功提示
      setTimeout(() => {
        alert(t('profile.rechargeSuccess'))
        // 清除URL参数
        window.history.replaceState({}, '', '/profile')
      }, 500)
    }
    
    profileNickname.value = auth.user?.username ?? auth.user?.nickname ?? ''
  }
  const onGitHubBound = () => {
    loadIdentities()
    refreshProfileAndNickname()
  }
  const onAuthSessionChanged = () => {
    refreshBoundIdentitiesAndProfile()
  }
  window.addEventListener('github-bound', onGitHubBound)
  window.addEventListener('auth-session-changed', onAuthSessionChanged)
  const onVisibilityChange = () => {
    if (document.visibilityState === 'visible' && auth.isAuthed) {
      loadIdentities()
      refreshProfileAndNickname()
    }
  }
  document.addEventListener('visibilitychange', onVisibilityChange)
  onUnmounted(() => {
    window.removeEventListener('github-bound', onGitHubBound)
    window.removeEventListener('auth-session-changed', onAuthSessionChanged)
    document.removeEventListener('visibilitychange', onVisibilityChange)
  })
})

// 登录身份变化时（退出后换账号/邮箱等再登录）：清除缓存并重新拉取，避免仍显示上一账号的绑定信息
watch(
  () => auth.user?.id,
  (newId, oldId) => {
    if (newId !== oldId && auth.isAuthed) {
      refreshBoundIdentitiesAndProfile()
    }
  }
)

// JWT 变化时（同 user.id 下从账号改 GitHub 登录等）必须重拉 identities
watch(
  () => auth.token,
  (newTok, oldTok) => {
    if (newTok === oldTok) return
    if (!newTok) {
      clearProfileCache()
      identitiesLoading.value = false
      return
    }
    if (auth.isAuthed) {
      refreshBoundIdentitiesAndProfile()
    }
  }
)

watch(() => auth.user?.username, (v) => { profileNickname.value = v || '' })
</script>

