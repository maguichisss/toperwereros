import { createContext, useContext, useState, useEffect, useCallback, useMemo, useRef } from 'react'

const CART_KEY = 'store_cart'

function loadCart() {
  try {
    const raw = localStorage.getItem(CART_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

const CartContext = createContext(null)

export function CartProvider({ children }) {
  const [items, setItems] = useState(loadCart)
  const itemsRef = useRef(items)

  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(items))
  }, [items])

  useEffect(() => {
    itemsRef.current = items
  }, [items])

  const addItem = useCallback((product) => {
    const current = itemsRef.current
    const existing = current.find(c => c.product_id === product.id)
    if (existing && existing.quantity >= (product.stock ?? existing.stock)) return false
    setItems(prev => {
      const ex = prev.find(c => c.product_id === product.id)
      if (ex) {
        return prev.map(c =>
          c.product_id === product.id ? { ...c, quantity: c.quantity + 1 } : c
        )
      }
      return [
        {
          product_id: product.id,
          name: product.name,
          code: product.code,
          image_url: product.image_url,
          price: parseFloat(product.price),
          quantity: 1,
          stock: product.stock ?? 1,
        },
        ...prev,
      ]
    })
    return true
  }, [])

  const removeItem = useCallback((productId) => {
    setItems(prev => prev.filter(c => c.product_id !== productId))
  }, [])

  const updateQty = useCallback((productId, delta) => {
    setItems(prev =>
      prev.map(c => {
        if (c.product_id !== productId) return c
        const newQty = delta > 0 && c.quantity >= c.stock ? c.quantity : c.quantity + delta
        return newQty <= 0 ? null : { ...c, quantity: newQty }
      }).filter(Boolean)
    )
  }, [])

  const clearCart = useCallback(() => setItems([]), [])

  const itemCount = useMemo(() => items.reduce((sum, c) => sum + c.quantity, 0), [items])
  const total = useMemo(() => items.reduce((sum, c) => sum + c.price * c.quantity, 0), [items])

  const value = useMemo(
    () => ({ items, addItem, removeItem, updateQty, clearCart, itemCount, total }),
    [items, addItem, removeItem, updateQty, clearCart, itemCount, total],
  )

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

export function useCart() {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart must be used inside CartProvider')
  return ctx
}
