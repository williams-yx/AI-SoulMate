<template>
  <div v-if="open" class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm p-4 flex items-center justify-center" @click.self="emit('close')">
    <div class="glass-panel max-w-lg w-full mx-auto rounded-2xl p-6 border border-slate-700 shadow-2xl relative max-h-[90vh] overflow-y-auto">
      <!-- 关闭按钮 -->
      <button class="absolute right-4 top-4 text-slate-400 hover:text-white" @click="emit('close')">
        <i data-lucide="x" class="w-4 h-4"></i>
      </button>

      <!-- 头部：图标 + 标题 -->
      <div class="flex items-center gap-3 mb-6">
        <div class="w-9 h-9 rounded-xl bg-indigo-500/20 flex items-center justify-center border border-indigo-500/40">
          <i data-lucide="shield" class="w-5 h-5 text-indigo-400"></i>
        </div>
        <div>
          <h2 class="text-xl font-bold text-white">{{ tab === 'login' ? t('authModal.welcomeBack') : t('authModal.createAccountTitle') }}</h2>
          <p class="text-xs text-slate-400 mt-1">
            {{ tab === 'login' ? t('authModal.loginSubtitle') : t('authModal.registerSubtitle') }}
          </p>
        </div>
      </div>

      <!-- 登录 -->
      <div v-if="tab==='login'" class="mt-4 space-y-4 text-sm">
        <!-- 登录方式 Tab：中文 手机→邮箱→账号；英文仅 邮箱→账号 -->
        <div class="flex mb-4 rounded-lg bg-slate-900/60 p-1 border border-slate-700 text-xs font-medium">
          <button
            v-for="kind in loginTypeOrder"
            :key="'login-tab-' + kind"
            type="button"
            class="flex-1 py-2 rounded-lg"
            :class="loginType === kind ? activeTabCls2 : idleTabCls2"
            @click="loginType = kind"
          >
            {{ loginTabLabel(kind) }}
          </button>
        </div>

        <!-- 账号登录 -->
        <form v-if="loginType==='account'" class="space-y-3" @submit.prevent="doLoginAccount">
          <input v-model="loginAccount.username" type="text" class="input-dark text-xs" :placeholder="t('authModal.accountPlaceholder')" required />
          <PasswordInput
            v-model="loginAccount.password"
            :placeholder="t('authModal.passwordPlaceholder')"
            required
            autocomplete="current-password"
          />
          <div class="flex gap-2 items-stretch">
            <input
              v-model="loginAccount.code"
              type="text"
              class="flex-1 input-dark text-xs"
              :placeholder="t('authModal.captchaPlaceholder')"
              maxlength="6"
              autocomplete="off"
            />
            <img
              v-if="captchaImage"
              :src="captchaImage"
              :alt="t('authModal.captchaAlt')"
              class="w-[140px] h-[2.75rem] rounded-lg border border-slate-600 bg-slate-800 object-contain cursor-pointer shrink-0"
              :title="t('authModal.captchaRefreshTitle')"
              @click="fetchCaptcha"
            />
          </div>
          <div class="flex items-start gap-2">
            <input
              id="auth-terms-login"
              v-model="termsAccepted"
              type="checkbox"
              class="mt-0.5 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500 shrink-0"
            />
            <div class="text-xs text-slate-300 leading-snug">
              <label for="auth-terms-login" class="cursor-pointer">{{ t('authModal.termsCheckboxBeforeLink') }}</label>
              <button
                type="button"
                class="text-indigo-300 hover:text-indigo-200 underline underline-offset-2 mx-0.5 align-baseline"
                @click.stop="openTermsDetail"
              >
                {{ t('authModal.termsLinkText') }}
              </button>
              <label for="auth-terms-login" class="cursor-pointer">{{ t('authModal.termsCheckboxAfterLink') }}</label>
            </div>
          </div>
          <button
            type="submit"
            :disabled="!termsAccepted"
            class="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i data-lucide="log-in" class="w-4 h-4"></i>
            <span>{{ t('authModal.loginButton') }}</span>
          </button>
        </form>

        <!-- 手机号登录 -->
        <form v-else-if="loginType==='phone'" class="space-y-3" @submit.prevent="doLoginPhone">
          <input v-model="loginPhone.phone" type="tel" class="w-full input-dark text-xs" :placeholder="t('authModal.phonePlaceholder')" />
          <p class="text-xs text-slate-500">{{ t('authModal.mainlandOnly') }}</p>
          <div class="flex gap-2 items-stretch">
            <input v-model="sendCodeCaptchaInput" type="text" class="flex-1 input-dark text-xs" :placeholder="t('authModal.graphicCaptcha')" maxlength="6" autocomplete="off" />
            <img v-if="sendCodeCaptchaImage" :src="sendCodeCaptchaImage" :alt="t('authModal.captchaAlt')" class="w-[100px] h-[2.75rem] rounded-lg border border-slate-600 bg-slate-800 object-contain cursor-pointer shrink-0" :title="t('authModal.captchaClickRefresh')" @click="fetchSendCodeCaptcha" />
          </div>
          <div class="flex rounded-lg border border-slate-600 bg-slate-900/80 overflow-hidden items-stretch min-h-[2.75rem]">
            <input
              v-model="loginPhone.code"
              type="text"
              class="flex-1 min-w-0 border-0 bg-transparent px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-0"
              :placeholder="t('authModal.smsCodePlaceholder')"
              maxlength="12"
              autocomplete="one-time-code"
            />
            <div class="w-px shrink-0 bg-slate-600 self-stretch my-2" aria-hidden="true" />
            <button
              type="button"
              :disabled="!termsAccepted"
              class="shrink-0 px-3 py-2 text-xs font-medium text-indigo-400 hover:text-indigo-300 hover:bg-slate-800/60 whitespace-nowrap transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent"
              @click="sendPhoneCode('login')"
            >
              {{ t('authModal.sendCode') }}
            </button>
          </div>
          <div class="flex items-start gap-2">
            <input
              id="auth-terms-login-phone"
              v-model="termsAccepted"
              type="checkbox"
              class="mt-0.5 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500 shrink-0"
            />
            <div class="text-xs text-slate-300 leading-snug">
              <label for="auth-terms-login-phone" class="cursor-pointer">{{ t('authModal.termsCheckboxBeforeLink') }}</label>
              <button
                type="button"
                class="text-indigo-300 hover:text-indigo-200 underline underline-offset-2 mx-0.5 align-baseline"
                @click.stop="openTermsDetail"
              >
                {{ t('authModal.termsLinkText') }}
              </button>
              <label for="auth-terms-login-phone" class="cursor-pointer">{{ t('authModal.termsCheckboxAfterLink') }}</label>
            </div>
          </div>
          <button
            type="submit"
            :disabled="!termsAccepted"
            class="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i data-lucide="log-in" class="w-4 h-4"></i>
            <span>{{ t('authModal.phoneLoginButton') }}</span>
          </button>
        </form>

        <!-- 邮箱登录 -->
        <form v-else class="space-y-3" @submit.prevent="doLoginEmail">
          <input v-model="loginEmail.email" type="email" class="w-full input-dark text-xs" :placeholder="t('authModal.emailPlaceholder')" />
          <div class="flex gap-2 items-stretch">
            <input v-model="sendCodeCaptchaInput" type="text" class="flex-1 input-dark text-xs" :placeholder="t('authModal.graphicCaptcha')" maxlength="6" autocomplete="off" />
            <img v-if="sendCodeCaptchaImage" :src="sendCodeCaptchaImage" :alt="t('authModal.captchaAlt')" class="w-[100px] h-[2.75rem] rounded-lg border border-slate-600 bg-slate-800 object-contain cursor-pointer shrink-0" :title="t('authModal.captchaClickRefresh')" @click="fetchSendCodeCaptcha" />
          </div>
          <div class="flex rounded-lg border border-slate-600 bg-slate-900/80 overflow-hidden items-stretch min-h-[2.75rem]">
            <input
              v-model="loginEmail.code"
              type="text"
              class="flex-1 min-w-0 border-0 bg-transparent px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-0"
              :placeholder="t('authModal.emailCodePlaceholder')"
              maxlength="12"
              autocomplete="one-time-code"
            />
            <div class="w-px shrink-0 bg-slate-600 self-stretch my-2" aria-hidden="true" />
            <button
              type="button"
              :disabled="!termsAccepted"
              class="shrink-0 px-3 py-2 text-xs font-medium text-indigo-400 hover:text-indigo-300 hover:bg-slate-800/60 whitespace-nowrap transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent"
              @click="sendEmailCode('login')"
            >
              {{ t('authModal.sendCode') }}
            </button>
          </div>
          <div class="flex items-start gap-2">
            <input
              id="auth-terms-login-email"
              v-model="termsAccepted"
              type="checkbox"
              class="mt-0.5 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500 shrink-0"
            />
            <div class="text-xs text-slate-300 leading-snug">
              <label for="auth-terms-login-email" class="cursor-pointer">{{ t('authModal.termsCheckboxBeforeLink') }}</label>
              <button
                type="button"
                class="text-indigo-300 hover:text-indigo-200 underline underline-offset-2 mx-0.5 align-baseline"
                @click.stop="openTermsDetail"
              >
                {{ t('authModal.termsLinkText') }}
              </button>
              <label for="auth-terms-login-email" class="cursor-pointer">{{ t('authModal.termsCheckboxAfterLink') }}</label>
            </div>
          </div>
          <button
            type="submit"
            :disabled="!termsAccepted"
            class="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i data-lucide="log-in" class="w-4 h-4"></i>
            <span>{{ t('authModal.emailLoginButton') }}</span>
          </button>
        </form>

        <div class="mt-4 text-xs text-slate-500 flex items-center justify-between gap-2">
          <span>{{ t('authModal.avatarHint') }}</span>
        </div>
        <div class="mt-4">
          <p class="text-xs text-slate-500 mb-2">{{ t('authModal.orUseOther') }}</p>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <button
              type="button"
              class="flex items-center justify-center gap-2 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 disabled:opacity-50"
              :disabled="githubLoading || !termsAccepted"
              @click="doGitHubLogin"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" class="w-4 h-4 fill-current">
                <path d="M12 2C6.48 2 2 6.58 2 12.23c0 4.52 2.87 8.35 6.84 9.7.5.1.68-.22.68-.49 0-.24-.01-1.05-.01-1.9-2.78.62-3.37-1.2-3.37-1.2-.46-1.18-1.12-1.5-1.12-1.5-.92-.64.07-.63.07-.63 1.01.08 1.55 1.06 1.55 1.06.9 1.57 2.37 1.12 2.95.86.09-.67.35-1.12.64-1.38-2.22-.26-4.56-1.14-4.56-5.07 0-1.12.39-2.04 1.03-2.75-.1-.26-.45-1.31.1-2.73 0 0 .84-.27 2.75 1.05A9.35 9.35 0 0 1 12 6.84c.85 0 1.7.12 2.5.36 1.9-1.32 2.74-1.05 2.74-1.05.56 1.42.21 2.47.1 2.73.64.71 1.03 1.63 1.03 2.75 0 3.94-2.34 4.8-4.57 5.06.36.32.67.94.67 1.9 0 1.38-.01 2.5-.01 2.84 0 .27.18.6.69.49A10.25 10.25 0 0 0 22 12.23C22 6.58 17.52 2 12 2z" />
              </svg>
              <span>{{ githubLoading ? t('authModal.githubLoading') : t('authModal.githubLogin') }}</span>
            </button>
            <button
              type="button"
              class="flex items-center justify-center gap-2 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 disabled:opacity-50"
              :disabled="wechatLoading || !termsAccepted"
              @click="openWechatQr"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" class="w-4 h-4 fill-current">
                <path d="M9.8 5.3C5.5 5.3 2 8.1 2 11.6c0 2.1 1.2 4 3.1 5.2l-.8 2.5 2.8-1.4c.9.2 1.8.3 2.7.3 4.3 0 7.8-2.8 7.8-6.3S14.1 5.3 9.8 5.3zm-3 5a.9.9 0 1 1 0-1.8.9.9 0 0 1 0 1.8zm6 0a.9.9 0 1 1 0-1.8.9.9 0 0 1 0 1.8zM22 16.4c0-2.9-2.8-5.3-6.2-5.3h-.2c.3.7.5 1.4.5 2.1 0 4-3.8 7.2-8.4 7.2h-.2c1.1 1.8 3.3 3 5.9 3 .8 0 1.6-.1 2.3-.3l2.4 1.2-.7-2.2c1.6-1 2.6-2.5 2.6-4.2zm-7.7.3a.8.8 0 1 1 0-1.6.8.8 0 0 1 0 1.6zm4.3 0a.8.8 0 1 1 0-1.6.8.8 0 0 1 0 1.6z"/>
              </svg>
              <span>{{ wechatLoading ? t('authModal.wechatOpening') : t('authModal.wechatLogin') }}</span>
            </button>
          </div>
        </div>
        <p class="mt-4 text-xs text-slate-400 text-center">
          {{ t('authModal.noAccountYet') }}
          <button type="button" class="text-indigo-300 hover:text-indigo-200 underline underline-offset-2" @click="tab='register'">{{ t('authModal.createAccountLink') }}</button>
        </p>
      </div>

      <!-- 微信扫码弹窗：内嵌二维码页 -->
      <div
        v-if="wechatQrOpen"
        class="fixed inset-0 z-[60] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
        @click.self="closeWechatQr"
      >
        <div class="bg-[#0f172a] rounded-2xl border border-slate-700 shadow-2xl overflow-hidden max-w-[360px] w-full">
          <div class="flex items-center justify-between px-4 py-3 border-b border-slate-700">
            <span class="text-white font-medium">{{ t('authModal.wechatScanTitle') }}</span>
            <button type="button" class="text-slate-400 hover:text-white p-1" @click="closeWechatQr">
              <i data-lucide="x" class="w-5 h-5"></i>
            </button>
          </div>
          <div class="aspect-square w-full bg-white min-h-[320px] flex items-center justify-center">
            <iframe
              v-if="wechatQrUrl"
              :src="wechatQrUrl"
              class="w-full h-full min-h-[320px] border-0"
              :title="t('authModal.wechatScanIframeTitle')"
            />
            <p v-else class="text-slate-500 text-sm">{{ t('authModal.loading') }}</p>
          </div>
          <p class="text-xs text-slate-400 px-4 py-3 text-center">{{ t('authModal.wechatScanHint') }}</p>
        </div>
      </div>

      <!-- 注册 -->
      <div v-if="tab==='register'" class="mt-4 space-y-4 text-sm">
        <div class="flex mb-4 rounded-lg bg-slate-900/60 p-1 border border-slate-700 text-xs font-medium">
          <button
            v-for="kind in registerTypeOrder"
            :key="'reg-tab-' + kind"
            type="button"
            class="flex-1 py-2 rounded-lg"
            :class="registerType === kind ? activeTabCls2 : idleTabCls2"
            @click="registerType = kind"
          >
            {{ registerTabLabel(kind) }}
          </button>
        </div>

        <form v-if="registerType==='account'" class="space-y-3" @submit.prevent="doRegister">
          <input v-model="reg.username" type="text" class="input-dark text-xs" :placeholder="t('authModal.registerUsernamePlaceholder')" />
          <PasswordInput
            v-model="reg.password"
            :placeholder="t('authModal.registerPasswordPlaceholder')"
            autocomplete="new-password"
          />
          <PasswordInput
            v-model="reg.password2"
            :placeholder="t('authModal.registerPasswordConfirmPlaceholder')"
            autocomplete="new-password"
          />
          <p class="text-[11px] text-slate-400 -mt-1">
            {{ t('authModal.registerPasswordHint') }}
          </p>

          <div class="border-t border-slate-700 pt-3 mt-3">
            <p class="text-xs text-slate-400 mb-3">{{ t('authModal.optionalBinding') }}</p>
            <div class="flex gap-2 items-stretch mb-2">
              <input v-model="sendCodeCaptchaInput" type="text" class="flex-1 input-dark text-xs" :placeholder="t('authModal.bindingCaptchaPlaceholder')" maxlength="6" autocomplete="off" />
              <img v-if="sendCodeCaptchaImage" :src="sendCodeCaptchaImage" :alt="t('authModal.captchaAlt')" class="w-[100px] h-[2.75rem] rounded-lg border border-slate-600 bg-slate-800 object-contain cursor-pointer shrink-0" :title="t('authModal.captchaClickRefresh')" @click="fetchSendCodeCaptcha" />
            </div>
            <div v-if="showPhoneAuth" class="space-y-2 mb-3">
              <input v-model="reg.phone" type="tel" class="w-full input-dark text-xs" :placeholder="t('authModal.optionalPhonePlaceholder')" />
              <div class="flex rounded-lg border border-slate-600 bg-slate-900/80 overflow-hidden items-stretch min-h-[2.75rem]">
                <input
                  v-model="reg.phoneCode"
                  type="text"
                  class="flex-1 min-w-0 border-0 bg-transparent px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-0"
                  :placeholder="t('authModal.optionalPhoneCodePlaceholder')"
                  maxlength="12"
                  autocomplete="one-time-code"
                />
                <div class="w-px shrink-0 bg-slate-600 self-stretch my-2" aria-hidden="true" />
                <button
                  type="button"
                  :disabled="!termsAccepted"
                  class="shrink-0 px-3 py-2 text-xs font-medium text-indigo-400 hover:text-indigo-300 hover:bg-slate-800/60 whitespace-nowrap transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent"
                  @click="sendPhoneCode('register')"
                >
                  {{ t('authModal.sendCode') }}
                </button>
              </div>
            </div>
            <div class="space-y-2 mb-3">
              <input v-model="reg.email" type="email" class="w-full input-dark text-xs" :placeholder="t('authModal.optionalEmailPlaceholder')" />
              <div class="flex rounded-lg border border-slate-600 bg-slate-900/80 overflow-hidden items-stretch min-h-[2.75rem]">
                <input
                  v-model="reg.emailCode"
                  type="text"
                  class="flex-1 min-w-0 border-0 bg-transparent px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-0"
                  :placeholder="t('authModal.optionalEmailCodePlaceholder')"
                  maxlength="12"
                  autocomplete="one-time-code"
                />
                <div class="w-px shrink-0 bg-slate-600 self-stretch my-2" aria-hidden="true" />
                <button
                  type="button"
                  :disabled="!termsAccepted"
                  class="shrink-0 px-3 py-2 text-xs font-medium text-indigo-400 hover:text-indigo-300 hover:bg-slate-800/60 whitespace-nowrap transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent"
                  @click="sendEmailCode('register')"
                >
                  {{ t('authModal.sendCode') }}
                </button>
              </div>
            </div>
          </div>

          <div class="flex items-start gap-2">
            <input
              id="auth-terms-reg-account"
              v-model="termsAccepted"
              type="checkbox"
              class="mt-0.5 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500 shrink-0"
            />
            <div class="text-xs text-slate-300 leading-snug">
              <label for="auth-terms-reg-account" class="cursor-pointer">{{ t('authModal.termsCheckboxBeforeLink') }}</label>
              <button
                type="button"
                class="text-indigo-300 hover:text-indigo-200 underline underline-offset-2 mx-0.5 align-baseline"
                @click.stop="openTermsDetail"
              >
                {{ t('authModal.termsLinkText') }}
              </button>
              <label for="auth-terms-reg-account" class="cursor-pointer">{{ t('authModal.termsCheckboxAfterLink') }}</label>
            </div>
          </div>
          <button
            type="submit"
            :disabled="!termsAccepted"
            class="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i data-lucide="user-plus" class="w-4 h-4"></i>
            <span>{{ t('authModal.registerAndLogin') }}</span>
          </button>
        </form>

        <form v-else-if="registerType==='phone'" class="space-y-3" @submit.prevent="doRegister">
          <p class="text-xs text-slate-400 -mt-1">{{ t('authModal.registerPhoneIntro') }}</p>
          <input v-model="reg.phone" type="tel" class="w-full input-dark text-xs" :placeholder="t('authModal.registerPhonePlaceholderRequired')" />
          <p class="text-xs text-slate-500">{{ t('authModal.mainlandOnly') }}</p>
          <div class="flex gap-2 items-stretch">
            <input v-model="sendCodeCaptchaInput" type="text" class="flex-1 input-dark text-xs" :placeholder="t('authModal.graphicCaptcha')" maxlength="6" autocomplete="off" />
            <img v-if="sendCodeCaptchaImage" :src="sendCodeCaptchaImage" :alt="t('authModal.captchaAlt')" class="w-[100px] h-[2.75rem] rounded-lg border border-slate-600 bg-slate-800 object-contain cursor-pointer shrink-0" :title="t('authModal.captchaClickRefresh')" @click="fetchSendCodeCaptcha" />
          </div>
          <div class="flex rounded-lg border border-slate-600 bg-slate-900/80 overflow-hidden items-stretch min-h-[2.75rem]">
            <input
              v-model="reg.phoneCode"
              type="text"
              class="flex-1 min-w-0 border-0 bg-transparent px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-0"
              :placeholder="t('authModal.registerPhoneCodeRequired')"
              maxlength="12"
              autocomplete="one-time-code"
            />
            <div class="w-px shrink-0 bg-slate-600 self-stretch my-2" aria-hidden="true" />
            <button
              type="button"
              :disabled="!termsAccepted"
              class="shrink-0 px-3 py-2 text-xs font-medium text-indigo-400 hover:text-indigo-300 hover:bg-slate-800/60 whitespace-nowrap transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent"
              @click="sendPhoneCode('register')"
            >
              {{ t('authModal.sendCode') }}
            </button>
          </div>
          <div class="flex items-start gap-2">
            <input
              id="auth-terms-reg-phone"
              v-model="termsAccepted"
              type="checkbox"
              class="mt-0.5 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500 shrink-0"
            />
            <div class="text-xs text-slate-300 leading-snug">
              <label for="auth-terms-reg-phone" class="cursor-pointer">{{ t('authModal.termsCheckboxBeforeLink') }}</label>
              <button
                type="button"
                class="text-indigo-300 hover:text-indigo-200 underline underline-offset-2 mx-0.5 align-baseline"
                @click.stop="openTermsDetail"
              >
                {{ t('authModal.termsLinkText') }}
              </button>
              <label for="auth-terms-reg-phone" class="cursor-pointer">{{ t('authModal.termsCheckboxAfterLink') }}</label>
            </div>
          </div>
          <button
            type="submit"
            :disabled="!termsAccepted"
            class="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i data-lucide="user-plus" class="w-4 h-4"></i>
            <span>{{ t('authModal.registerPhoneSubmit') }}</span>
          </button>
        </form>

        <form v-else class="space-y-3" @submit.prevent="doRegister">
          <p class="text-xs text-slate-400 -mt-1">{{ t('authModal.registerEmailIntro') }}</p>
          <input v-model="reg.email" type="email" class="w-full input-dark text-xs" :placeholder="t('authModal.registerEmailPlaceholderRequired')" />
          <div class="flex gap-2 items-stretch">
            <input v-model="sendCodeCaptchaInput" type="text" class="flex-1 input-dark text-xs" :placeholder="t('authModal.graphicCaptcha')" maxlength="6" autocomplete="off" />
            <img v-if="sendCodeCaptchaImage" :src="sendCodeCaptchaImage" :alt="t('authModal.captchaAlt')" class="w-[100px] h-[2.75rem] rounded-lg border border-slate-600 bg-slate-800 object-contain cursor-pointer shrink-0" :title="t('authModal.captchaClickRefresh')" @click="fetchSendCodeCaptcha" />
          </div>
          <div class="flex rounded-lg border border-slate-600 bg-slate-900/80 overflow-hidden items-stretch min-h-[2.75rem]">
            <input
              v-model="reg.emailCode"
              type="text"
              class="flex-1 min-w-0 border-0 bg-transparent px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-0"
              :placeholder="t('authModal.registerEmailCodeRequired')"
              maxlength="12"
              autocomplete="one-time-code"
            />
            <div class="w-px shrink-0 bg-slate-600 self-stretch my-2" aria-hidden="true" />
            <button
              type="button"
              :disabled="!termsAccepted"
              class="shrink-0 px-3 py-2 text-xs font-medium text-indigo-400 hover:text-indigo-300 hover:bg-slate-800/60 whitespace-nowrap transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent"
              @click="sendEmailCode('register')"
            >
              {{ t('authModal.sendCode') }}
            </button>
          </div>
          <div class="flex items-start gap-2">
            <input
              id="auth-terms-reg-email"
              v-model="termsAccepted"
              type="checkbox"
              class="mt-0.5 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500 shrink-0"
            />
            <div class="text-xs text-slate-300 leading-snug">
              <label for="auth-terms-reg-email" class="cursor-pointer">{{ t('authModal.termsCheckboxBeforeLink') }}</label>
              <button
                type="button"
                class="text-indigo-300 hover:text-indigo-200 underline underline-offset-2 mx-0.5 align-baseline"
                @click.stop="openTermsDetail"
              >
                {{ t('authModal.termsLinkText') }}
              </button>
              <label for="auth-terms-reg-email" class="cursor-pointer">{{ t('authModal.termsCheckboxAfterLink') }}</label>
            </div>
          </div>
          <button
            type="submit"
            :disabled="!termsAccepted"
            class="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i data-lucide="user-plus" class="w-4 h-4"></i>
            <span>{{ t('authModal.registerEmailSubmit') }}</span>
          </button>
        </form>

        <p class="text-[11px] text-slate-500 leading-relaxed">
          {{ t('authModal.registerAgreement') }}
        </p>
        <p class="text-xs text-slate-400 text-center">
          {{ t('authModal.haveAccount') }}
          <button type="button" class="text-indigo-300 hover:text-indigo-200 underline underline-offset-2" @click="tab='login'">{{ t('authModal.loginNow') }}</button>
        </p>
      </div>

      <div v-if="msg" class="mt-4 text-sm" :class="msgType==='error' ? 'text-red-300' : 'text-emerald-300'">{{ msg }}</div>
      <div v-if="captchaCountdownDisplay" class="mt-3 text-sm text-amber-400">
        {{ t('authModal.captchaLocked', { time: captchaCountdownDisplay }) }}
      </div>
    </div>
  </div>

  <UserAgreementModal v-if="open && termsDetailOpen" v-model="termsDetailOpen" />
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import PasswordInput from './PasswordInput.vue'
import UserAgreementModal from './UserAgreementModal.vue'
import { api } from '../lib/api'
import { useAuthStore } from '../stores/auth'
import { setToken, setUserInfoRaw } from '../lib/storage'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ (e: 'close'): void }>()

