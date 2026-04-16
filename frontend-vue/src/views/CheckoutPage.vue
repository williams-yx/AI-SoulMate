<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between gap-4 flex-wrap">
      <div class="text-2xl font-bold">{{ t('checkout.title') }}</div>
      <RouterLink to="/market" class="btn-secondary">{{ t('checkout.backToMarket') }}</RouterLink>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
      <section class="panel p-6">
        <div class="flex items-center justify-between mb-4">
          <div class="font-bold">{{ t('checkout.cart') }}</div>
          <div v-if="cart.items.length > 0" class="flex items-center gap-3">
            <button
              class="text-sm text-indigo-400 hover:text-indigo-300"
              type="button"
              @click="toggleSelectAll"
            >
              {{ allSelected ? t('checkout.unselectAll') : t('checkout.selectAll') }}
            </button>
            <button
              class="text-sm text-red-400 hover:text-red-300"
              type="button"
              :disabled="cart.selectedItems.length === 0"
              @click="deleteSelected"
            >
              {{ t('checkout.deleteSelected') }}
            </button>
          </div>
        </div>

        <div v-if="cart.items.length === 0" class="text-slate-400">{{ t('checkout.emptyCart') }}</div>

        <div v-else class="space-y-3">
          <div v-for="it in cart.items" :key="it.id" class="row relative group">
            <!-- 选中复选框 - 左侧 -->
            <div class="flex-shrink-0">
              <input
                type="checkbox"
                :checked="it.selected !== false"
                class="w-5 h-5 rounded border-slate-600 bg-slate-900 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-0 cursor-pointer"
                @change="cart.toggleSelect(it.id)"
                @click.stop
              />
            </div>

            <!-- 删除按钮 - 右上角 -->
            <button 
              class="absolute top-3 right-3 text-red-400 hover:text-red-300 text-xs flex items-center gap-1 z-10" 
              type="button" 
              @click.stop="cart.remove(it.id)"
            >
              <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>

            <!-- 可点击区域 - 跳转到商品详情 -->
            <div 
              class="flex items-center gap-3 flex-1 cursor-pointer"
              :class="canViewDetail(it.id) ? 'hover:opacity-80' : 'cursor-default'"
              @click="viewDetail(it.id)"
            >
              <!-- 商品图片 -->
              <div class="w-20 h-20 rounded-lg border border-slate-700 bg-slate-900 flex-shrink-0 overflow-hidden">
                <img 
                  :src="it.image || placeholderImage"
                  :alt="it.name"
                  class="w-full h-full object-cover"
                  @error="handleImageError"
                />
              </div>

              <!-- 商品信息和数量控制 -->
              <div class="flex-1 flex items-center justify-between gap-4 pr-8">
                <!-- 左侧：商品信息 -->
                <div class="min-w-0">
                  <div class="font-bold text-slate-100 truncate">{{ it.name }}</div>
                  <div class="text-sm text-slate-400 mt-1">
                    {{ t('checkout.itemPriceQty', { price: it.price.toFixed(2), qty: it.qty }) }}
                  </div>
                  <div class="text-sm text-emerald-300 mt-1">
                    {{ t('checkout.subtotal', { amount: (it.price * it.qty).toFixed(2) }) }}
                  </div>
                  <div v-if="canViewDetail(it.id)" class="text-xs text-indigo-400 mt-1 opacity-0 group-hover:opacity-100 transition">
                    {{ t('checkout.viewDetail') }}
                  </div>
                </div>

                <!-- 右侧：数量控制 -->
                <div class="flex items-center gap-2" @click.stop>
                  <button
                    class="w-7 h-7 rounded bg-slate-800 hover:bg-slate-700 border border-slate-600 flex items-center justify-center text-sm"
                    type="button"
                    :disabled="it.qty <= 1"
                    @click="cart.setQty(it.id, it.qty - 1)"
                  >
                    -
                  </button>
                  <input
                    class="qty"
                    type="number"
                    min="1"
                    :value="it.qty"
                    @change="(e:any) => cart.setQty(it.id, Number(e.target.value))"
                  />
                  <button
                    class="w-7 h-7 rounded bg-slate-800 hover:bg-slate-700 border border-slate-600 flex items-center justify-center text-sm"
                    type="button"
                    @click="cart.setQty(it.id, it.qty + 1)"
                  >
                    +
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <aside class="panel p-6 h-fit lg:sticky lg:top-24 space-y-6">
        <!-- 收货地址 -->
        <div>
          <div class="font-bold mb-3">{{ t('checkout.shippingAddress') }}</div>
          <div class="space-y-3">
            <div>
              <label class="text-xs text-slate-400 mb-1 block">{{ t('checkout.receiver') }}</label>
              <input
                v-model="shippingAddress.name"
                class="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 focus:border-indigo-500 outline-none"
                type="text"
                :placeholder="t('checkout.receiverPlaceholder')"
              />
            </div>
            <div>
              <label class="text-xs text-slate-400 mb-1 block">{{ t('checkout.phone') }}</label>
              <input
                v-model="shippingAddress.phone"
                class="w-full bg-slate-900 border rounded px-3 py-2 text-sm text-slate-200 focus:border-indigo-500 outline-none"
                :class="phoneError ? 'border-red-500' : 'border-slate-600'"
                type="tel"
                maxlength="11"
                :placeholder="t('checkout.phonePlaceholder')"
              />
              <p v-if="phoneError" class="text-xs text-red-400 mt-1">{{ phoneError }}</p>
            </div>
            <div>
              <label class="text-xs text-slate-400 mb-1 block">{{ t('checkout.address') }}</label>
              <textarea
                v-model="shippingAddress.address"
                class="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 focus:border-indigo-500 outline-none resize-none"
                rows="3"
                :placeholder="t('checkout.addressPlaceholder')"
              ></textarea>
            </div>
          </div>
        </div>

        <!-- 订单摘要 -->
        <div class="border-t border-slate-700 pt-6">
          <div class="font-bold mb-4">{{ t('checkout.orderSummary') }}</div>
          
          <!-- 选中的商品列表 -->
          <div v-if="cart.selectedItems.length > 0" class="mb-4 space-y-2">
            <div 
              v-for="item in cart.selectedItems" 
              :key="item.id"
              class="text-sm bg-slate-950/50 rounded-lg p-3 border border-slate-700"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="flex-1 min-w-0">
                  <div class="text-slate-200 truncate">{{ item.name }}</div>
                  <div class="text-slate-400 text-xs mt-1">
                    {{ t('checkout.itemPriceQty', { price: item.price.toFixed(2), qty: item.qty }) }}
                  </div>
                </div>
                <div class="text-emerald-300 font-bold whitespace-nowrap">
                  ¥{{ (item.price * item.qty).toFixed(2) }}
                </div>
              </div>
            </div>
          </div>
          
          <!-- 汇总信息 -->
          <div class="text-sm text-slate-300 flex items-center justify-between">
            <span>{{ t('checkout.selectedItems') }}</span><span>{{ t('checkout.itemCount', { count: cart.selectedCount }) }}</span>
          </div>
          <div class="text-sm text-slate-300 flex items-center justify-between mt-2 pt-2 border-t border-slate-700">
            <span class="font-bold">{{ t('checkout.total') }}</span><span class="text-emerald-300 font-bold text-lg">¥ {{ cart.selectedTotal.toFixed(2) }}</span>
          </div>

          <button 
            class="w-full mt-5 py-3 rounded-xl font-bold shadow-lg transition-all duration-300 border-2"
            :class="cart.selectedItems.length > 0 && isAddressValid && !busy 
              ? 'bg-emerald-600 hover:bg-emerald-500 border-emerald-500 text-white shadow-emerald-500/20' 
              : 'bg-slate-800 border-slate-600 text-slate-400 cursor-not-allowed'"
            type="button" 
            :disabled="cart.selectedItems.length===0 || busy || !isAddressValid" 
            @click="pay"
          >
            {{ busy ? t('checkout.processing') : t('checkout.submitOrder') }}
          </button>
          
          <!-- 提示信息 -->
          <div v-if="cart.selectedItems.length === 0" class="mt-3 text-sm text-yellow-400 bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 flex items-start gap-2">
            <i data-lucide="alert-circle" class="w-4 h-4 flex-shrink-0 mt-0.5"></i>
            <span>{{ t('checkout.tipSelectFirst') }}</span>
          </div>
          <div v-else-if="!isAddressValid" class="mt-3 text-sm text-yellow-400 bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 flex items-start gap-2">
            <i data-lucide="alert-circle" class="w-4 h-4 flex-shrink-0 mt-0.5"></i>
            <span>{{ t('checkout.tipAddressRequired') }}</span>
          </div>
          
          <button 
            class="w-full mt-3 py-3 rounded-xl font-bold transition-all duration-300 border-2"
            :class="cart.items.length > 0 
              ? 'bg-slate-800 hover:bg-slate-700 border-slate-600 text-slate-200' 
              : 'bg-slate-900 border-slate-700 text-slate-500 cursor-not-allowed'"
            type="button" 
            :disabled="cart.items.length===0" 
            @click="cart.clear"
          >
            {{ t('checkout.clearCart') }}
          </button>

          <div class="text-xs text-slate-500 mt-4">
            {{ t('checkout.submitTip') }}
          </div>
        </div>
      </aside>
    </div>

    <div v-if="msg" class="text-sm" :class="msgType==='error' ? 'text-red-300' : 'text-emerald-300'">{{ msg }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useCartStore } from '../stores/cart'
