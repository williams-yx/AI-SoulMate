<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../lib/api'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'success'): void
}>()

const amount = ref<number | null>(null)
const paymentMethod = ref<'alipay' | 'stripe'>('alipay')
const loading = ref(false)
const rechargeTiers = ref<any[]>([])

const { t, locale } = useI18n()

// 计算赠送积分
const bonusInfo = computed(() => {
  if (!amount.value || amount.value <= 0) return null
  
  // 赠送策略：
  // - 100以下：不送
  // - 100-500：不送
  // - 500-1000：5%
  // - 1000-5000：10%
  // - 5000-10000：15%
  // - 10000以上：20%
  let bonusRate = 0
  
  if (amount.value < 100) {
    bonusRate = 0
  } else if (amount.value < 500) {
    bonusRate = 0
  } else if (amount.value < 1000) {
    bonusRate = 5
  } else if (amount.value < 5000) {
    bonusRate = 10
  } else if (amount.value < 10000) {
    bonusRate = 15
  } else {  // >= 10000
    bonusRate = 20
  }
  
  const bonusAmount = Math.floor(amount.value * bonusRate / 100)
  const totalAmount = amount.value + bonusAmount
  
  return {
    bonusAmount,
    totalAmount,
    bonusRate,
    description: bonusRate > 0 ? `赠送${bonusRate}%` : '无赠送'
  }
})

const isValid = computed(() => {
  return amount.value && amount.value > 0 && amount.value <= 100000
})

// 计算积分对应的人民币金额
function calculateAmountYuan(credits: number): number {
  // 从第一个档位获取汇率，如果没有档位则使用默认值
  if (rechargeTiers.value.length > 0) {
    const firstTier = rechargeTiers.value[0]
    const rate = firstTier.amount_yuan / firstTier.min_amount
    return credits * rate
  }
  // 默认汇率 1积分 = 0.1元
  return credits * 0.1
}

// 加载充值档位
async function loadRechargeTiers() {
  try {
    rechargeTiers.value = await api.credits.getRechargeTiers()
  } catch (error: any) {
    console.error('加载充值档位失败:', error)
  }
}

// 选择档位
function selectTier(minAmount: number) {
  amount.value = minAmount
}

// 页面加载时获取充值档位
onMounted(() => {
  loadRechargeTiers()
})