declare const lucide: any

const { t, locale } = useI18n()
const auth = useAuthStore()

type AuthMethod = 'account' | 'phone' | 'email'

/** 大陆中文：含手机号登录/注册；英文模式：隐藏手机号相关入口 */
const showPhoneAuth = computed(() => locale.value === 'zh-CN')

const loginTypeOrder = computed((): AuthMethod[] =>
  showPhoneAuth.value ? ['phone', 'email', 'account'] : ['email', 'account']
)

const registerTypeOrder = computed((): AuthMethod[] =>
  showPhoneAuth.value ? ['phone', 'email', 'account'] : ['email', 'account']
)

function loginTabLabel(kind: AuthMethod): string {
  if (kind === 'account') return t('authModal.loginTypeAccount')
  if (kind === 'phone') return t('authModal.loginTypePhone')
  return t('authModal.loginTypeEmail')
}

function registerTabLabel(kind: AuthMethod): string {
  if (kind === 'account') return t('authModal.registerTypeAccount')
  if (kind === 'phone') return t('authModal.registerTypePhone')
  return t('authModal.registerTypeEmail')
}

function defaultLoginType(): AuthMethod {
  return locale.value === 'zh-CN' ? 'phone' : 'email'
}

function defaultRegisterType(): AuthMethod {
  return locale.value === 'zh-CN' ? 'phone' : 'email'
}