import { api } from '../lib/api'

declare const lucide: any

const router = useRouter()
const cart = useCartStore()
const { t } = useI18n()
cart.hydrate()

const msg = ref('')
const msgType = ref<'ok' | 'error'>('ok')
const busy = ref(false)

// 占位图base64
const placeholderImage = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgZmlsbD0iIzFhMjAzMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTgiIGZpbGw9IiM2NDc0OGIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj7lm77niYfml6Dms5XliqDovb08L3RleHQ+PC9zdmc+'

function handleImageError(e: Event) {
  const target = e.target as HTMLImageElement
  target.src = placeholderImage
}

// 收货地址
const shippingAddress = ref({
  name: '',
  phone: '',
  address: ''
})

// 手机号验证错误信息
const phoneError = ref('')

// 验证手机号格式
function validatePhone(phone: string): boolean {
  const phoneRegex = /^1[3-9]\d{9}$/
  return phoneRegex.test(phone.trim())
}

// 监听手机号输入，实时验证
watch(() => shippingAddress.value.phone, (newPhone) => {
  if (newPhone.trim() === '') {
    phoneError.value = ''
  } else if (!validatePhone(newPhone)) {
    phoneError.value = '请输入正确的手机号码'
  } else {
    phoneError.value = ''
  }
})