async function handleRecharge() {
  if (!isValid.value) return
  
  loading.value = true
  try {
    // 创建充值订单
    const res = await api.credits.recharge({
      amount: amount.value!,
      payment_method: paymentMethod.value,
      return_url: window.location.origin
    })
    
    if (res.payment_url) {
      // 跳转到支付页面
      window.location.href = res.payment_url
    } else if (res.message) {
      alert(res.message)
    }
  } catch (error: any) {
    const errorMsg = error.message || t('recharge.rechargeFailed')
    
    // 如果是认证错误，提示重新登录
    if (errorMsg.includes('authentication') || errorMsg.includes('认证') || errorMsg.includes('登录')) {
      alert(t('recharge.authExpired'))
      emit('close')
      // 页面会自动跳转到登录页面（由 api.ts 中的 401 处理）
    } else {
      alert(errorMsg)
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" @click.self="emit('close')">
    <div class="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-white/10 bg-slate-900 p-4 sm:p-6 shadow-2xl">
      <!-- 头部 -->
      <div class="flex items-center justify-between mb-4 sm:mb-6">
        <h2 class="text-xl sm:text-2xl font-bold text-white">{{ t('recharge.title') }}</h2>
        <button
          type="button"
          @click="emit('close')"
          class="text-slate-400 hover:text-white transition-colors"
        >
          <svg class="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 充值档位选择 -->
      <div class="mb-4 sm:mb-6">
        <label class="block text-sm font-medium text-slate-300 mb-2">{{ t('recharge.chooseTier') }}</label>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            v-for="tier in rechargeTiers"
            :key="tier.id"
            type="button"
            @click="selectTier(tier.min_amount)"
            class="flex flex-col items-start p-3 sm:p-4 rounded-lg border transition-colors"
            :class="amount === tier.min_amount
              ? 'border-indigo-500 bg-indigo-500/20 text-white'
              : 'border-white/10 bg-slate-800 text-slate-300 hover:border-indigo-500/50'"
          >
            <div class="text-base sm:text-lg font-bold">
              {{ tier.min_amount }}
              <span v-if="tier.bonus_rate > 0 || tier.bonus_fixed > 0" class="text-green-400">
                +{{ Math.floor(tier.min_amount * tier.bonus_rate / 100) + tier.bonus_fixed }}
              </span>
              积分
            </div>
            <div class="text-xs text-slate-400 mt-1">¥{{ tier.amount_yuan.toFixed(2) }}</div>
            <div v-if="tier.bonus_rate > 0 || tier.bonus_fixed > 0" class="text-xs text-green-400 mt-1">
              赠送{{ tier.bonus_rate > 0 ? tier.bonus_rate + '%' : '' }}{{ tier.bonus_fixed > 0 ? (tier.bonus_rate > 0 ? '+' : '') + tier.bonus_fixed : '' }}
            </div>
          </button>
        </div>
      </div>

      <!-- 自定义充值金额 -->
      <div class="mb-4 sm:mb-6">
        <label class="block text-sm font-medium text-slate-300 mb-2">自定义充值</label>
        <div class="flex items-center gap-3">
          <input
            v-model.number="amount"
            type="number"
            min="1"
            max="100000"
            placeholder="请输入积分数量（1-100000）"
            class="flex-1 px-4 py-3 rounded-lg border border-white/10 bg-slate-800 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
          />
          <span class="text-slate-400 text-sm">积分</span>
        </div>
        <p v-if="amount && amount > 0 && amount >= 1 && amount <= 100000" class="mt-2 text-sm">
          <span class="text-indigo-400">需支付: ¥{{ calculateAmountYuan(amount).toFixed(2) }}</span>
          <span v-if="bonusInfo" class="text-green-400 ml-2">
            将获得: {{ bonusInfo.totalAmount }} 积分
            (含赠送 {{ bonusInfo.bonusAmount }} 积分)
          </span>
        </p>
        <p v-if="amount && (amount < 1 || amount > 100000)" class="mt-2 text-sm text-red-400">
          充值金额必须在 1-100000 积分之间
        </p>
      </div>

      <!-- 支付方式 -->
      <div class="mb-4 sm:mb-6">
        <label class="block text-sm font-medium text-slate-300 mb-2">{{ t('recharge.paymentMethod') }}</label>
        <div class="grid grid-cols-1 gap-3">
          <button
            type="button"
            @click="paymentMethod = 'alipay'"
            class="flex items-center justify-center gap-2 px-4 py-3 rounded-lg border transition-colors"
            :class="paymentMethod === 'alipay'
              ? 'border-indigo-500 bg-indigo-500/20 text-white'
              : 'border-white/10 bg-slate-800 text-slate-300 hover:border-indigo-500/50'"
          >
            <span class="text-lg">💳</span>
            <span>{{ t('recharge.alipay') }}</span>
          </button>
          <!-- 暂时注释掉 Stripe 支付方式 -->
          <!-- <button
            type="button"
            @click="paymentMethod = 'stripe'"
            class="flex items-center justify-center gap-2 px-4 py-3 rounded-lg border transition-colors"
            :class="paymentMethod === 'stripe'
              ? 'border-indigo-500 bg-indigo-500/20 text-white'
              : 'border-white/10 bg-slate-800 text-slate-300 hover:border-indigo-500/50'"
          >
            <span class="text-lg">💳</span>
            <span>Stripe</span>
          </button> -->
        </div>
      </div>

      <!-- 充值按钮 -->
      <button
        type="button"
        @click="handleRecharge"
        :disabled="!isValid || loading"
        class="w-full py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {{ loading ? t('recharge.processing') : t('recharge.rechargeNow') }}
      </button>

      <!-- 说明 -->
      <div class="mt-4 text-xs text-slate-400 space-y-1">
        <p>{{ t('recharge.note1') }}</p>
        <p>{{ t('recharge.note2') }}</p>
        <p>{{ t('recharge.note3') }}</p>
        <p>{{ t('recharge.note4') }}</p>
      </div>
    </div>
  </div>
</template>