const tab = ref<'login' | 'register'>('login')
const loginType = ref<AuthMethod>('account')
const registerType = ref<AuthMethod>('account')
/** 登录/注册均须勾选：同意用户协议（切换 Tab 或重新打开弹窗会重置） */
const termsAccepted = ref(false)
/** 用户协议全文弹层（仅点击「用户协议」打开，主界面不展示细则） */
const termsDetailOpen = ref(false)

const msg = ref('')
const msgType = ref<'ok' | 'error'>('ok')
const captchaLockedUntilUtc = ref<string | null>(null)
const captchaCountdownDisplay = ref('')
let captchaLockTimer: ReturnType<typeof setInterval> | null = null

const activeTabCls2 = 'bg-slate-800 text-white'
const idleTabCls2 = 'bg-transparent text-slate-400'

const loginAccount = ref({ username: '', password: '', code: '' })
const captchaImage = ref('')
const captchaId = ref('')
const sendCodeCaptchaImage = ref('')
const sendCodeCaptchaId = ref('')
const sendCodeCaptchaInput = ref('')
const loginPhone = ref({ phone: '', code: '' })
const loginEmail = ref({ email: '', code: '' })
const loginPhoneOneTimeToken = ref('')
const loginEmailOneTimeToken = ref('')
const loginAccountOneTimeToken = ref('')

