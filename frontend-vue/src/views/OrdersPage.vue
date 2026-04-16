<template>
  <div class="space-y-4 sm:space-y-6">
    <div class="flex items-center justify-between gap-4 flex-wrap">
      <div class="text-xl sm:text-2xl font-bold">{{ t('orders.title') }}</div>
      <RouterLink to="/market" class="btn-secondary text-sm sm:text-base">{{ t('orders.toMarket') }}</RouterLink>
    </div>

    <!-- 筛选器 -->
    <div class="flex gap-2 overflow-x-auto pb-2">
      <button
        v-for="filter in filters"
        :key="filter.value"
        @click="currentFilter = filter.value"
        class="px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors"
        :class="currentFilter === filter.value
          ? 'bg-indigo-600 text-white'
          : 'bg-slate-800 text-slate-300 hover:bg-slate-700'"
      >
        {{ filter.label }}
      </button>
    </div>

    <section class="panel p-4 sm:p-6">
      <div v-if="loading" class="text-slate-400">{{ t('orders.loading') }}</div>
      <div v-else-if="err" class="text-red-300">{{ err }}</div>
      <div v-else-if="filteredOrders.length === 0" class="text-slate-400">{{ t('orders.empty') }}</div>

      <div v-else class="space-y-3 sm:space-y-4">
        <div v-for="(o, idx) in filteredOrders" :key="o.id">
          <div v-if="idx > 0" class="border-t border-slate-700 mb-3 sm:mb-4"></div>
          <RouterLink
            :to="o.order_type === 'recharge' ? `/recharge-orders/${o.id}` : `/orders/${o.id}`"
            class="block p-3 sm:p-4 rounded-lg transition-all duration-300 cursor-pointer border-2 border-transparent hover:border-indigo-500 hover:shadow-lg hover:shadow-indigo-500/20 hover:scale-[1.01] sm:hover:scale-[1.02]"
            :class="o.order_type === 'recharge' ? 'bg-gradient-to-r from-amber-900/20 to-transparent' : ''"
          >
            <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
              <div class="space-y-2 flex-1">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div class="flex items-center gap-2">
                    <div class="font-bold text-base sm:text-lg text-slate-100">{{ getOrderTitle(o) }}</div>
                    <span v-if="o.order_type === 'recharge'" class="px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-300 border border-amber-500/30">充值</span>
                  </div>
                  <span
                    class="px-2 sm:px-3 py-1 rounded-full text-xs font-bold w-fit"
                    :class="getStatusClass(o.status)"
                  >
                    {{ getStatusText(o.status) }}
                  </span>
                </div>
                <div class="text-xs text-slate-400">{{ t('orders.orderNo', { id: o.id }) }}</div>
                <div class="text-xs text-slate-400">{{ t('orders.createdAt', { time: fmt(o.created_at) }) }}</div>
              </div>
              <div class="flex sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-2 sm:gap-1 sm:text-right">
                <div class="text-emerald-300 font-bold text-base sm:text-lg">¥ {{ Number(o.total_amount).toFixed(2) }}</div>
                <div class="text-xs text-slate-500">{{ getOrderSubtitle(o) }}</div>
              </div>
            </div>
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import { api, type OrderListItem } from '../lib/api'

const router = useRouter()
const { t, locale } = useI18n()
const loading = ref(true)
const err = ref('')
const orders = ref<any[]>([])
const currentFilter = ref('all')

const filters = [
  { value: 'all', label: '全部订单' },
  { value: 'product', label: '商品订单' },
  { value: 'recharge', label: '充值订单' }
]

const filteredOrders = computed(() => {
  if (currentFilter.value === 'all') {
    return orders.value
  } else if (currentFilter.value === 'recharge') {
    return orders.value.filter(o => o.order_type === 'recharge')
  } else {
    return orders.value.filter(o => o.order_type !== 'recharge')
  }
})

function fmt(s: string) {
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return s
  return d.toLocaleString(locale.value === 'zh-CN' ? 'zh-CN' : 'en-US')
}

function getOrderTitle(order: any) {
  if (order.order_type === 'recharge') {
    const bonus = order.bonus_amount || 0
    if (bonus > 0) {
      return `积分充值 ${order.amount}+${bonus}`
    }
    return `积分充值 ${order.amount}`
  }
  
  // 商品订单
  try {
    const items = order.items
    const arr = typeof items === 'string' ? (JSON.parse(items) as any[]) : (items as any[])
    if (!Array.isArray(arr) || arr.length === 0) return t('orders.detailFallback')

    const firstItem = arr[0]
    const productName = firstItem?.product_name || firstItem?.name || t('orders.unknownItem')
    const quantity = Number(firstItem?.quantity || firstItem?.qty || 1)

    if (arr.length === 1) {
      return quantity > 1 ? `${productName} x${quantity}` : productName
    }

    return t('orders.mixedItems', { name: productName, count: arr.length })
  } catch {
    return t('orders.detailFallback')
  }
}

