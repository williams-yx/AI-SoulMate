<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between gap-4 flex-wrap">
      <div class="text-2xl font-bold">{{ t('productDetail.title') }}</div>
      <RouterLink to="/market" class="btn-secondary">{{ t('productDetail.backMarket') }}</RouterLink>
    </div>

    <div v-if="loading" class="panel p-6 text-slate-400">{{ t('productDetail.loading') }}</div>
    <div v-else-if="err" class="panel p-6 text-red-300">{{ err }}</div>

    <template v-else-if="product">
      <div class="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6">
        <!-- 左侧：商品图片 -->
        <section class="panel p-6">
          <div class="aspect-square rounded-xl border border-slate-700 bg-slate-900 flex items-center justify-center overflow-hidden">
            <img 
              v-if="currentImage"
              :src="currentImage" 
              :alt="product.name"
              class="w-full h-full object-contain"
              @error="handleImageError"
            />
            <div v-else class="text-slate-500">
              <i data-lucide="image-off" class="w-24 h-24"></i>
            </div>
          </div>
          
          <!-- 图片缩略图 -->
          <div v-if="product.images && product.images.length > 1" class="flex gap-2 mt-4">
            <button
              v-for="(img, idx) in product.images"
              :key="idx"
              class="w-20 h-20 rounded-lg border-2 overflow-hidden transition"
              :class="currentImage === img ? 'border-indigo-500' : 'border-slate-700 hover:border-slate-600'"
              type="button"
              @click="currentImage = img"
            >
              <img :src="img" class="w-full h-full object-cover" alt="" />
            </button>
          </div>
        </section>

        <!-- 右侧：商品信息 -->
        <aside class="space-y-6">
          <!-- 基本信息 -->
          <section class="panel p-6">
            <div class="text-2xl font-bold text-slate-100 mb-2">{{ product.name }}</div>
            <div v-if="product.category_name" class="text-sm text-slate-400 mb-4">
              {{ t('productDetail.categoryLabel', { name: product.category_name }) }}
            </div>
            
            <!-- 价格 -->
            <div class="bg-slate-900/50 rounded-lg p-4 mb-4">
              <div v-if="product.price_type === 'fixed'" class="text-3xl font-bold text-emerald-300">
                ¥{{ actualPrice.toFixed(2) }}
              </div>
              <div v-else-if="product.price_type === 'weight'" class="space-y-1">
                <div class="text-sm text-slate-400">{{ t('productDetail.pricePerGramLabel') }}</div>
                <div class="text-3xl font-bold text-emerald-300">
                  ¥{{ actualPrice.toFixed(2) }}/g
                </div>
              </div>
              <div v-if="product.price_unit" class="text-xs text-slate-500 mt-1">
                {{ product.price_unit }}
              </div>
            </div>

            <!-- 库存 -->
            <div class="text-sm text-slate-400 mb-4">
              <span v-if="product.stock_type === 'limited'">
                {{ t('productDetail.stockLimited', { count: product.stock }) }}
              </span>
              <span v-else-if="product.stock_type === 'unlimited'">
                {{ t('productDetail.stockUnlimited') }}
              </span>
              <span v-else>
                {{ t('productDetail.stockVirtual') }}
              </span>
            </div>

            <!-- 描述 -->
            <div v-if="product.description" class="text-sm text-slate-300 mb-4 leading-relaxed">
              {{ product.description }}
            </div>

            <!-- 可选规格选择 -->
            <div v-if="hasSelectableSpecs" class="border-t border-slate-700 pt-4 mb-4 space-y-4">
              <div class="text-sm font-bold text-slate-400 mb-3">{{ t('productDetail.chooseSpecs') }}</div>
              
              <!-- 高度选择（定制白模） -->
              <div v-if="productSpecs.heights && Array.isArray(productSpecs.heights)" class="space-y-2">
                <label class="text-sm text-slate-400">{{ t('productDetail.heightLabel') }}</label>
                <div class="flex gap-2">
                  <button
                    v-for="height in productSpecs.heights"
                    :key="height"
                    class="px-4 py-2 rounded-lg border-2 transition"
                    :class="selectedHeight === height ? 'border-indigo-500 bg-indigo-500/20 text-indigo-300' : 'border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500'"
                    type="button"
                    @click="selectedHeight = height"
                  >
                    {{ height }}
                  </button>
                </div>
              </div>

              <!-- 颜色选择（PLA耗材） -->
              <div v-if="productSpecs.colors && Array.isArray(productSpecs.colors)" class="space-y-2">
                <label class="text-sm text-slate-400">{{ t('productDetail.colorLabel') }}</label>
                <div class="flex gap-2 flex-wrap">
                  <button
                    v-for="color in productSpecs.colors"
                    :key="color"
                    class="px-4 py-2 rounded-lg border-2 transition"
                    :class="selectedColor === color ? 'border-indigo-500 bg-indigo-500/20 text-indigo-300' : 'border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500'"
                    type="button"
                    @click="selectedColor = color"
                  >
                      {{ formatColorLabel(color) }}
                  </button>
                </div>
              </div>

              <!-- 材质选择（如果有多个材质） -->
              <div v-if="productSpecs.materials && Array.isArray(productSpecs.materials)" class="space-y-2">
                <label class="text-sm text-slate-400">{{ t('productDetail.materialLabel') }}</label>
                <div class="flex gap-2">
                  <button
                    v-for="material in productSpecs.materials"
                    :key="material"
                    class="px-4 py-2 rounded-lg border-2 transition"
                    :class="selectedMaterial === material ? 'border-indigo-500 bg-indigo-500/20 text-indigo-300' : 'border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500'"
                    type="button"
                    @click="selectedMaterial = material"
                  >
                    {{ material }}
                  </button>
                </div>
              </div>
            </div>

            <!-- 固定规格信息展示（不可选） -->
            <div v-if="hasDisplaySpecs" class="border-t border-slate-700 pt-4 mb-4">
              <div class="text-sm font-bold text-slate-400 mb-2">{{ t('productDetail.specsTitle') }}</div>
              <div class="space-y-1 text-sm text-slate-300">
                <div v-if="productSpecs.material && !Array.isArray(productSpecs.material)">
                  <span class="text-slate-400">{{ t('productDetail.specMaterial') }}</span>
                  <span>{{ productSpecs.material }}</span>
                </div>
                <div v-if="productSpecs.package">
                  <span class="text-slate-400">{{ t('productDetail.specPackage') }}</span>
                  <span>{{ productSpecs.package }}</span>
                </div>
                <div v-if="productSpecs.max_height">
                  <span class="text-slate-400">{{ t('productDetail.specMaxHeight') }}</span>
                  <span>{{ productSpecs.max_height }}</span>
                </div>
                <div v-if="productSpecs.color && !Array.isArray(productSpecs.color)">
                  <span class="text-slate-400">{{ t('productDetail.specColor') }}</span>
                  <span>{{ formatColorLabel(productSpecs.color) }}</span>
                </div>
                <div v-if="productSpecs.size">
                  <span class="text-slate-400">{{ t('productDetail.specSize') }}</span>
                  <span>{{ productSpecs.size }}</span>
                </div>
                <div v-if="productSpecs.weight">
                  <span class="text-slate-400">{{ t('productDetail.specWeight') }}</span>
                  <span>{{ productSpecs.weight }}</span>
                </div>
                <div v-if="productSpecs.features && Array.isArray(productSpecs.features)">
                  <span class="text-slate-400">{{ t('productDetail.specFeatures') }}</span>
                  <span>{{ productSpecs.features.join(locale === 'zh-CN' ? '、' : ', ') }}</span>
                </div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="border-t border-slate-700 pt-4 mt-4 space-y-3">
              <!-- 数量选择（固定价格商品） -->
              <div v-if="product.price_type === 'fixed'" class="flex items-center gap-3">
                <span class="text-sm text-slate-400">{{ t('productDetail.quantityLabel') }}</span>
                <input
                  v-model.number="quantity"
                  class="w-24 text-center bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm"
                  type="number"
                  min="1"
                  max="999"
                  @input="validateQuantity"
                  @blur="validateQuantity"
                  placeholder="1-999"
                />
                <span class="text-xs text-slate-500">{{ t('productDetail.quantityHint') }}</span>
              </div>

              <!-- 克重输入（按重量计价商品） -->
              <div v-else-if="product.price_type === 'weight'" class="space-y-2">
                <label class="text-sm text-slate-400">{{ t('productDetail.weightInputLabel') }}</label>
                <input
                  v-model.number="weight"
                  class="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm"
                  type="number"
                  min="1"
                  max="999"
                  @input="validateWeight"
                  @blur="validateWeight"
                  placeholder="1-999"
                />
                <div class="text-xs text-slate-500">{{ t('productDetail.weightHint') }}</div>
                <div v-if="weight > 0" class="text-sm text-emerald-300">
                  {{ t('productDetail.estimatedPrice', { amount: (weight * actualPrice).toFixed(2) }) }}
                </div>
              </div>

              <button
                class="btn-primary w-full border-2 border-indigo-500"
                type="button"
                :disabled="busy || !canAddToCart"
                @click="addToCart"
              >
                <i data-lucide="shopping-cart" class="w-4 h-4 inline-block mr-2"></i>
                {{ busy ? t('productDetail.addToCartBusy') : t('productDetail.addToCart') }}
              </button>
              
              <button
                class="btn-secondary w-full border-2 border-slate-600"
                type="button"
                :disabled="busy || !canAddToCart"
                @click="addToCartAndCheckout"
              >
                <i data-lucide="credit-card" class="w-4 h-4 inline-block mr-2"></i>
                {{ busy ? t('productDetail.addToCartBusy') : t('productDetail.goCheckout') }}
              </button>
            </div>
          </section>
        </aside>
      </div>
    </template>

    <!-- 成功提示弹窗 -->
    <div
      v-if="showSuccessModal"
      class="fixed inset-0 flex items-center justify-center z-50 pointer-events-none"
    >
      <div class="bg-slate-900 rounded-2xl border border-emerald-500/50 px-8 py-6 shadow-2xl shadow-emerald-500/20 animate-scaleIn pointer-events-auto">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 bg-emerald-500/20 rounded-full flex items-center justify-center flex-shrink-0">
            <i data-lucide="check-circle" class="w-8 h-8 text-emerald-400"></i>
          </div>
          <div class="text-lg font-bold text-slate-100">{{ t('productDetail.addedToCart') }}</div>
        </div>
      </div>
    </div>

    <div v-if="msg" class="text-sm" :class="msgType==='error' ? 'text-red-300' : 'text-emerald-300'">{{ msg }}</div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed, nextTick } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '../lib/api'