// 全选状态
const allSelected = computed(() => {
  return cart.items.length > 0 && cart.items.every(item => item.selected !== false)
})

// 验证地址是否填写完整
const isAddressValid = computed(() => {
  return shippingAddress.value.name.trim() !== '' &&
         shippingAddress.value.phone.trim() !== '' &&
         validatePhone(shippingAddress.value.phone) &&
         shippingAddress.value.address.trim() !== ''
})

// 切换全选
function toggleSelectAll() {
  if (allSelected.value) {
    cart.unselectAll()
  } else {
    cart.selectAll()
  }
}

// 删除选中的商品
function deleteSelected() {
  if (confirm(t('checkout.confirmDeleteSelected'))) {
    cart.clearSelected()
  }
}

// 判断商品是否可以查看详情（排除3D打印定制商品）
function canViewDetail(itemId: string) {
  // 3D打印定制商品的ID格式：print:asset_id:height:material
  return !itemId.startsWith('print:')
}

// 查看商品详情
function viewDetail(itemId: string) {
  if (!canViewDetail(itemId)) return
  
  // 提取纯商品ID（去掉规格信息）
  // 商品ID格式可能是：product_id 或 product_id:spec1:spec2:spec3
  const productId = itemId.split(':')[0]
  
  // 普通商品，跳转到商品详情页（路由是 /market/:id）
  router.push(`/market/${productId}`)
}