const reg = ref({
  username: '',
  password: '',
  password2: '',
  phone: '',
  phoneCode: '',
  email: '',
  emailCode: ''
})

const githubLoading = ref(false)
const wechatLoading = ref(false)
const wechatQrOpen = ref(false)
const wechatQrUrl = ref('')

function handleWechatMessage(e: MessageEvent) {
  if (e.origin !== window.location.origin || e.data?.type !== 'wechat-login-success') return
  const { access_token, user } = e.data
  if (access_token) {
    setToken(access_token)
    if (user) setUserInfoRaw(JSON.stringify(user))
    auth.hydrate()
    closeWechatQr()
    emit('close')
  }
}

function resetGithubLoadingIfStale(e: PageTransitionEvent) {
  // 从 GitHub 返回时若走 BFCache，内存里的 githubLoading 可能仍为 true；跳转前也会先置 false
  if (e.persisted) githubLoading.value = false
}

onMounted(() => {
  window.addEventListener('message', handleWechatMessage)
  window.addEventListener('pageshow', resetGithubLoadingIfStale)
})
onUnmounted(() => {
  window.removeEventListener('message', handleWechatMessage)
  window.removeEventListener('pageshow', resetGithubLoadingIfStale)
  clearCaptchaLockCountdown()
})

async function openWechatQr() {
  if (!assertTermsAccepted()) return
  // 微信登录尚未正式开放，暂时只给用户一个提示，不真正发起登录流程
  toastErr(t('authModal.wechatNotAvailable'))
  return
}