function getOrderSubtitle(order: any) {
  if (order.order_type === 'recharge') {
    const remaining = order.remaining_credits || 0
    const total = order.total_credits || order.amount || 0  // 使用 total_credits 而不是 total_amount
    return `剩余${remaining}/${total}积分`
  }
  
  // 商品订单
  try {
    const items = order.items
    const arr = typeof items === 'string' ? (JSON.parse(items) as any[]) : (items as any[])
    if (!Array.isArray(arr) || arr.length === 0) return ''
    
    const isPrintOrder = arr.some(it => 
      it?.product_type === 'print' || 
      it?.id?.toString().startsWith('print:') ||
      it?.name?.includes('打印') ||
      it?.name?.includes('定制') ||
      it?.product_name?.includes('打印') ||
      it?.product_name?.includes('定制')
    )
    
    const totalCount = arr.reduce((sum, it) => sum + Number(it?.quantity || it?.qty || 1), 0)
    
    return `共${totalCount}${isPrintOrder ? '克' : '件'}`
  } catch {
    return ''
  }
}

function getStatusText(status: string) {
  const statusMap: Record<string, string> = {
    pricing: '切片定价中',
    pricing_failed: '切片定价失败',
    pending: t('orders.statusPending'),
    awaiting_payment: t('orders.statusPending'),
    paid: t('orders.statusPaid'),
    processing: t('orders.statusProcessing'),
    shipped: t('orders.statusShipped'),
    completed: t('orders.statusCompleted'),
    cancelled: t('orders.statusCancelled'),
    refunded: '已退款'
  }
  return statusMap[status] || status
}

function getStatusClass(status: string) {
  const classMap: Record<string, string> = {
    pricing: 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30',
    pricing_failed: 'bg-red-500/20 text-red-300 border border-red-500/30',
    pending: 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30',
    awaiting_payment: 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30',
    paid: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
    processing: 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30',
    shipped: 'bg-purple-500/20 text-purple-300 border border-purple-500/30',
    completed: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
    cancelled: 'bg-slate-500/20 text-slate-400 border border-slate-500/30',
    refunded: 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
  }
  return classMap[status] || 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
}

async function loadOrders() {
  loading.value = true
  err.value = ''
  
  try {
    // 加载商品订单
    const productOrders = await api.orders.list()
    
    // 加载充值订单
    let rechargeOrders: any[] = []
    try {
      const rechargeResult = await api.credits.getRechargeOrders({ page: 1, page_size: 100 })
      rechargeOrders = rechargeResult.orders.map(r => ({
        id: r.id,
        order_type: 'recharge',
        amount: r.amount,
        bonus_amount: r.bonus_amount,
        total_amount: r.amount_yuan,  // 金额（用于显示价格）
        total_credits: r.total_amount,  // 总积分（用于显示积分）
        remaining_credits: r.remaining_credits,
        status: r.status,
        created_at: r.created_at,
        items: []
      }))
    } catch (rechargeError) {
      console.warn('加载充值订单失败，仅显示商品订单:', rechargeError)
    }
    
    // 合并订单并去重（使用 Map 按 id 去重）
    const allOrders = [...productOrders, ...rechargeOrders]
    const orderMap = new Map()
    allOrders.forEach(order => {
      // 如果已存在相同 id 的订单，保留最新的（根据 created_at）
      const existing = orderMap.get(order.id)
      if (!existing || new Date(order.created_at) > new Date(existing.created_at)) {
        orderMap.set(order.id, order)
      }
    })
    
    // 转换为数组并按创建时间排序
    orders.value = Array.from(orderMap.values()).sort((a, b) => {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
  } catch (e: any) {
    err.value = e?.message || t('orders.loadFailed')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // 检测是否从充值支付返回
  const urlParams = new URLSearchParams(window.location.search)
  const orderId = urlParams.get('out_trade_no')
  
  if (orderId) {
    try {
      const rechargeHistory = await api.credits.getRechargeHistory()
      const isRechargeOrder = rechargeHistory.records.some(r => r.id === orderId)
      
      if (isRechargeOrder) {
        router.push('/profile?recharge_success=1')
        return
      }
    } catch (e) {
      console.error('检查充值订单失败:', e)
    }
  }
  
  await loadOrders()
})
</script>

<style scoped>
.panel {
  @apply rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur;
}
.btn-secondary {
  @apply px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 text-sm font-bold disabled:opacity-60 disabled:cursor-not-allowed;
}
.row {
  @apply flex items-center justify-between gap-4 p-6 rounded-xl bg-slate-950/30 border-2;
}
</style>