import { useCartStore } from '../stores/cart'
import { useAuthStore } from '../stores/auth'

declare const lucide: any

const { t, te, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const cart = useCartStore()
const auth = useAuthStore()
const productId = route.params.id as string

const loading = ref(true)
const err = ref('')
const product = ref<any>(null)
const currentImage = ref('')
const quantity = ref(1)
const weight = ref<number>(0)
const busy = ref(false)
const msg = ref('')
const msgType = ref<'ok' | 'error'>('ok')
const showSuccessModal = ref(false)

// 规格选择状态
const selectedHeight = ref<string>('')
const selectedColor = ref<string>('')
const selectedMaterial = ref<string>('')

const productSpecs = computed(() => {
  if (!product.value?.specs) return {}
  try {
    const specs = typeof product.value.specs === 'string' 
      ? JSON.parse(product.value.specs) 
      : product.value.specs
    return specs || {}
  } catch {
    return {}
  }
})

// 判断是否有可选规格
const hasSelectableSpecs = computed(() => {
  return (
    (productSpecs.value.heights && Array.isArray(productSpecs.value.heights)) ||
    (productSpecs.value.colors && Array.isArray(productSpecs.value.colors)) ||
    (productSpecs.value.materials && Array.isArray(productSpecs.value.materials))
  )
})

// 判断是否有固定规格信息需要展示
const hasDisplaySpecs = computed(() => {
  const specs = productSpecs.value
  return (
    (specs.material && !Array.isArray(specs.material)) ||
    specs.package ||
    specs.max_height ||
    (specs.color && !Array.isArray(specs.color)) ||
    specs.size ||
    specs.weight ||
    (specs.features && Array.isArray(specs.features))
  )
})

// 获取实际单价（克重计价商品从specs中读取）
const actualPrice = computed(() => {
  if (!product.value) return 0
  if (product.value.price_type === 'weight') {
    return Number(productSpecs.value.price_per_gram || 0)
  }
  return Number(product.value.price)
})

const canAddToCart = computed(() => {
  if (product.value?.price_type === 'weight') {
    return weight.value > 0
  }
  return quantity.value > 0
})

function formatSpecKey(key: string) {
  const path = `productDetail.specKeys.${key}`
  return te(path) ? t(path) : key
}

  function formatColorLabel(value: any) {
    if (value === undefined || value === null) return ''
    const s = String(value)
    const map: Record<string, string> = {
      '白色': 'white', '黑色': 'black', '红色': 'red', '蓝色': 'blue',
      'white': 'white', 'black': 'black', 'red': 'red', 'blue': 'blue',
      'White': 'white', 'Black': 'black', 'Red': 'red', 'Blue': 'blue'
    }
    const key = map[s] || s.toLowerCase()
    const path = `productDetail.colorOptions.${key}`
    return te(path) ? t(path) : s
  }

function formatSpecValue(value: any) {
  if (Array.isArray(value)) {
    return value.join('、')
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

function handleImageError(e: Event) {
  const target = e.target as HTMLImageElement
  // 使用base64内联的占位图，避免路径问题
  target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgZmlsbD0iIzFhMjAzMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTgiIGZpbGw9IiM2NDc0OGIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj7lm77niYfml6Dms5XliqDovb08L3RleHQ+PC9zdmc+'
}

function validateQuantity() {
  // 移除非数字字符
  const val = String(quantity.value).replace(/[^\d]/g, '')
  let num = parseInt(val) || 1
  
  // 限制范围 1-999
  if (num < 1) num = 1
  if (num > 999) num = 999
  
  quantity.value = num
}

function validateWeight() {
  // 移除非数字字符
  const val = String(weight.value).replace(/[^\d]/g, '')
  let num = parseInt(val) || 0
  
  // 限制范围 1-999
  if (num < 0) num = 0
  if (num > 999) num = 999
  
  weight.value = num
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

async function loadProduct() {
  loading.value = true
  err.value = ''
  try {
    product.value = await api.products.detail(productId)
    
    // 设置默认图片
    if (product.value.images && product.value.images.length > 0) {
      currentImage.value = product.value.images[0]
    }
    
    // 初始化默认选中的规格
    const specs = productSpecs.value
    if (specs.heights && Array.isArray(specs.heights) && specs.heights.length > 0) {
      selectedHeight.value = specs.heights[0]
    }
    if (specs.colors && Array.isArray(specs.colors) && specs.colors.length > 0) {
      selectedColor.value = specs.colors[0]
    }
    if (specs.materials && Array.isArray(specs.materials) && specs.materials.length > 0) {
      selectedMaterial.value = specs.materials[0]
    }
    
    // 渲染图标
    setTimeout(() => {
      if (typeof lucide !== 'undefined' && lucide?.createIcons) {
        lucide.createIcons()
      }
    }, 100)
  } catch (e: any) {
    err.value = e?.message || t('productDetail.loadFailed')
  } finally {
    loading.value = false
  }
}

async function addToCart() {
  if (busy.value) return
  
  // 检查登录状态
  if (!auth.isAuthed) {
    await router.replace({ path: route.path, query: { ...route.query, login: '1' } })
    return
  }
  
  busy.value = true
  try {    
    if (product.value.price_type === 'weight') {
      // 按重量计价
      if (weight.value <= 0) {
        toastErr(t('productDetail.enterWeight'))
        return
      }
      
      const totalPrice = weight.value * actualPrice.value
      
      // 构建商品名称，包含选中的规格
      let productName = product.value.name
      const specParts = []
      if (selectedHeight.value) specParts.push(selectedHeight.value)
      if (selectedColor.value) specParts.push(selectedColor.value)
      if (selectedMaterial.value) specParts.push(selectedMaterial.value)
      specParts.push(`${weight.value}g`)
      if (specParts.length > 0) {
        productName += `（${specParts.join('，')}）`
      }
      
      cart.add(
        {
          id: `${product.value.id}:${weight.value}g:${selectedHeight.value}:${selectedColor.value}`,
          name: productName,
          price: totalPrice,
          image: product.value.images?.[0] || ''
        },
        1
      )
      showSuccessModal.value = true
      setTimeout(() => {
        if (typeof lucide !== 'undefined' && lucide?.createIcons) {
          lucide.createIcons()
        }
      }, 100)
      // 1.5秒后自动关闭弹窗
      setTimeout(() => {
        showSuccessModal.value = false
      }, 1500)
    } else {
      // 固定价格
      let productName = product.value.name
      const specParts = []
      if (selectedHeight.value) specParts.push(selectedHeight.value)
      if (selectedColor.value) specParts.push(selectedColor.value)
      if (selectedMaterial.value) specParts.push(selectedMaterial.value)
      if (specParts.length > 0) {
        productName += `（${specParts.join('，')}）`
      }
      
      cart.add(
        {
          id: `${product.value.id}:${selectedHeight.value}:${selectedColor.value}:${selectedMaterial.value}`,
          name: productName,
          price: actualPrice.value,
          image: product.value.images?.[0] || ''
        },
        quantity.value
      )
      showSuccessModal.value = true
      setTimeout(() => {
        if (typeof lucide !== 'undefined' && lucide?.createIcons) {
          lucide.createIcons()
        }
      }, 100)
      // 1.5秒后自动关闭弹窗
      setTimeout(() => {
        showSuccessModal.value = false
      }, 1500)
    }
  } catch (e: any) {
    toastErr(e?.message || t('productDetail.addFailed'))
  } finally {
    busy.value = false
  }
}

// 加入购物车并跳转到结算页面
async function addToCartAndCheckout() {
  if (busy.value) return
  
  // 检查登录状态
  if (!auth.isAuthed) {
    await router.replace({ path: route.path, query: { ...route.query, login: '1' } })
    return
  }
  
  busy.value = true
  try {    
    if (product.value.price_type === 'weight') {
      // 按重量计价
      if (weight.value <= 0) {
        toastErr(t('productDetail.enterWeight'))
        busy.value = false
        return
      }
      
      const totalPrice = weight.value * actualPrice.value
      
      // 构建商品名称，包含选中的规格
      let productName = product.value.name
      const specParts = []
      if (selectedHeight.value) specParts.push(selectedHeight.value)
      if (selectedColor.value) specParts.push(selectedColor.value)
      if (selectedMaterial.value) specParts.push(selectedMaterial.value)
      specParts.push(`${weight.value}g`)
      if (specParts.length > 0) {
        productName += `（${specParts.join('，')}）`
      }
      
      cart.add(
        {
          id: `${product.value.id}:${weight.value}g:${selectedHeight.value}:${selectedColor.value}`,
          name: productName,
          price: totalPrice,
          image: product.value.images?.[0] || ''
        },
        1
      )
    } else {
      // 固定价格
      let productName = product.value.name
      const specParts = []
      if (selectedHeight.value) specParts.push(selectedHeight.value)
      if (selectedColor.value) specParts.push(selectedColor.value)
      if (selectedMaterial.value) specParts.push(selectedMaterial.value)
      if (specParts.length > 0) {
        productName += `（${specParts.join('，')}）`
      }
      
      cart.add(
        {
          id: `${product.value.id}:${selectedHeight.value}:${selectedColor.value}:${selectedMaterial.value}`,
          name: productName,
          price: actualPrice.value,
          image: product.value.images?.[0] || ''
        },
        quantity.value
      )
    }
    
    // 跳转到结算页面
    router.push('/checkout')
  } catch (e: any) {
    toastErr(e?.message || t('productDetail.addFailed'))
    busy.value = false
  }
}

onMounted(() => {
  loadProduct()
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
  @apply px-4 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 font-bold disabled:opacity-60 disabled:cursor-not-allowed;
}

/* 隐藏 number 输入框的上下箭头 */
input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

input[type="number"] {
  -moz-appearance: textfield;
}

/* 弹窗动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.animate-fadeIn {
  animation: fadeIn 0.2s ease-out;
}

.animate-scaleIn {
  animation: scaleIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
</style>