function closeWechatQr() {
  wechatQrOpen.value = false
  wechatQrUrl.value = ''
}

async function doGitHubLogin() {
  if (!assertTermsAccepted()) return
  try {
    githubLoading.value = true
    const redirectUri = window.location.origin + '/'
    const res = await api.auth.getGitHubAuthUrl(redirectUri)
    const ghOAuth = await import('../lib/githubOAuth')
    if (res.url) {
      ghOAuth.stashGithubOAuthRedirectUriFromAuthorizeUrl(res.url, 'same-tab')
    }
    if (res.state) {
      ghOAuth.setGithubOAuthStateForSameTabLogin(res.state)
    }
    // 跳转前复位，避免用户从 GitHub 返回时 BFCache 恢复页面仍卡在「跳转中…」
    githubLoading.value = false
    window.location.href = res.url
  } catch (e: any) {
    githubLoading.value = false
    toastErr(e?.message || t('authModal.githubAuthUrlFailed'))
  }
}

function renderIcons() {
  if (typeof lucide !== 'undefined' && lucide?.createIcons) {
    lucide.createIcons()
  }
}

function openTermsDetail() {
  termsDetailOpen.value = true
  void nextTick(() => {
    setTimeout(renderIcons, 0)
  })
}

watch(
  () => props.open,
  (v) => {
    if (v) {
      // 每次打开弹窗都回到默认登录页，避免停留在上次关闭时的注册态
      tab.value = 'login'
      loginType.value = defaultLoginType()
      registerType.value = defaultRegisterType()
      termsAccepted.value = false
      setTimeout(renderIcons, 0)
      // 每次打开弹窗且为账号登录时都拉新验证码，避免退出再登录时仍显示旧图、后端已失效导致报错
      if (loginType.value === 'account') fetchCaptcha()
    }
  },
  { immediate: true }
)

