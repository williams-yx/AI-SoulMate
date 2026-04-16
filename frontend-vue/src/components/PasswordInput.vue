<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

declare const lucide: any

const model = defineModel<string>({ default: '' })

withDefaults(
  defineProps<{
    placeholder?: string
    required?: boolean
    /** HTML autocomplete，如 current-password / new-password */
    autocomplete?: string
    /** 输入框 class（须含宽度与右侧留白，如 pr-10） */
    inputClass?: string
  }>(),
  {
    autocomplete: 'current-password',
    inputClass: 'input-dark text-xs pr-10'
  }
)

const { t } = useI18n()
const visible = ref(false)

function paintIcons() {
  nextTick(() => {
    if (typeof lucide !== 'undefined' && lucide?.createIcons) {
      lucide.createIcons()
    }
  })
}

function toggle() {
  visible.value = !visible.value
  paintIcons()
}

watch(visible, () => paintIcons())
onMounted(() => paintIcons())
</script>

<template>
  <div class="relative w-full">
    <input
      v-model="model"
      :type="visible ? 'text' : 'password'"
      :placeholder="placeholder"
      :required="required"
      :autocomplete="autocomplete"
      :class="inputClass"
    />
    <button
      type="button"
      class="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/60"
      :title="visible ? t('authModal.hidePassword') : t('authModal.showPassword')"
      :aria-label="visible ? t('authModal.hidePassword') : t('authModal.showPassword')"
      :aria-pressed="visible"
      @click="toggle"
    >
      <i v-if="!visible" data-lucide="eye" class="w-4 h-4 pointer-events-none" />
      <i v-else data-lucide="eye-off" class="w-4 h-4 pointer-events-none" />
    </button>
  </div>
</template>