function toastOk(t: string) {
  msgType.value = 'ok'
  msg.value = t
  setTimeout(() => (msg.value = ''), 2000)
}

function toastErr(t: string) {
  msgType.value = 'error'
  msg.value = t
  setTimeout(() => (msg.value = ''), 2600)
}

async function pay() {
  if (cart.selectedItems.length === 0) return
  if (busy.value) return
  if (!isAddressValid.value) {
    toastErr(t('checkout.addressIncomplete'))
    return
  }
  
  // 额外验证手机号
  if (!validatePhone(shippingAddress.value.phone)) {
    toastErr('请输入正确的手机号码')
    return
  }
  
  busy.value = true
  try {
    // 1) 创建订单（只包含选中的商品）
    const payload = {
      items: cart.selectedItems.map((it) => ({
        id: it.id,
        name: it.name,
        price: it.price,
        quantity: it.qty
      })),
      total_amount: cart.selectedTotal,
      payment_method: null,  // 不再预设支付方式，让用户在订单详情页选择
      shipping_address: {
        name: shippingAddress.value.name,
        phone: shippingAddress.value.phone,
        address: shippingAddress.value.address
      }
    }
    const { order_id } = await api.orders.create(payload)

    toastOk(t('checkout.orderCreated', { orderId: order_id }))
    // 清除已下单的商品
    cart.clearSelected()
    // 清空地址信息
    shippingAddress.value = { name: '', phone: '', address: '' }
    phoneError.value = ''
    
    // 跳转到订单详情页进行支付
    setTimeout(() => {
      router.push(`/orders/${order_id}`)
    }, 1000)
  } catch (e: any) {
    toastErr(e?.message || t('checkout.orderFailed'))
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  setTimeout(() => {
    if (typeof lucide !== 'undefined' && lucide?.createIcons) {
      lucide.createIcons()
    }
  }, 100)
})

// 监听地址和选中商品变化，重新渲染图标
watch([() => cart.selectedItems.length, isAddressValid], () => {
  setTimeout(() => {
    if (typeof lucide !== 'undefined' && lucide?.createIcons) {
      lucide.createIcons()
    }
  }, 50)
})
</script>

<style scoped>
.panel {
  @apply rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur;
}
.btn-primary {
  @apply py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold shadow-lg shadow-indigo-500/20 disabled:opacity-60 disabled:cursor-not-allowed;
}
.btn-secondary {
  @apply px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 text-sm font-bold disabled:opacity-60 disabled:cursor-not-allowed;
}
.row {
  @apply flex items-start gap-3 p-4 rounded-xl bg-slate-950/30 border border-slate-700 hover:border-slate-600 transition;
}
.qty {
  @apply w-14 border border-slate-600 rounded-lg px-2 py-1 text-sm text-center outline-none focus:border-indigo-500;
  background-color: rgb(15 23 42) !important; /* slate-900 */
  color: rgb(241 245 249) !important; /* slate-100 */
}
.qty:focus {
  background-color: rgb(30 41 59) !important; /* slate-800 */
  border-color: rgb(99 102 241) !important; /* indigo-500 */
}
/* 隐藏 number 输入框的上下箭头 */
.qty::-webkit-inner-spin-button,
.qty::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.qty {
  -moz-appearance: textfield;
}
</style>