watch(locale, () => {
  if (locale.value !== 'zh-CN') {
    if (loginType.value === 'phone') loginType.value = 'email'
    if (registerType.value === 'phone') registerType.value = 'email'
  }
})

watch(tab, () => {
  termsAccepted.value = false
  termsDetailOpen.value = false
})
watch(
  () => [props.open, loginType.value],
  ([open, type], [prevOpen, prevType]) => {
    // 仅在「已打开且切到账号登录」时拉验证码，避免与 watch(open) 重复请求
    const justOpened = open && prevOpen === false
    if (open && type === 'account' && !justOpened) fetchCaptcha()
  }
)
// 进入注册页或切换注册方式时换一张图形验证码并清空输入（与 fetchSendCodeCaptcha 内逻辑一致）
watch(
  () => [props.open, tab.value, registerType.value],
  ([open, currentTab]) => {
    if (!open || currentTab !== 'register') return
    fetchSendCodeCaptcha()
  }
)

// 每次关闭登录/注册弹窗时清空底部提示；打开时清除账号登录的缓存凭证，避免用过期/他人 OTT 导致「请先完成图形验证」误报
// 打开时同时清空手机/邮箱登录与注册中的短信、邮箱验证码及 OTT，避免无操作登出后再点开仍显示上一次的验证码
watch(() => props.open, (open) => {
  if (!open) {
    msg.value = ''
    msgType.value = 'ok'
    termsDetailOpen.value = false
    clearCaptchaLockCountdown()
  } else {
    loginAccountOneTimeToken.value = ''
    loginPhone.value.code = ''
    loginEmail.value.code = ''
    loginPhoneOneTimeToken.value = ''
    loginEmailOneTimeToken.value = ''
    reg.value.phoneCode = ''
    reg.value.emailCode = ''
    refreshCaptchaLockState()
  }
})
// 用户名变化时清除账号登录凭证，否则会拿旧用户的 OTT 去登录当前用户
watch(() => loginAccount.value.username, () => {
  loginAccountOneTimeToken.value = ''
})

