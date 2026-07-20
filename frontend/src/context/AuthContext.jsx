import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const API_BASE = '/api'
const STORAGE_KEY = 'store_token'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY))
  const [loading, setLoading] = useState(true)

  const fetchUser = useCallback(async (t) => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${t}` },
      })
      if (!res.ok) throw new Error('Unauthorized')
      const data = await res.json()
      setUser(data)
    } catch {
      setUser(null)
      setToken(null)
      localStorage.removeItem(STORAGE_KEY)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (token) {
      fetchUser(token)
    } else {
      setLoading(false)
    }
  }, [token, fetchUser])

  const login = async (username, password) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || 'Error al iniciar sesión')
    }
    const data = await res.json()
    localStorage.setItem(STORAGE_KEY, data.access_token)
    setToken(data.access_token)
    await fetchUser(data.access_token)
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem(STORAGE_KEY)
  }

  const refreshUser = useCallback(async () => {
    if (token) await fetchUser(token)
  }, [token, fetchUser])

  const can = (permission) => {
    if (!user) return false
    if (user.role_name === 'admin') return true
    if (user.role_name === 'viewer') {
      const viewOnly = ['product.view', 'sale.view', 'apartado.view', 'customer.view', 'category.view', 'color.view']
      return viewOnly.includes(permission)
    }
    if (user.role_name === 'employee') {
      const employeePerms = [
        'product.view', 'product.create', 'product.edit', 'product.delete',
        'sale.view', 'sale.create',
        'apartado.view', 'apartado.create', 'apartado.edit',
        'customer.view', 'customer.create', 'customer.edit', 'customer.delete',
        'category.view', 'color.view',
      ]
      return employeePerms.includes(permission)
    }
    return false
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, refreshUser, can, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
