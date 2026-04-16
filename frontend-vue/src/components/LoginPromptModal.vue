<template>
  <Teleport to="body">
    <Transition name="login-prompt">
      <div
        v-if="open"
        class="login-prompt-overlay"
        @click.self="handleLater"
      >
        <div class="login-prompt-panel">
          <div class="login-prompt-icon-wrap">
            <i data-lucide="log-in" class="login-prompt-icon"></i>
          </div>
          <h3 class="login-prompt-title">{{ t('loginPrompt.title') }}</h3>
          <p class="login-prompt-message">{{ message }}</p>
          <div class="login-prompt-actions">
            <button
              class="login-prompt-btn login-prompt-btn-secondary"
              type="button"
              @click="handleLater"
            >
              {{ t('loginPrompt.later') }}
            </button>
            <button
              class="login-prompt-btn login-prompt-btn-primary"
              type="button"
              @click="handleGoLogin"
            >
              {{ t('loginPrompt.goLogin') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

declare const lucide: { createIcons?: () => void } | undefined

const props = defineProps<{
  open: boolean
  message: string
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'goLogin'): void
}>()

const router = useRouter()
const { t } = useI18n()

function handleGoLogin() {
  emit('update:open', false)
  emit('goLogin')
  router.push('/profile')
}

function handleLater() {
  emit('update:open', false)
}

// ESC 关闭
let escHandler: ((e: KeyboardEvent) => void) | null = null

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      escHandler = (e: KeyboardEvent) => {
        if (e.key === 'Escape') handleLater()
      }
      document.addEventListener('keydown', escHandler)
      await nextTick()
      if (typeof lucide !== 'undefined' && lucide?.createIcons) lucide.createIcons()
    } else {
      if (escHandler) {
        document.removeEventListener('keydown', escHandler)
        escHandler = null
      }
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.login-prompt-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.login-prompt-panel {
  width: 100%;
  max-width: 22rem;
  background: linear-gradient(145deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05);
}

.login-prompt-icon-wrap {
  width: 3rem;
  height: 3rem;
  margin: 0 auto 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(99, 102, 241, 0.2);
  border: 1px solid rgba(99, 102, 241, 0.4);
  border-radius: 50%;
}

.login-prompt-icon {
  width: 1.5rem;
  height: 1.5rem;
  color: #a5b4fc;
}

.login-prompt-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #f1f5f9;
  text-align: center;
  margin-bottom: 0.5rem;
}

.login-prompt-message {
  font-size: 0.875rem;
  color: #94a3b8;
  text-align: center;
  margin-bottom: 1.5rem;
  line-height: 1.5;
}

.login-prompt-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}

.login-prompt-btn {
  flex: 1 1 0;
  min-width: 0;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.login-prompt-btn-secondary {
  background: rgba(51, 65, 85, 0.8);
  border: 1px solid rgba(100, 116, 139, 0.5);
  color: #cbd5e1;
}

.login-prompt-btn-secondary:hover {
  background: rgba(71, 85, 105, 0.9);
  border-color: rgba(148, 163, 184, 0.5);
  color: #f1f5f9;
}

.login-prompt-btn-primary {
  background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%);
  border: 1px solid rgba(129, 140, 248, 0.5);
  color: #fff;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.login-prompt-btn-primary:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}

/* 过渡动画 */
.login-prompt-enter-active,
.login-prompt-leave-active {
  transition: opacity 0.2s ease;
}

.login-prompt-enter-active .login-prompt-panel,
.login-prompt-leave-active .login-prompt-panel {
  transition: transform 0.2s ease;
}

.login-prompt-enter-from,
.login-prompt-leave-to {
  opacity: 0;
}

.login-prompt-enter-from .login-prompt-panel,
.login-prompt-leave-to .login-prompt-panel {
  transform: scale(0.96);
}
</style>
