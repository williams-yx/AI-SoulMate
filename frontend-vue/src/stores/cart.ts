import { defineStore } from 'pinia'

export type CartItem = {
  id: string
  name: string
  price: number
  qty: number
  image?: string
  selected?: boolean  // 添加选中状态
}

const STORAGE_KEY = 'cart_v1'

function loadCart(): CartItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as CartItem[]) : []
  } catch {
    return []
  }
}

function saveCart(items: CartItem[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

export const useCartStore = defineStore('cart', {
  state: () => ({
    items: loadCart() as CartItem[]
  }),
  getters: {
    count: (s) => s.items.reduce((a, b) => a + b.qty, 0),
    total: (s) => s.items.reduce((a, b) => a + b.price * b.qty, 0),
    selectedItems: (s) => s.items.filter(item => item.selected !== false),
    selectedCount: (s) => s.items.filter(item => item.selected !== false).reduce((a, b) => a + b.qty, 0),
    selectedTotal: (s) => s.items.filter(item => item.selected !== false).reduce((a, b) => a + b.price * b.qty, 0)
  },
  actions: {
    hydrate() {
      this.items = loadCart()
    },
    add(item: Omit<CartItem, 'qty'>, qty = 1) {
      const idx = this.items.findIndex((x) => x.id === item.id)
      if (idx >= 0) this.items[idx].qty += qty
      else this.items.push({ ...item, qty, selected: true })  // 新添加的商品默认选中
      saveCart(this.items)
    },
    remove(id: string) {
      this.items = this.items.filter((x) => x.id !== id)
      saveCart(this.items)
    },
    setQty(id: string, qty: number) {
      const idx = this.items.findIndex((x) => x.id === id)
      if (idx < 0) return
      this.items[idx].qty = Math.max(1, Math.floor(qty))
      saveCart(this.items)
    },
    toggleSelect(id: string) {
      const idx = this.items.findIndex((x) => x.id === id)
      if (idx < 0) return
      this.items[idx].selected = !this.items[idx].selected
      saveCart(this.items)
    },
    selectAll() {
      this.items.forEach(item => item.selected = true)
      saveCart(this.items)
    },
    unselectAll() {
      this.items.forEach(item => item.selected = false)
      saveCart(this.items)
    },
    clear() {
      this.items = []
      localStorage.removeItem(STORAGE_KEY)
    },
    clearSelected() {
      this.items = this.items.filter(item => item.selected === false)
      saveCart(this.items)
    }
  }
})