function formatLockCountdown(untilUtc: string): string {
  const until = new Date(untilUtc).getTime()
  const now = Date.now()
  const sec = Math.max(0, Math.floor((until - now) / 1000))
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function clearCaptchaLockCountdown() {
  captchaLockedUntilUtc.value = null
  captchaCountdownDisplay.value = ''
  if (captchaLockTimer !== null) {
    clearInterval(captchaLockTimer)
    captchaLockTimer = null
  }
}

function tickCaptchaLockCountdown() {
  if (!captchaLockedUntilUtc.value) return
  const until = new Date(captchaLockedUntilUtc.value).getTime()
  const now = Date.now()
  if (until <= now) {
    clearCaptchaLockCountdown()
    return
  }
  captchaCountdownDisplay.value = formatLockCountdown(captchaLockedUntilUtc.value)
}

function startCaptchaLockCountdown(untilUtc: string) {
  captchaLockedUntilUtc.value = untilUtc
  tickCaptchaLockCountdown()
  if (captchaLockTimer !== null) clearInterval(captchaLockTimer)
  captchaLockTimer = setInterval(tickCaptchaLockCountdown, 1000)
}

async function refreshCaptchaLockState() {
  try {
    const res = await api.auth.getCaptchaLockState()
    if (res.locked && res.locked_until_utc) startCaptchaLockCountdown(res.locked_until_utc)
    else clearCaptchaLockCountdown()
  } catch {
    clearCaptchaLockCountdown()
  }
}

function onCaptchaLockError() {
  refreshCaptchaLockState()
}

function toastOk(text: string) {
  msgType.value = 'ok'
  msg.value = text
}
function toastErr(text: string) {
  msgType.value = 'error'
  msg.value = text
}

function assertTermsAccepted(): boolean {
  if (!termsAccepted.value) {
    toastErr(t('authModal.mustAcceptTerms'))
    return false
  }
  return true
}

function buildAutoRegisterCredential(kind: 'phone' | 'email', identifier: string) {
  const seed = Math.random().toString(36).slice(2, 8)
  const suffix = Date.now().toString(36).slice(-6)
  const compact = identifier.replace(/[^a-zA-Z0-9]/g, '').slice(-6) || 'user'
  const username = `${kind}_${compact}_${suffix}`
  // 满足后端密码复杂度（>=6 且至少 3 类字符）
  const password = `Ai${seed}!9`
  return { username, password }
}

async function fetchCaptcha() {
  try {
    const res = await api.auth.getCaptcha()
    const img = res?.image
    const cid = res?.captcha_id
    if (!img || !cid || typeof img !== 'string' || !img.startsWith('data:image')) {
      toastErr(t('authModal.captchaDataInvalidWithProxy'))
      return
    }
    captchaImage.value = img
    captchaId.value = cid
    loginAccount.value.code = ''
  } catch (e: any) {
    const raw = e?.message || ''
    toastErr(raw || t('authModal.captchaFetchFailed'))
    if (raw.includes('15分钟')) onCaptchaLockError()
  }
}

/** 发码接口失败且与图形验证码相关时再换新图（成功发码后不刷新，避免清空用户已填内容） */
function shouldRefreshSendCodeCaptchaAfterError(msg: string): boolean {
  if (!msg) return false
  if (msg.includes('15分钟')) return false
  const low = msg.toLowerCase()
  if (msg.includes('图形验证码')) return true
  if (msg.includes('验证码错误')) return true
  if (msg.includes('请先获取')) return true
  if (msg.includes('过期')) return true
  if (low.includes('captcha')) return true
  return false
}

async function fetchSendCodeCaptcha() {
  try {
    const res = await api.auth.getCaptcha()
    const img = res?.image
    const cid = res?.captcha_id
    if (!img || !cid || typeof img !== 'string' || !img.startsWith('data:image')) {
      toastErr(t('authModal.captchaDataInvalid'))
      return
    }
    sendCodeCaptchaImage.value = img
    sendCodeCaptchaId.value = cid
    sendCodeCaptchaInput.value = ''
  } catch (e: any) {
    const raw = e?.message || ''
    toastErr(raw || t('authModal.graphicCaptchaFetchFailed'))
    if (raw.includes('15分钟')) onCaptchaLockError()
  }
}

// 发码用图形验证码：登录「手机 / 邮箱」与注册共用一套 ref。切换登录方式、从注册回到登录、从账号切到手机/邮箱时须换新图并清空输入，避免串值。
watch(
  () => [props.open, tab.value, loginType.value] as const,
  (now, prev) => {
    const [open, t, lt] = now
    if (!open || t !== 'login') return
    if (lt !== 'phone' && lt !== 'email') return
    if (!prev) {
      if (!sendCodeCaptchaImage.value) void fetchSendCodeCaptcha()
      return
    }
    const [, pTab, pLt] = prev
    if (!sendCodeCaptchaImage.value) {
      void fetchSendCodeCaptcha()
      return
    }
    const needFresh =
      pTab === 'register' ||
      ((pLt === 'phone' || pLt === 'email') && (lt === 'phone' || lt === 'email') && pLt !== lt) ||
      (pLt === 'account' && (lt === 'phone' || lt === 'email'))
    if (needFresh) void fetchSendCodeCaptcha()
  }
)

async function sendPhoneCode(scene: 'login' | 'register') {
  if (!assertTermsAccepted()) return
  const phone = scene === 'login' ? loginPhone.value.phone : reg.value.phone
  if (!/^1[3-9]\d{9}$/.test(phone)) return toastErr(t('authModal.invalidMainlandPhone'))
  if (!sendCodeCaptchaId.value || !sendCodeCaptchaInput.value.trim()) return toastErr(t('authModal.inputGraphicCaptchaFirst'))
  try {
    const res = await api.auth.sendPhoneCode(phone, sendCodeCaptchaId.value, sendCodeCaptchaInput.value.trim(), scene)
    if (res.one_time_token) loginPhoneOneTimeToken.value = res.one_time_token
    toastOk(res.message || t('authModal.codeSent'))
  } catch (e: any) {
    const errMsg = e?.message || t('authModal.sendFailed')
    toastErr(errMsg)
    if (errMsg.includes('15分钟')) onCaptchaLockError()
    else if (shouldRefreshSendCodeCaptchaAfterError(errMsg)) void fetchSendCodeCaptcha()
  }
}

async function sendEmailCode(scene: 'login' | 'register') {
  if (!assertTermsAccepted()) return
  const email = scene === 'login' ? loginEmail.value.email : reg.value.email
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return toastErr(t('authModal.invalidEmail'))
  if (!sendCodeCaptchaId.value || !sendCodeCaptchaInput.value.trim()) return toastErr(t('authModal.inputGraphicCaptchaFirst'))
  try {
    const res = await api.auth.sendEmailCode(email, sendCodeCaptchaId.value, sendCodeCaptchaInput.value.trim(), scene)
    if (res.one_time_token) loginEmailOneTimeToken.value = res.one_time_token
    toastOk(res.message || t('authModal.codeSentToEmail'))
  } catch (e: any) {
    const errMsg = e?.message || t('authModal.sendFailed')
    toastErr(errMsg)
    if (errMsg.includes('15分钟')) onCaptchaLockError()
    else if (shouldRefreshSendCodeCaptchaAfterError(errMsg)) void fetchSendCodeCaptcha()
  }
}

async function doLoginAccount() {
  if (!assertTermsAccepted()) return
  const u = loginAccount.value.username.trim()
  const p = loginAccount.value.password.trim()
  const c = loginAccount.value.code.trim()
  if (!u || !p) return toastErr(t('authModal.fillAccountPassword'))
  if (!captchaId.value) return toastErr(t('authModal.clickGetCaptchaFirst'))
  if (!c) return toastErr(t('authModal.inputGraphicCaptcha'))
  try {
    const ott = loginAccountOneTimeToken.value || (await api.auth.loginAccountRequest(u, captchaId.value, c)).one_time_token
    if (!loginAccountOneTimeToken.value) loginAccountOneTimeToken.value = ott
    const result = await auth.loginWithOTT({ username: u, password: p, one_time_token: ott })
    if (result.success) {
      toastOk(t('authModal.loginSuccess'))
      emit('close')
      return
    }
    if (result.one_time_token) loginAccountOneTimeToken.value = result.one_time_token
    toastErr(result.detail || t('authModal.loginFailed'))
  } catch (e: any) {
    const errMsg = e?.message || t('authModal.loginFailed')
    toastErr(errMsg)
    if (errMsg.includes('15分钟')) onCaptchaLockError()
    else if (errMsg.includes('图形验证码')) fetchCaptcha()
  }
}

async function doLoginPhone() {
  if (!assertTermsAccepted()) return
  const phone = loginPhone.value.phone.trim()
  const code = loginPhone.value.code.trim()
  if (!phone || !code) return toastErr(t('authModal.fillPhoneCode'))
  if (!loginPhoneOneTimeToken.value) return toastErr(t('authModal.sendCodeFirstForLogin'))
  const result = await auth.loginWithOTT({ phone, phone_code: code, one_time_token: loginPhoneOneTimeToken.value })
  if (result.success) {
    toastOk(t('authModal.loginSuccess'))
    emit('close')
    return
  }
  if (result.one_time_token) loginPhoneOneTimeToken.value = result.one_time_token
  toastErr(result.detail || t('authModal.loginFailed'))
}

async function doLoginEmail() {
  if (!assertTermsAccepted()) return
  const email = loginEmail.value.email.trim()
  const code = loginEmail.value.code.trim()
  if (!email || !code) return toastErr(t('authModal.fillEmailCode'))
  if (!loginEmailOneTimeToken.value) return toastErr(t('authModal.sendCodeFirstForLogin'))
  const result = await auth.loginWithOTT({ email, email_code: code, one_time_token: loginEmailOneTimeToken.value })
  if (result.success) {
    toastOk(t('authModal.loginSuccess'))
    emit('close')
    return
  }
  if (result.one_time_token) loginEmailOneTimeToken.value = result.one_time_token
  toastErr(result.detail || t('authModal.loginFailed'))
}

async function doRegister() {
  if (!assertTermsAccepted()) return
  try {
    let u = reg.value.username.trim()
    let p1 = reg.value.password.trim()
    // 兼容“只填用户名+密码就想注册”的习惯：确认密码不填时默认等于密码
    let p2 = (reg.value.password2.trim() || p1).trim()

    if (registerType.value === 'account') {
      if (!u || !p1) return toastErr(t('authModal.fillUsernamePassword'))
      if (p1.length < 6) return toastErr(t('authModal.passwordTooShort'))
      if (p1 !== p2) return toastErr(t('authModal.passwordMismatch'))
    } else if (registerType.value === 'phone') {
      if (!reg.value.phone.trim()) return toastErr(t('authModal.registerFillPhone'))
      if (!reg.value.phoneCode.trim()) return toastErr(t('authModal.registerFillPhoneSms'))
      const auto = buildAutoRegisterCredential('phone', reg.value.phone.trim())
      u = auto.username
      p1 = auto.password
      p2 = auto.password
    } else {
      if (!reg.value.email.trim()) return toastErr(t('authModal.registerFillEmail'))
      if (!reg.value.emailCode.trim()) return toastErr(t('authModal.registerFillEmailVerification'))
      const auto = buildAutoRegisterCredential('email', reg.value.email.trim())
      u = auto.username
      p1 = auto.password
      p2 = auto.password
    }

    const payload: any = { username: u, password: p1, password_confirm: p2, register_via: registerType.value }
    if (registerType.value === 'phone') {
      if (!reg.value.phone.trim()) return toastErr(t('authModal.registerFillPhone'))
      if (!reg.value.phoneCode.trim()) return toastErr(t('authModal.registerFillPhoneSms'))
      payload.phone = reg.value.phone.trim()
      payload.phone_code = reg.value.phoneCode.trim()
    } else if (registerType.value === 'email') {
      if (!reg.value.email.trim()) return toastErr(t('authModal.registerFillEmail'))
      if (!reg.value.emailCode.trim()) return toastErr(t('authModal.registerFillEmailVerification'))
      payload.email = reg.value.email.trim()
      payload.email_code = reg.value.emailCode.trim()
    } else {
      if (reg.value.phone.trim()) {
        if (!reg.value.phoneCode.trim()) return toastErr('填写手机号后需要手机验证码')
        payload.phone = reg.value.phone.trim()
        payload.phone_code = reg.value.phoneCode.trim()
      }
      if (reg.value.email.trim()) {
        if (!reg.value.emailCode.trim()) return toastErr('填写邮箱后需要邮箱验证码')
        payload.email = reg.value.email.trim()
        payload.email_code = reg.value.emailCode.trim()
      }
    }

    await auth.register(payload)
    toastOk(t('authModal.registerSuccess'))
    emit('close')
  } catch (e: any) {
    toastErr(e?.message || t('authModal.registerFailed'))
  }
}
</script>

<style scoped>
/* 使用全局的 .input-dark 样式，不再在这里定义 */
</style>

